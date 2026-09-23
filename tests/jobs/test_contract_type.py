from unittest.mock import Mock, patch

from apps.jobs.importers.arbeitnow import ArbeitnowImporter
from apps.jobs.importers.remotive import RemotiveImporter
from apps.jobs.utils import deduce_contract_type


def test_deduce_contract_type_from_french_labels():
    assert deduce_contract_type("Stage") == "stage"
    assert deduce_contract_type("Stage de fin d'études") == "stage"
    assert deduce_contract_type("Contrat d'apprentissage") == "alternance"
    assert deduce_contract_type("CDI") == "cdi"
    assert deduce_contract_type("Contrat à durée indéterminée") == "cdi"
    assert deduce_contract_type("CDD") == "cdd"
    assert deduce_contract_type("Contrat à durée déterminée") == "cdd"
    assert deduce_contract_type("Freelance / indépendant") == "freelance"
    assert deduce_contract_type("") == "inconnu"
    assert deduce_contract_type("Quelque chose d'obscur") == "inconnu"


def test_deduce_contract_type_from_english_labels():
    assert deduce_contract_type("Internship") == "stage"
    assert deduce_contract_type("full_time") == "cdi"
    assert deduce_contract_type("Contract") == "freelance"


def test_deduce_contract_type_recognizes_interim():
    assert deduce_contract_type("Intérim") == "interim"
    assert deduce_contract_type("Mission intérimaire") == "interim"
    assert deduce_contract_type("Technicien hotline (H/F)", is_alternance=False) == "inconnu"


def test_deduce_contract_type_alternance_flag_applies_when_no_stage_wording():
    assert deduce_contract_type("CDI", is_alternance=True) == "alternance"
    assert deduce_contract_type("Alternant Data Analyst", is_alternance=True) == "alternance"


def test_deduce_contract_type_explicit_stage_wins_over_alternance_flag():
    # France Travail flags many "Stage de fin d'études / Alternance" postings with
    # alternance=true; the explicit "stage" wording should still win so these surface in the
    # stage-filtered view.
    assert (
        deduce_contract_type("Stage de fin d'études / Alternance - Sujet", is_alternance=True)
        == "stage"
    )


def _mock_response(json_data):
    response = Mock()
    response.status_code = 200
    response.json.return_value = json_data
    response.raise_for_status = Mock()
    return response


@patch("apps.jobs.importers.remotive.requests.get")
def test_remotive_deduces_contract_type_from_api_response(mock_get):
    mock_get.return_value = _mock_response(
        {
            "jobs": [
                {
                    "id": 1,
                    "url": "https://remotive.com/jobs/1",
                    "title": "Backend Intern",
                    "company_name": "Acme",
                    "job_type": "internship",
                    "description": "<p>Fun internship</p>",
                }
            ]
        }
    )

    jobs = RemotiveImporter().fetch(limit=10)

    assert jobs[0]["contract_type"] == "stage"


@patch("apps.jobs.importers.arbeitnow.requests.get")
def test_arbeitnow_deduces_contract_type_from_tags(mock_get):
    mock_get.return_value = _mock_response(
        {
            "data": [
                {
                    "slug": "internship-1",
                    "company_name": "Acme",
                    "title": "Backend Internship",
                    "description": "desc",
                    "remote": True,
                    "url": "https://arbeitnow.com/jobs/1",
                    "tags": ["Internship", "Backend"],
                    "job_types": [],
                    "location": "Berlin",
                    "created_at": 1735729200,
                }
            ]
        }
    )

    jobs = ArbeitnowImporter().fetch(limit=10)

    assert jobs[0]["contract_type"] == "stage"
