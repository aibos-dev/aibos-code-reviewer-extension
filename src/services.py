"""
services.py
Business Logic Layer
====================

Handles:
- Synchronous code review generation
- Asynchronous job queue
- Feedback saving (with foreign key checks)
"""

import json
import logging
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from queue import Queue

from sqlalchemy.orm import Session

from .llm_engines.base import BaseLLMEngine
from .models_db import ReviewCategories, ReviewFeedback, ReviewJobs, Reviews
from .schemas import ReviewRequest

logger = logging.getLogger(__name__)

# For async jobs
job_queue = Queue()

DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"
# Load config.json once at module level
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")

with open(CONFIG_FILE, encoding="utf-8") as f:
    CONFIG = json.load(f)


def _format_prompt(language: str, source_code: str, diff: str | None) -> str:
    """
    Provide a prompt that instructs the LLM to return JSON with multiple categories.
    Uses a JSON config file to define categories and instructions dynamically.
    """

    # Extract values from config
    categories_str = ", ".join(CONFIG.get("categories", []))  # Ensure categories exist
    instructions = CONFIG.get("instructions", "").replace("{categories}", categories_str)

    # Format guidelines with safe default values
    format_guidelines = CONFIG.get("format_guidelines", {})  # Ensure it exists
    use_markdown = format_guidelines.get("use_markdown", False)
    include_line_numbers = format_guidelines.get("include_line_numbers", False)
    max_length = format_guidelines.get("max_response_length", 10000)

    # Generate additional formatting instructions
    formatting_instructions = []
    if use_markdown:
        formatting_instructions.append("- Use markdown for inline code (`code`) and code blocks.")
    if include_line_numbers:
        formatting_instructions.append("- Reference specific line numbers where applicable.")

    formatting_str = "\n".join(formatting_instructions) if formatting_instructions else ""

    base_prompt = (
        f"### Code Review Request ({CONFIG.get('review_depth', 'Deep')} Analysis)\n"
        f"#### Language: {language}\n\n"
        f"```{language}\n{source_code}\n```\n\n"
        f"#### Diff:\n{diff or 'No diff provided.'}\n\n"
        f"### Categories of Interest:\n{categories_str}\n\n"
        f"### Review Guidelines:\n"
        f"{instructions}\n\n"
        f"{formatting_str}\n"
        f"- Ensure response length does not exceed {max_length} characters.\n"
        f"- Return only valid JSON as output."
    )

    return base_prompt


def _parse_llm_output(raw_output: str) -> list[dict]:
    """
    Parses the LLM output into multiple categories, ensuring proper JSON structure.
    Handles various edge cases in LLM responses to maintain consistent output format.
    """
    import re

    # Strip any leading/trailing whitespace and detect JSON blocks
    cleaned_output = raw_output.strip()

    # Look for JSON array pattern - handles cases where LLM might include thinking/explanation
    json_match = re.search(r"\[\s*\{.*\}\s*\]", cleaned_output, re.DOTALL)
    if json_match:
        cleaned_output = json_match.group(0)

    try:
        # Parse the JSON
        data = json.loads(cleaned_output)

        # Ensure it's a list
        if not isinstance(data, list):
            data = [data]  # Convert single object to list

        # Validate each item has required fields
        validated_items = []
        general_feedback = None

        for item in data:
            if not isinstance(item, dict):
                continue

            if "category" in item and "message" in item:
                # Store General Feedback separately to ensure it comes first
                if item["category"] == "General Feedback":
                    general_feedback = item
                else:
                    validated_items.append(item)

        # If no general feedback was found, create a fallback
        if not general_feedback:
            # Try to extract a reasonable message from the raw output
            fallback_message = raw_output
            if len(fallback_message) > 5000:  # Truncate if too long
                fallback_message = fallback_message[:1000] + "..."

            general_feedback = {"category": "General Feedback", "message": fallback_message}

        # Return with General Feedback first, followed by other categories
        result = [general_feedback] + validated_items

        logger.debug(f"Parsed LLM Output: {json.dumps(result, indent=2, ensure_ascii=False)}")
        return result

    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse LLM JSON. Error: {e}. Raw output: {raw_output[:100]}...")

        # More robust fallback - try to extract any JSON-like parts
        try:
            # Look for anything that might be JSON arrays or objects
            potential_json = re.findall(r"(\[.*?\]|\{.*?\})", raw_output, re.DOTALL)
            for json_candidate in potential_json:
                try:
                    parsed = json.loads(json_candidate)
                    if isinstance(parsed, list) and len(parsed) > 0:
                        return _parse_llm_output(json_candidate)  # Recursively try to parse this candidate
                    if isinstance(parsed, dict) and "category" in parsed and "message" in parsed:
                        return [parsed]  # We found a valid item
                except:
                    continue
        except:
            pass  # Silently fail if regex fails

        # Ultimate fallback - just wrap the raw output
        fallback = [{"category": "General Feedback", "message": raw_output}]
        logger.debug("Using ultimate fallback response")

        return fallback


