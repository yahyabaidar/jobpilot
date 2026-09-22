from unittest.mock import Mock, patch

import pytest
import requests

from apps.jobs.importers.arbeitnow import ArbeitnowImporter
from apps.jobs.importers.base import ImporterError
from apps.jobs.importers.remotive import RemotiveImporter

REMOTIVE_PAYLOAD = {
    "jobs": [
        {
            "id": 123,
            "url": "https://remotive.com/remote-jobs/x/123",
            "title": "Backend Developer",
            "company_name": "Acme",
            "category": "Software Dev",
            "tags": ["python", "django"],
            "job_type": "full_time",
            "publication_date": "2026-01-01T10:00:00",
            "candidate_required_location": "Worldwide",
            "salary": "$80k - $100k",
            "description": "<p>Great <strong>job</strong>.</p>",
        }
    ]
}

ARBEITNOW_PAYLOAD = {
    "data": [
        {
            "slug": "backend-dev-berlin-123",
            "company_name": "Acme GmbH",
            "title": "Backend Developer",
            "description": "<p>Toller <strong>Job</strong>.</p>",
            "remote": True,
            "url": "https://www.arbeitnow.com/jobs/companies/acme/backend-dev-berlin-123",
            "tags": ["Remote", "Backend"],
            "job_types": ["Full-time"],
            "location": "Berlin",
            "created_at": 1735729200,
        }
    ]
}


def _mock_response(json_data):
    response = Mock()
    response.status_code = 200
    response.json.return_value = json_data
    response.raise_for_status = Mock()
    return response


@patch("apps.jobs.importers.remotive.requests.get")
def test_remotive_normalizes_real_shaped_payload(mock_get):
    mock_get.return_value = _mock_response(REMOTIVE_PAYLOAD)

    jobs = RemotiveImporter().fetch(limit=10)

    assert len(jobs) == 1
    job = jobs[0]
    assert job["source"] == "remotive"
    assert job["external_id"] == "123"
    assert job["title"] == "Backend Developer"
    assert job["company"] == "Acme"
    assert job["remote"] is True
    assert "Great" in job["description"] and "job" in job["description"]
    assert "<p>" not in job["description"]
    assert job["salary"] == "$80k - $100k"
    assert job["tags"] == ["python", "django"]
    assert job["published_at"] is not None


@patch("apps.jobs.importers.remotive.requests.get")
def test_remotive_raises_importer_error_on_unexpected_payload(mock_get):
    mock_get.return_value = _mock_response({"unexpected": "shape"})

    with pytest.raises(ImporterError):
        RemotiveImporter().fetch(limit=10)


@patch("apps.jobs.importers.remotive.requests.get")
def test_remotive_raises_importer_error_on_network_failure(mock_get):
    mock_get.side_effect = requests.Timeout("boom")

    with pytest.raises(ImporterError):
        RemotiveImporter().fetch(limit=10)


@patch("apps.jobs.importers.arbeitnow.requests.get")
def test_arbeitnow_normalizes_real_shaped_payload(mock_get):
    mock_get.return_value = _mock_response(ARBEITNOW_PAYLOAD)

    jobs = ArbeitnowImporter().fetch(limit=10)

    assert len(jobs) == 1
    job = jobs[0]
    assert job["source"] == "arbeitnow"
    assert job["external_id"] == "backend-dev-berlin-123"
    assert job["title"] == "Backend Developer"
    assert job["company"] == "Acme GmbH"
    assert job["remote"] is True
    assert job["location"] == "Berlin"
    assert "Toller" in job["description"] and "Job" in job["description"]
    assert job["published_at"] is not None


@patch("apps.jobs.importers.arbeitnow.requests.get")
def test_arbeitnow_raises_importer_error_on_unexpected_payload(mock_get):
    mock_get.return_value = _mock_response({"unexpected": "shape"})

    with pytest.raises(ImporterError):
        ArbeitnowImporter().fetch(limit=10)
