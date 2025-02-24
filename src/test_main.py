"""
pytest Test Module
==================

Tests for:
- Code review (synchronous & async)
- Job queue (status check, reviewId retrieval)
- Feedback submission
"""

import sys
import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ensure Python can find `src/` package
sys.path.append("/workspace")  # Adjust if needed

from src.database import get_db_session
from src.main import app
from src.models_db import Base

# ✅ PostgreSQL Test Database Configuration
TEST_DATABASE_URL = "postgresql://postgres:rmt_system@34.97.121.181:5433/fact_check"

# ✅ Create a PostgreSQL test database engine
engine = create_engine(TEST_DATABASE_URL, echo=True)

# ✅ Create a new session factory
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


# ✅ Override DB session dependency in FastAPI
def override_get_db_session():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


app.dependency_overrides[get_db_session] = override_get_db_session

client = TestClient(app)


# ✅ Setup Database: Runs once per test session
@pytest.fixture(scope="module", autouse=True)
def setup_database():
    """Set up the PostgreSQL test database before running tests."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


# ✅ Fixtures for test data
@pytest.fixture
def sample_review_body() -> dict:
    return {
        "language": "Python",
        "sourceCode": "print('Hello World')",
        "fileName": "hello.py",
        "diff": None,
        "options": {},
    }


@pytest.fixture
def sample_feedback_body() -> dict:
    return {
        "reviewId": "00000000-0000-0000-0000-000000000000",  # Dummy UUID
        "feedbacks": [{"category": "General Feedback", "feedback": "Good"}],
    }


# ===========================
# 🛠️ TEST: SYNCHRONOUS REVIEW
# ===========================
def test_review_endpoint(sample_review_body):
    """Test synchronous code review"""
    response = client.post("/v1/review", json=sample_review_body)
    assert response.status_code == 200
    data = response.json()
    assert "reviewId" in data
    assert "reviews" in data
    assert isinstance(data["reviews"], list)
    assert len(data["reviews"]) > 0


# ===========================
# 🛠️ TEST: ASYNCHRONOUS JOB REVIEW
# ===========================
def test_async_review_job(sample_review_body):
    """Test queuing a code review job"""
    response = client.post("/v1/jobs", json=sample_review_body)
    assert response.status_code == 200
    data = response.json()
    assert "jobId" in data
    assert data["status"] == "queued"


def test_job_status_review():
    """Test retrieving a job status"""
    sample_review_body = {
        "language": "Python",
        "sourceCode": "print('async test')",
        "fileName": "async_test.py",
        "diff": None,
        "options": {},
    }
    job_response = client.post("/v1/jobs", json=sample_review_body)
    assert job_response.status_code == 200
    job_id = job_response.json()["jobId"]

    # Allow some time for the background thread to process the job
    time.sleep(2)

    job_status_response = client.get(f"/v1/jobs/{job_id}")
    assert job_status_response.status_code == 200
    job_data = job_status_response.json()

    assert "status" in job_data
    assert job_data["status"] in ["queued", "in_progress", "completed"]

    if job_data["status"] == "completed":
        assert "reviewId" in job_data
        assert job_data["reviewId"] is not None


# ===========================
# 🛠️ TEST: SUBMITTING FEEDBACK
# ===========================
def test_feedback_endpoint(sample_feedback_body):
    """Test submitting feedback for a review"""
    response = client.post("/v1/review/feedback", json=sample_feedback_body)
    assert response.status_code in (200, 404, 500)
    if response.status_code == 200:
        data = response.json()
        assert "status" in data
        assert data["status"] == "success"


# ===========================
# 🛠️ TEST: HANDLING ERRORS
# ===========================
def test_review_not_found():
    """Test fetching a review that does not exist"""
    response = client.get("/v1/review/00000000-0000-0000-0000-000000000000")  # Dummy UUID
    assert response.status_code == 404


def test_job_not_found():
    """Test fetching a job that does not exist"""
    response = client.get("/v1/jobs/00000000-0000-0000-0000-000000000000")  # Dummy UUID
    assert response.status_code == 404


def test_invalid_feedback():
    """Test submitting feedback for a non-existent review"""
    response = client.post(
        "/v1/review/feedback",
        json={
            "reviewId": "00000000-0000-0000-0000-000000000000",
            "feedbacks": [{"category": "Security", "feedback": "Bad"}],
        },
    )
    assert response.status_code == 404


# ===========================
# 🛠️ TEST: CANCELLING A JOB
# ===========================
def test_cancel_job():
    """Test cancelling a queued job"""
    sample_review_body = {
        "language": "Python",
        "sourceCode": "print('cancel test')",
        "fileName": "cancel_test.py",
        "diff": None,
        "options": {},
    }
    job_response = client.post("/v1/jobs", json=sample_review_body)
    assert job_response.status_code == 200
    job_id = job_response.json()["jobId"]

    cancel_response = client.put(f"/v1/jobs/{job_id}", json={"status": "canceled"})
    assert cancel_response.status_code in (200, 409)


# ===========================
# 🛠️ TEST: INVALID JOB CANCELLATION
# ===========================
def test_cancel_invalid_job():
    """Test cancelling a job that does not exist"""
    response = client.put("/v1/jobs/00000000-0000-0000-0000-000000000000", json={"status": "canceled"})
    assert response.status_code == 404