def format_review_response(review: Reviews) -> dict:
    """
    Formats a review into the desired JSON response structure.

    Args:
        review: The Reviews object from the database

    Returns:
        dict: Formatted response with reviewId and reviews array
    """
    # Extract categories and format them
    categories = []
    for category in review.categories:
        categories.append({"category": category.category_name, "message": category.message})

    # Ensure General Feedback always comes first
    general_first = []
    other_categories = []

    for cat in categories:
        if cat["category"] == "General Feedback":
            general_first.append(cat)
        else:
            other_categories.append(cat)

    # Construct the final response
    response = {"reviewId": str(review.review_id), "reviews": general_first + other_categories}

    return response


# -----------------------------------------
# Asynchronous job worker logic
# -----------------------------------------
def queue_review_job(session: Session, review_req: ReviewRequest) -> str:
    new_job = ReviewJobs()
    session.add(new_job)
    session.commit()

    job_queue.put((str(new_job.job_id), review_req.dict()))
    return str(new_job.job_id)


def process_jobs_in_background() -> None:
    while True:
        job_id, review_req_dict = job_queue.get()
        logger.info(f"Dequeued job {job_id} for processing.")
        _process_single_job(job_id, review_req_dict)


def _process_single_job(job_id: str, review_req_dict: dict) -> None:
    from .database import SessionLocal

    with SessionLocal() as session:
        job = session.query(ReviewJobs).filter(ReviewJobs.job_id == job_id).first()
        if not job or job.status not in ("queued", "in_progress"):
            logger.info(f"Job {job_id} not found or no longer valid.")
            return

        job.status = "in_progress"
        session.commit()

        try:
            review_req = ReviewRequest(**review_req_dict)
            from .llm_engines.ollama_engine import OllamaEngine

            engine = OllamaEngine()

            prompt_str = _format_prompt(review_req.language, review_req.sourceCode, review_req.diff)
            raw_output = engine.generate_review(prompt_str)
            cat_data = _parse_llm_output(raw_output)

            new_review = Reviews(
                language=review_req.language,
                source_code=review_req.sourceCode,
                diff=review_req.diff,
                file_name=review_req.fileName,
                options=review_req.options,
            )
            session.add(new_review)
            session.flush()  # get review_id

            for cat_item in cat_data:
                rc = ReviewCategories(
                    review_id=new_review.review_id, category_name=cat_item["category"], message=cat_item["message"]
                )
                session.add(rc)
            session.commit()

            job.review_id = new_review.review_id
            job.status = "completed"
            job.completed_at = datetime.utcnow()
            session.commit()

            logger.info(f"Job {job_id} completed with {len(cat_data)} categories.")

        except Exception as ex:
            logger.exception(f"Job {job_id} failed: {ex}")
            job.status = "error"
            session.commit()


# Start the background worker on import
worker_thread = threading.Thread(target=process_jobs_in_background, daemon=True)
worker_thread.start()


def get_job_status(session: Session, job_id: str) -> dict | None:
    """
    Get the status of a job and its review results if completed.
    Uses format_review_response for consistent response formatting.
    """
    job = session.query(ReviewJobs).filter(ReviewJobs.job_id == job_id).first()
    if not job:
        return None

    resp = {
        "jobId": str(job.job_id),
        "status": job.status,
        "reviewId": str(job.review_id) if job.review_id else None,  # Include reviewId
    }

    if job.status == "completed" and job.review_id:
        review = session.query(Reviews).filter(Reviews.review_id == job.review_id).first()
        if review:
            formatted_response = format_review_response(review)
            resp["reviews"] = formatted_response["reviews"]

    return resp


def cancel_job(session: Session, job_id: str) -> dict | None:
    job = session.query(ReviewJobs).filter(ReviewJobs.job_id == job_id).first()
    if not job:
        return None
    if job.status in ["completed", "canceled", "error"]:
        return None

    job.status = "canceled"
    job.completed_at = datetime.utcnow()
    session.commit()

    return {"jobId": str(job.job_id), "status": job.status, "message": "Job has been canceled."}


