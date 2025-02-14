"""
Database Table Definitions
==========================

Defines tables for PostgreSQL using SQLAlchemy.
The schema follows "LLM Code Review System - Database Schema Documentation".
"""

import uuid

from sqlalchemy import (
    JSON,
    TIMESTAMP,
    Column,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import BIGSERIAL, UUID
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()


class Reviews(Base):
    """
    Reviews Table
    -------------
    - review_id: Unique ID for the review
    - language: Programming language of the source code
    - source_code: Full source code text
    - diff: Code diff information
    - file_name: Filename
    - options: JSON for additional options
    - created_at: Timestamp when the review was created
    - model_id: (Optional) references the model used
    """

    __tablename__ = "reviews"

    review_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    language = Column(String(50), nullable=False)
    source_code = Column(Text, nullable=False)
    diff = Column(Text, nullable=True)
    file_name = Column(String(255), nullable=True)
    options = Column(JSON, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    model_id = Column(UUID(as_uuid=True), ForeignKey("models.model_id"), nullable=True)

    categories = relationship("ReviewCategories", back_populates="review", cascade="all, delete")
    feedbacks = relationship("ReviewFeedback", back_populates="review", cascade="all, delete")


class ReviewCategories(Base):
    """
    ReviewCategories Table
    ----------------------
    - id: Primary key
    - review_id: Foreign key to Reviews table
    - category_name: Category name (e.g., "Memory Management")
    - message: Feedback message for that category
    - created_at: Timestamp
    """

    __tablename__ = "review_categories"

    id = Column(BIGSERIAL, primary_key=True, autoincrement=True)
    review_id = Column(UUID(as_uuid=True), ForeignKey("reviews.review_id"), nullable=False)
    category_name = Column(String(100), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    review = relationship("Reviews", back_populates="categories")


class ReviewFeedback(Base):
    """
    ReviewFeedback Table
    --------------------
    - feedback_id: Primary key
    - review_id: Foreign key to Reviews table
    - category_name: Category for which the feedback is given
    - user_feedback: e.g., "Good"/"Bad"
    - created_at: Timestamp
    """

    __tablename__ = "review_feedback"

    feedback_id = Column(BIGSERIAL, primary_key=True, autoincrement=True)
    review_id = Column(UUID(as_uuid=True), ForeignKey("reviews.review_id"), nullable=False)
    category_name = Column(String(100), nullable=False)
    user_feedback = Column(String(10), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    review = relationship("Reviews", back_populates="feedbacks")


class Models(Base):
    """
    Models Table (Optional)
    -----------------------
    - model_id: Unique model ID
    - name: Human-readable model name
    - version: Model version
    - hosted_by: Hosting environment (e.g., "Ollama")
    - description: Description of the model
    - created_at: Timestamp
    """

    __tablename__ = "models"

    model_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name = Column(String(150), nullable=False)
    version = Column(String(50), nullable=True)
    hosted_by = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
