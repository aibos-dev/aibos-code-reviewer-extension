"""
Database Table Definitions
==========================

Defines tables for PostgreSQL using SQLAlchemy.
Includes:
- Reviews, ReviewCategories, ReviewFeedback, Models
- NEW: ReviewJobs for job queue tracking.
"""

import uuid
from sqlalchemy import (
    JSON,
    TIMESTAMP,
    BigInteger,
    Column,
    ForeignKey,
    String,
    Text,
    Enum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()


class ReviewJobs(Base):
    """
    ReviewJobs Table
    ----------------
    - job_id: Unique ID for the job
    - status: queued, in_progress, completed, canceled, error
    - created_at: When the job was created
    - completed_at: When the job completed or canceled
    - review_id: (Optional) references the Reviews table
    """

    __tablename__ = "review_jobs"

    job_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )
    status = Column(
        Enum("queued", "in_progress", "completed", "canceled", "error", name="job_status"),
        nullable=False,
        default="queued"
    )
    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    completed_at = Column(TIMESTAMP(timezone=True), nullable=True)

    # Link to the Reviews table once the review is complete
    review_id = Column(UUID(as_uuid=True), ForeignKey("reviews.review_id"), nullable=True)
    review = relationship("Reviews", back_populates="job")


class Reviews(Base):
    """
    Reviews Table
    -------------
    - review_id: Unique ID for the review
    - language: Programming language
    - source_code: Full source code text
    - diff: Code diff
    - file_name: Filename
    - options: JSON for additional options
    - created_at: Timestamp
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

    # One-to-one relationship with ReviewJobs
    job = relationship("ReviewJobs", back_populates="review", uselist=False)

    categories = relationship("ReviewCategories", back_populates="review", cascade="all, delete")
    feedbacks = relationship("ReviewFeedback", back_populates="review", cascade="all, delete")


class ReviewCategories(Base):
    """
    ReviewCategories Table
    ----------------------
    - id
    - review_id
    - category_name
    - message
    - created_at
    """

    __tablename__ = "review_categories"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    review_id = Column(UUID(as_uuid=True), ForeignKey("reviews.review_id"), nullable=False)
    category_name = Column(String(100), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    review = relationship("Reviews", back_populates="categories")


class ReviewFeedback(Base):
    """
    ReviewFeedback Table
    --------------------
    - feedback_id
    - review_id
    - category_name
    - user_feedback
    - created_at
    """

    __tablename__ = "review_feedback"

    feedback_id = Column(BigInteger, primary_key=True, autoincrement=True)
    review_id = Column(UUID(as_uuid=True), ForeignKey("reviews.review_id"), nullable=False)
    category_name = Column(String(100), nullable=False)
    user_feedback = Column(String(10), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    review = relationship("Reviews", back_populates="feedbacks")


class Models(Base):
    """
    Models Table
    ------------
    - model_id
    - name
    - version
    - hosted_by
    - description
    - created_at
    """

    __tablename__ = "models"

    model_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name = Column(String(150), nullable=False)
    version = Column(String(50), nullable=True)
    hosted_by = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
