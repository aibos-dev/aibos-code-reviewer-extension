"""
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

STANDARD_CATEGORIES = ["Memory Management", "Performance", "Null Check", "Security", "Coding Standard"]
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"


def _format_prompt(language: str, source_code: str, diff: str | None) -> str:
    """
    Provide a prompt that instructs the LLM to return JSON with multiple categories.
    We mention 5 standard categories, but the LLM can still produce others.
    """
    instructions = (
        "Return only valid JSON in this format:\n"
        "[\n"
        "  {\n"
        '    "category": "(one of Memory Management, Performance, Null Check, Security, Coding Standard, or any other)",\n'
        '    "message": "<explanation>"\n'
        "  },\n"
        "  ...\n"
        "]\n"
        "Do not include extra text."
    )

    base_prompt = (
        f"Please review the following {language} code:\n\n"
        f"{source_code}\n\n"
        f"Diff:\n{diff or ''}\n\n"
        f"Categories of interest: {STANDARD_CATEGORIES}\n"
    )
    return base_prompt + instructions


def _parse_llm_output(raw_output: str) -> list[dict]:
    """
    Attempt to parse LLM output as JSON with multiple categories.
    Fallback to single category if parse fails.
    """
    try:
        data = json.loads(raw_output)
        if not isinstance(data, list):
            data = [data]

        result = []
        for item in data:
            c = item.get("category", "General Feedback")
            m = item.get("message", raw_output[:200])
            result.append({"category": c, "message": m})

        if DEBUG_MODE:
            logger.debug(f"Parsed LLM output as multiple categories: {result}")

        return result

    except Exception as e:
        logger.warning(f"Failed to parse LLM JSON. Fallback to single category. Error: {e}")
        fallback = [{"category": "General Feedback", "message": raw_output[:300]}]
        if DEBUG_MODE:
            logger.debug(f"Falling back to single category: {fallback}")
        return fallback


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
    job = session.query(ReviewJobs).filter(ReviewJobs.job_id == job_id).first()
    if not job:
        return None

    resp = {"jobId": str(job.job_id), "status": job.status}
    if job.status == "completed":
        review = session.query(Reviews).filter(Reviews.review_id == job.review_id).first()
        if review:
            cats = []
            for c in review.categories:
                cats.append({"category": c.category_name, "message": c.message})
            resp["reviews"] = cats

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
    diff_str: str | None,
    filename_str: str | None,
    options_dict: dict | None,
    prompt_str: str = None,
) -> Reviews:
    """
    Synchronously calls the LLM to generate multiple categories.
    'prompt_str' is optional. If None, we'll format a new prompt ourselves.
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

        return new_review

    except Exception:
        logger.exception("Error occurred while generating or saving the review.")
        session.rollback()
        raise


def save_feedback(session: Session, review_id_str: str, feedback_list: list[tuple[str, str]]) -> None:
    """
    Saves user feedback to the database after verifying the review exists.
    """
    try:
        review = session.query(Reviews).filter(Reviews.review_id == review_id_str).first()
        if not review:
            raise ValueError(f"Review with ID {review_id_str} not found.")

        for category_name, feedback_value in feedback_list:
            fb = ReviewFeedback(review_id=review_id_str, category_name=category_name, user_feedback=feedback_value)
            session.add(fb)
        session.commit()

    except ValueError as e:
        logger.error(f"Error while saving feedback: {e}")
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail=str(e))

    except Exception:
        logger.exception("Error occurred while saving feedback.")
        session.rollback()
        raise
