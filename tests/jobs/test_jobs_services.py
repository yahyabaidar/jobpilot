from unittest.mock import patch

import pytest

from apps.jobs.models import JobOffer
from apps.jobs.services import extract_job_offer, upsert_job_offer

SAMPLE_DATA = {
    "source": "remotive",
    "external_id": "999",
    "title": "Data Engineer",
    "company": "Acme",
    "location": "Remote",
    "remote": True,
    "description": "desc",
    "url": "https://example.com/jobs/999",
    "salary": "",
    "tags": ["sql"],
    "published_at": None,
    "language": "en",
}


@pytest.mark.django_db
def test_upsert_job_offer_is_idempotent():
    offer1, created1 = upsert_job_offer(SAMPLE_DATA)
    offer2, created2 = upsert_job_offer({**SAMPLE_DATA, "title": "Senior Data Engineer"})

    assert created1 is True
    assert created2 is False
    assert JobOffer.objects.count() == 1
    assert offer1.pk == offer2.pk
    assert JobOffer.objects.get(pk=offer1.pk).title == "Senior Data Engineer"


@patch("apps.jobs.services.complete_json")
def test_extract_job_offer_uses_mocked_llm(mock_complete_json):
    mock_complete_json.return_value = {
        "titre": "Ingénieur Data",
        "entreprise": "DataCo",
        "lieu": "Lyon",
        "teletravail": True,
        "competences": ["Python", "SQL"],
        "langue": "fr",
        "salaire": "40-50k",
        "resume": "Résumé court.",
    }

    data = extract_job_offer("texte de l'offre")

    assert data["title"] == "Ingénieur Data"
    assert data["company"] == "DataCo"
    assert data["remote"] is True
    assert data["tags"] == ["Python", "SQL"]
    mock_complete_json.assert_called_once()