# -----------------------------------------
# Synchronous (Legacy) Code Review
# -----------------------------------------
def generate_and_save_review(
    session: Session,
    llm_engine: BaseLLMEngine,
    language_str: str,
    sourcecode_str: str,
    diff_str: str | None = None,
    filename_str: str | None = None,
    options_dict: dict | None = None,
    prompt_str: str | None = None,
) -> dict:
    """
    Synchronously calls the LLM to generate multiple categories and returns formatted response.

    Args:
        session: Database session
        llm_engine: LLM engine instance
        language_str: Programming language of code to review
        sourcecode_str: Source code to review
        diff_str: Optional diff information
        filename_str: Optional filename
        options_dict: Optional additional options
        prompt_str: Optional custom prompt (if None, one will be generated)

    Returns:
        Dict: Formatted review response with reviewId and reviews
    """
    try:
        if prompt_str is None:
            # In case we want to pass a custom prompt
            prompt_str = _format_prompt(language_str, sourcecode_str, diff_str)

        if DEBUG_MODE:
            logger.debug(f"Synchronous Review Prompt:\n{prompt_str}")

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(llm_engine.generate_review, prompt_str)
            raw_output = future.result()

        cat_data = _parse_llm_output(raw_output)

        new_review = Reviews(
            language=language_str,
            source_code=sourcecode_str,
            diff=diff_str,
            file_name=filename_str,
            options=options_dict,
        )
        session.add(new_review)
        session.flush()

        for cat_item in cat_data:
            rc = ReviewCategories(
                review_id=new_review.review_id, category_name=cat_item["category"], message=cat_item["message"]
            )
            session.add(rc)

        session.commit()
        session.refresh(new_review)

        if DEBUG_MODE:
            logger.debug(f"Synchronous review created. ID: {new_review.review_id}")

        # Format the review response before returning
        return format_review_response(new_review)

    except Exception as e:
        logger.exception(f"Error occurred while generating or saving the review: {e!s}")
        session.rollback()
        raise


def save_feedback(session: Session, review_id_str: str, feedback_list: list[tuple[str, str]]) -> dict:
    """
    Saves user feedback to the database after verifying the review exists.

    Args:
        session: Database session
        review_id_str: Review ID to save feedback for
        feedback_list: List of tuples with (category_name, feedback_value)

    Returns:
        Dict: Success response with review ID and count of feedback items saved

    Raises:
        HTTPException: If review not found or other error occurs
    """
    try:
        review = session.query(Reviews).filter(Reviews.review_id == review_id_str).first()
        if not review:
            raise ValueError(f"Review with ID {review_id_str} not found.")

        saved_count = 0
        for category_name, feedback_value in feedback_list:
            fb = ReviewFeedback(review_id=review_id_str, category_name=category_name, user_feedback=feedback_value)
            session.add(fb)
            saved_count += 1

        session.commit()

        return {"reviewId": review_id_str, "status": "success", "feedbackSaved": saved_count}

    except ValueError as e:
        logger.error(f"Error while saving feedback: {e}")
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail=str(e))

    except Exception as e:
        logger.exception(f"Error occurred while saving feedback: {e!s}")
        session.rollback()
        from fastapi import HTTPException

        raise HTTPException(status_code=500, detail="Failed to save feedback")


# -----------------------------------------
# API Layer Functions (for FastAPI routes)
# -----------------------------------------


async def create_review(session: Session, review_req: ReviewRequest, async_mode: bool = False) -> dict:
    """
    API function to create a new code review (either sync or async)

    Args:
        session: Database session
        review_req: Review request data
        async_mode: Whether to process asynchronously (True) or synchronously (False)

    Returns:
        Dict: Response with either job ID (async) or complete review (sync)
    """
    if async_mode:
        job_id = queue_review_job(session, review_req)
        return {"jobId": job_id, "status": "queued"}
    from .llm_engines.ollama_engine import OllamaEngine

    engine = OllamaEngine()

    result = generate_and_save_review(
        session=session,
        llm_engine=engine,
        language_str=review_req.language,
        sourcecode_str=review_req.sourceCode,
        diff_str=review_req.diff,
        filename_str=review_req.fileName,
        options_dict=review_req.options,
    )

    return result


async def get_review_status(session: Session, job_id: str) -> dict:
    """
    API function to get the status of an asynchronous review job

    Args:
        session: Database session
        job_id: Job ID to query

    Returns:
        Dict: Job status and review data if completed

    Raises:
        HTTPException: If job not found
    """
    result = get_job_status(session, job_id)
    if not result:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail=f"Job with ID {job_id} not found")

    return result


async def get_review_by_id(session: Session, review_id: str) -> dict:
    """
    API function to get a review by its ID

    Args:
        session: Database session
        review_id: Review ID to fetch

    Returns:
        Dict: Formatted review data

    Raises:
        HTTPException: If review not found
    """
    review = session.query(Reviews).filter(Reviews.review_id == review_id).first()
    if not review:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail=f"Review with ID {review_id} not found")

    return format_review_response(review)


async def submit_feedback(session: Session, review_id: str, feedback_data: list[dict[str, str]]) -> dict:
    """
    API function to submit feedback for a review

    Args:
        session: Database session
        review_id: Review ID to provide feedback for
        feedback_data: List of category/feedback pairs

    Returns:
        Dict: Success response
    """
    # Convert the feedback data to the expected format
    feedback_list = [(item["category"], item["feedback"]) for item in feedback_data]

    return save_feedback(session, review_id, feedback_list)
