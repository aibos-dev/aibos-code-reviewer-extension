"""
Business Logic Layer
====================

Handles:
- Synchronous code review generation (generate_and_save_review)
- Feedback saving (save_feedback)
- NEW: Job queue processing (async) for v0.2
"""

import logging
import threading
import uuid
from queue import Queue
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy.orm import Session

from .llm_engines.base import BaseLLMEngine
from .models_db import (
    ReviewJobs,
    Reviews,
    ReviewCategories,
    ReviewFeedback,
)
from .schemas import ReviewRequest

logger = logging.getLogger(__name__)

# In-memory job queue
job_queue = Queue()


def queue_review_job(session: Session, review_req: ReviewRequest) -> str:
    """
    Creates a new job in DB with status=queued, then puts it on the in-memory queue.
    Returns the newly created job_id (UUID).
    """
    new_job = ReviewJobs()
    session.add(new_job)
    session.commit()  # We have a valid job_id now

    job_queue.put((str(new_job.job_id), review_req.dict()))
    return str(new_job.job_id)


def process_jobs_in_background() -> None:
    """
    Background worker that continually processes jobs from the queue (FIFO).
    """
    while True:
        job_id, review_req_dict = job_queue.get()  # blocking call
        logger.info(f"Dequeued job {job_id} for processing.")
        _process_single_job(job_id, review_req_dict)


def _process_single_job(job_id: str, review_req_dict: dict) -> None:
    """
    Processes a single job: calls the LLM engine, saves results, updates job status.
    """
    from .database import SessionLocal  # avoid circular imports
    with SessionLocal() as session:
        # Check if job was canceled or still queued
        job = session.query(ReviewJobs).filter(ReviewJobs.job_id == job_id).first()
        if not job or job.status not in ("queued", "in_progress"):
            logger.info(f"Job {job_id} not found or no longer valid for processing.")
            return

        # Mark job in_progress
        job.status = "in_progress"
        session.commit()

        try:
            review_req = ReviewRequest(**review_req_dict)
            prompt_str = (
                f"Please review the following {review_req.language} code:\n\n"
                f"{review_req.sourceCode}\n\n"
                f"Diff:\n{review_req.diff}"
            )

            # Generate code review using LLM
            from .llm_engines.ollama_engine import OllamaEngine
            llm_engine = OllamaEngine()

            # We can run it synchronously here, or also use a thread pool
            llm_result = llm_engine.generate_review(prompt_str)

            # Save to 'reviews' table
            new_review = Reviews(
                language=review_req.language,
                source_code=review_req.sourceCode,
                diff=review_req.diff,
                file_name=review_req.fileName,
                options=review_req.options,
            )
            session.add(new_review)
            session.flush()  # get new_review.review_id

            # Example: Create 1 default category item
            cat = ReviewCategories(
                review_id=new_review.review_id,
                category_name="General Feedback",
                message=llm_result[:200]
            )
            session.add(cat)
            session.commit()

            # Link the job to the newly created review
            job.review_id = new_review.review_id
            job.status = "completed"
            job.completed_at = datetime.utcnow()
            session.commit()

            logger.info(f"Job {job_id} completed successfully.")
        except Exception as ex:
            logger.exception(f"Job {job_id} failed: {ex}")
            job.status = "error"
            session.commit()


# Start background worker thread (daemon = True)
worker_thread = threading.Thread(target=process_jobs_in_background, daemon=True)
worker_thread.start()


def generate_and_save_review(
    session: Session,
    llm_engine: BaseLLMEngine,
    prompt_str: str,
    language_str: str,
    sourcecode_str: str,
    diff_str: str | None,
    filename_str: str | None,
    options_dict: dict | None,
) -> Reviews:
    """
    Generates a code review using an LLM engine and saves the result to DB.
    Synchronous approach (old logic).
    """
    try:
        # Parallelize with ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(llm_engine.generate_review, prompt_str)
            llm_result = future.result()

        # Insert a new review record
        new_review = Reviews(
            language=language_str,
            source_code=sourcecode_str,
            diff=diff_str,
            file_name=filename_str,
            options=options_dict,
        )
        session.add(new_review)
        session.flush()

        # Create a single category item as an example
        cat = ReviewCategories(
            review_id=new_review.review_id,
            category_name="General Feedback",
            message=llm_result[:200],
        )
        session.add(cat)

        session.commit()
        session.refresh(new_review)
        return new_review

    except Exception:
        logger.exception("Error occurred while generating or saving the review.")
        session.rollback()
        raise


def save_feedback(
    session: Session,
    review_id_str: str,
    feedback_list: list[tuple[str, str]]
) -> None:
    """
    Saves user feedback to the database.
    """
    try:
        for category_name, feedback_value in feedback_list:
            fb = ReviewFeedback(
                review_id=review_id_str,
                category_name=category_name,
                user_feedback=feedback_value
            )
            session.add(fb)
        session.commit()
    except Exception:
        logger.exception("Error occurred while saving feedback.")
        session.rollback()
        raise


def get_job_status(session: Session, job_id: str) -> dict | None:
    """
    Retrieves the job status from DB, plus partial or final results if completed.
    """
    job = session.query(ReviewJobs).filter(ReviewJobs.job_id == job_id).first()
    if not job:
        return None

    response = {
        "jobId": str(job.job_id),
        "status": job.status,
    }

    if job.status == "completed":
        # Return the stored review results
        review = session.query(Reviews).filter(Reviews.review_id == job.review_id).first()
        if review:
            # For demonstration, return categories
            cats = []
            for c in review.categories:
                cats.append({"category": c.category_name, "message": c.message})
            response["reviews"] = cats

    return response


def cancel_job(session: Session, job_id: str) -> dict | None:
    """
    Cancels a queued or in_progress job by updating status to 'canceled'.
    """
    job = session.query(ReviewJobs).filter(ReviewJobs.job_id == job_id).first()
    if not job:
        return None
    if job.status in ["completed", "canceled", "error"]:
        return None  # can't re-cancel or revert a done job

    job.status = "canceled"
    job.completed_at = datetime.utcnow()
    session.commit()

    return {
        "jobId": str(job.job_id),
        "status": job.status,
        "message": "Job has been canceled."
    }
