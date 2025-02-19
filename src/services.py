"""
Business Logic Layer
====================

Handles calls to the LLM engine, shaping review results, and saving to the database.
"""

import logging
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy.orm import Session

from .llm_engines.base import BaseLLMEngine
from .models_db import ReviewCategories, ReviewFeedback, Reviews

logger = logging.getLogger(__name__)


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
    Generates a code review using an LLM engine and saves the result to the DB.

    Parameters
    ----------
    session : Session
        The DB session.
    llm_engine : BaseLLMEngine
        The LLM engine to use for inference.
    prompt_str : str
        The prompt given to the LLM.
    language_str : str
        The programming language of the source code.
    sourcecode_str : str
        The full source code.
    diff_str : str | None
        Code diff information (if any).
    filename_str : str | None
        The file name being reviewed (if any).
    options_dict : dict | None
        Additional review options.

    Returns
    -------
    Reviews
        The newly created review object.
    """
    try:
        # Parallelize with ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(llm_engine.generate_review, prompt_str)
            llm_result = future.result()  # Wait for inference

        # Create and insert a new review record
        new_review = Reviews(
            language=language_str,
            source_code=sourcecode_str,
            diff=diff_str,
            file_name=filename_str,
            options=options_dict,
        )
        session.add(new_review)
        session.flush()

        # Create a single category from the LLM output (example)
        cat = ReviewCategories(
            review_id=new_review.review_id,
            category_name="General Feedback",
            message=llm_result[:200],  # first 200 characters from LLM output
        )
        session.add(cat)

        session.commit()
        session.refresh(new_review)
        return new_review

    except Exception:
        logger.exception("Error occurred while generating or saving the review.")
        session.rollback()
        raise


def save_feedback(session: Session, review_id_str: str, feedback_list: list[tuple[str, str]]) -> None:
    """
    Saves user feedback to the database.

    Parameters
    ----------
    session : Session
        The DB session.
    review_id_str : str
        The ID of the review being updated.
    feedback_list : list[tuple[str, str]]
        A list of (category_name, feedback) tuples.

    Returns
    -------
    None
    """
    try:
        for category_name, feedback_value in feedback_list:
            fb = ReviewFeedback(review_id=review_id_str, category_name=category_name, user_feedback=feedback_value)
            session.add(fb)
        session.commit()
    except Exception:
        logger.exception("Error occurred while saving feedback.")
        session.rollback()
        raise
