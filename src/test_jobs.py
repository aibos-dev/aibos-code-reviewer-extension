import csv
import json

import pytest
from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)
_test_results = {}  # Store test outcomes globally


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
    assert response.status_code == 200
    return response.json()["jobId"]


@pytest.fixture(scope="session")
def updated_test_data(job_id_fixture, load_test_data):
    """Replaces {jobId} in test_data.json with actual jobId."""
    for key, entry in load_test_data.items():
        if "{jobId}" in entry["endpoint"]:
            entry["endpoint"] = entry["endpoint"].replace("{jobId}", job_id_fixture)
    return load_test_data


@pytest.mark.parametrize("test_id", ["A-1", "A-2", "A-3", "A-4", "A-5"])
def test_job_creation(test_id, updated_test_data):
    """Tests job creation scenarios."""
    data = updated_test_data[test_id]
    response = client.post(data["endpoint"], json=data.get("request_body", {}))
    assert response.status_code in [200, 201, 400]
    record_result(test_id, response.status_code in [200, 201])


@pytest.mark.parametrize("test_id", ["B-1", "B-2", "B-3", "B-4"])
def test_job_status(test_id, updated_test_data):
    """Tests job status retrieval."""
    data = updated_test_data[test_id]
    response = client.get(data["endpoint"])
    assert response.status_code in [200, 404, 422]
    record_result(test_id, response.status_code == 200)


@pytest.mark.parametrize("test_id", ["C-1", "C-2", "C-3", "C-4", "C-5"])
def test_job_cancel(test_id, updated_test_data):
    """Tests job cancellation."""
    data = updated_test_data[test_id]
    response = client.put(data["endpoint"], json=data["request_body"])
    assert response.status_code in [200, 400, 409, 404]
    record_result(test_id, response.status_code == 200)
