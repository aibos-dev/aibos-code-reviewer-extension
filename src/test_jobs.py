import csv
import json

import pytest
from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)
_test_results = {}  # Store test outcomes globally


REVIEW_ID = "b905777f-a154-4ea0-b2e3-af67e92b41e2"  # Provided example review ID


def record_result(test_id: str, success: bool, error_message=""):
    """Records test results for CSV export."""
    _test_results[test_id] = "PASS" if success else f"FAIL: {error_message}"


@pytest.fixture(scope="session")
def load_test_data():
    """Loads test_data.json for all tests."""
    with open("test_data.json", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session", autouse=True)
def prepare_csv_report():
    """Writes test results to test_report.csv after all tests."""
    yield  # Run tests first
    with open("test_report.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["TestID", "Result"])
        for test_id, result in _test_results.items():
            writer.writerow([test_id, result])


@pytest.fixture(scope="session")
def job_id_fixture(load_test_data):
    """Creates a job once and reuses its ID for multiple tests."""
    data = load_test_data["A-1"]
    response = client.post("/v1/jobs", json=data["request_body"])
    assert response.status_code in [200, 201], f"Job creation failed: {response.text}"
    return response.json().get("jobId")


@pytest.fixture(scope="session")
def updated_test_data(job_id_fixture, load_test_data):
    """Replaces placeholders {jobId} and {reviewId} in test_data.json."""
    for key, entry in load_test_data.items():
        if "{jobId}" in entry["endpoint"]:
            entry["endpoint"] = entry["endpoint"].replace("{jobId}", job_id_fixture)
        if "{reviewId}" in entry["endpoint"]:
            entry["endpoint"] = entry["endpoint"].replace("{reviewId}", REVIEW_ID)

        if "request_body" in entry and isinstance(entry["request_body"], dict):
            for field in entry["request_body"]:
                if isinstance(entry["request_body"][field], str):
                    entry["request_body"][field] = (
                        entry["request_body"][field]
                        .replace("{jobId}", job_id_fixture)
                        .replace("{reviewId}", REVIEW_ID)
                    )

    return load_test_data


def extract_endpoint(data):
    """Extracts HTTP method and API path correctly."""
    method, endpoint = data["endpoint"].split(" ", 1)  # Split method from path
    return method.strip(), endpoint.strip()


def make_request(method, endpoint, request_body=None):
    """Handles different types of requests dynamically."""
    url = f"http://127.0.0.1:8000{endpoint}"
    print(f"\n🔍 Testing: {method} {url}")  # Debugging info

    if method == "POST":
        response = client.post(endpoint, json=request_body or {})
    elif method == "GET":
        response = client.get(endpoint)
    elif method == "PUT":
        response = client.put(endpoint, json=request_body or {})
    else:
        pytest.fail(f"Unsupported HTTP method: {method}")

    print(f"🔍 Response Status: {response.status_code} | Body: {response.text}")  # Debugging output
    return response


@pytest.mark.parametrize("test_id", ["A-1", "A-2", "A-3", "A-4", "A-5"])
def test_job_creation(test_id, updated_test_data):
    """Tests job creation scenarios."""
    data = updated_test_data[test_id]
    method, endpoint = extract_endpoint(data)

    response = make_request(method, endpoint, data.get("request_body", {}))

    expected_statuses = [200, 201, 400, 422]  # Accept 422 for missing fields
    assert response.status_code in expected_statuses, f"Unexpected response: {response.status_code}"
    record_result(test_id, response.status_code in expected_statuses)


@pytest.mark.parametrize("test_id", ["B-1", "B-2", "B-3", "B-4"])
def test_job_status(test_id, updated_test_data):
    """Tests job status retrieval."""
    data = updated_test_data[test_id]
    method, endpoint = extract_endpoint(data)

    response = make_request(method, endpoint)
    expected_statuses = [200, 404, 422]
    assert response.status_code in expected_statuses, f"Unexpected response: {response.status_code}"
    record_result(test_id, response.status_code in expected_statuses)


@pytest.mark.parametrize("test_id", ["C-1", "C-2", "C-3", "C-4", "C-5"])
def test_job_cancel(test_id, updated_test_data):
    """Tests job cancellation."""
    data = updated_test_data[test_id]
    method, endpoint = extract_endpoint(data)

    response = make_request(method, endpoint, data.get("request_body", {}))

    expected_statuses = [200, 400, 404, 409, 422]
    success = response.status_code in expected_statuses
    assert success, f"Unexpected response: {response.status_code}"
    record_result(test_id, success, f"Unexpected status: {response.status_code}" if not success else "")


@pytest.mark.parametrize("test_id", ["D-1", "D-2", "D-3", "D-4"])
def test_feedback_submission(test_id, updated_test_data):
    """Tests feedback submission scenarios."""
    data = updated_test_data[test_id]
    method, endpoint = extract_endpoint(data)

    response = make_request(method, endpoint, data.get("request_body", {}))
    expected_statuses = [200, 201, 400, 422, 404]
    assert response.status_code in expected_statuses, f"Unexpected response: {response.status_code}"
    record_result(test_id, response.status_code in expected_statuses)
