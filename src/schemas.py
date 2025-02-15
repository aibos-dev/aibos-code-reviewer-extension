"""
Pydantic Schema Definitions
===========================

Defines schemas for requests and responses in FastAPI endpoints.
Also shows an example of Tap + Pydantic usage for CLI argument validation.
"""

from typing import Any

from pydantic import BaseModel, Field


class ReviewRequest(BaseModel):
    """
    Input schema for the review API.
    """

    language: str = Field(..., description="Programming language of the source code")
    sourceCode: str = Field(..., description="Full source code text")
    fileName: str | None = Field(None, description="File name")
    diff: str | None = Field(None, description="Diff information")
    options: dict[str, Any] | None = Field(None, description="Additional review options")


class ReviewResponseCategory(BaseModel):
    """
    Represents a single category of review feedback.
    """

    category: str
    message: str


class ReviewResponse(BaseModel):
    """
    Output schema for the review API.
    """

    reviewId: str
    reviews: list[ReviewResponseCategory]


class FeedbackItem(BaseModel):
    """
    Represents user feedback for a single category.
    """

    category: str
    feedback: str


class ReviewFeedbackRequest(BaseModel):
    """
    Input schema for sending user feedback about a review.
    """

    reviewId: str
    feedbacks: list[FeedbackItem]


# === Example: CLI argument validation with Tap + pydantic ===


class CliArgs(BaseModel):
    """
    Example schema for CLI arguments (Tap).
    """

    host: str = Field("0.0.0.0", description="Host to bind the API server")
    port: int = Field(8000, description="Port to bind the API server")
    debug: bool = Field(False, description="Flag for debug mode")
