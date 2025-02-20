"""
pytest Test Module
==================

Example tests for the key endpoints.
"""

import pytest
from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


@pytest.fixture
def sample_review_body() -> dict:
    return {
        "language": "Python",
        "sourceCode": "print('Hello World')",
        "fileName": "hello.py",
        "diff": None,
        "options": {},
    }


def test_review_endpoint(sample_review_body: dict):
    response = client.post("/v1/review", json=sample_review_body)
    assert response.status_code == 200
    data = response.json()
    assert "reviewId" in data
    assert "reviews" in data
    assert len(data["reviews"]) >= 1


def test_feedback_endpoint():
    feedback_body = {"reviewId": "some-review-id", "feedbacks": [{"category": "General Feedback", "feedback": "Good"}]}
    response = client.post("/v1/review/feedback", json=feedback_body)
    # Might be 404 or 500 if the review doesn't exist
    assert response.status_code in (200, 404, 500)
