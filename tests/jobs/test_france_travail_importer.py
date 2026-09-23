from unittest.mock import Mock, patch

import pytest
import requests

from apps.jobs.importers.base import ImporterError
from apps.jobs.importers.france_travail import FranceTravailImporter

SAMPLE_OFFER = {
    "id": "123ABC",
    "intitule": "Stagiaire Développeur Python",
    "description": "<p>Stage de fin d'études en développement Python/Django.</p>",
    "dateCreation": "2026-01-15T10:00:00.000Z",
    "lieuTravail": {"libelle": "Paris (75)", "commune": "75056"},
    "romeCode": "M1805",
    "romeLibelle": "Études et développement informatique",
    "entreprise": {"nom": "TechFR"},
    "typeContrat": "MIS",
    "typeContratLibelle": "Stage",
    "alternance": False,
    "salaire": {"libelle": "Selon profil"},
    "competences": [{"code": "123", "libelle": "Python"}, {"code": "124", "libelle": "Django"}],
    "origineOffre": {"origine": "1", "urlOrigine": "https://candidat.francetravail.fr/offres/123"},
}


def _token_response():
    response = Mock()
    response.raise_for_status = Mock()
    response.json.return_value = {"access_token": "fake-token", "expires_in": 1200}
    return response


def _search_response(status_code=200):
    response = Mock()
    response.status_code = status_code
    response.raise_for_status = Mock()
    response.json.return_value = {"resultats": [SAMPLE_OFFER]}
    return response


@pytest.fixture
def with_credentials(settings):
    settings.FRANCE_TRAVAIL_CLIENT_ID = "client-id"
    settings.FRANCE_TRAVAIL_CLIENT_SECRET = "client-secret"


def test_fetch_without_credentials_is_disabled_gracefully(settings):
    settings.FRANCE_TRAVAIL_CLIENT_ID = ""
    settings.FRANCE_TRAVAIL_CLIENT_SECRET = ""

    with pytest.raises(ImporterError, match="n'est pas configuré"):
        FranceTravailImporter().fetch(limit=10)


@patch("apps.jobs.importers.france_travail.requests.get")
@patch("apps.jobs.importers.france_travail.requests.post")
def test_fetch_normalizes_real_shaped_response(mock_post, mock_get, with_credentials):
    mock_post.return_value = _token_response()
    mock_get.return_value = _search_response()

    jobs = FranceTravailImporter().fetch(limit=10)

    assert len(jobs) == 1
    job = jobs[0]
    assert job["source"] == "france_travail"
    assert job["external_id"] == "123ABC"
    assert job["title"] == "Stagiaire Développeur Python"
    assert job["company"] == "TechFR"
    assert job["location"] == "Paris (75)"
    assert job["url"] == "https://candidat.francetravail.fr/offres/123"
    assert job["tags"] == ["Python", "Django"]
    assert job["contract_type"] == "stage"
    assert job["published_at"] is not None

    # token request used client_credentials grant with the confirmed scope shape
    _, token_kwargs = mock_post.call_args
    assert token_kwargs["data"]["grant_type"] == "client_credentials"
    assert "api_offresdemploiv2" in token_kwargs["data"]["scope"]


@patch("apps.jobs.importers.france_travail.requests.get")
@patch("apps.jobs.importers.france_travail.requests.post")
def test_fetch_handles_206_partial_content(mock_post, mock_get, with_credentials):
    mock_post.return_value = _token_response()
    mock_get.return_value = _search_response(status_code=206)

    jobs = FranceTravailImporter().fetch(limit=10)

    assert len(jobs) == 1


@patch("apps.jobs.importers.france_travail.requests.post")
def test_fetch_raises_importer_error_on_auth_failure(mock_post, with_credentials):
    response = Mock()
    response.raise_for_status.side_effect = requests.HTTPError("401 Unauthorized")
    mock_post.return_value = response

    with pytest.raises(ImporterError):
        FranceTravailImporter().fetch(limit=10)


@patch("apps.jobs.importers.france_travail.requests.get")
@patch("apps.jobs.importers.france_travail.requests.post")
def test_fetch_raises_importer_error_on_unexpected_payload(mock_post, mock_get, with_credentials):
    mock_post.return_value = _token_response()
    bad_response = Mock()
    bad_response.status_code = 200
    bad_response.raise_for_status = Mock()
    bad_response.json.return_value = {"unexpected": "shape"}
    mock_get.return_value = bad_response

    with pytest.raises(ImporterError):
        FranceTravailImporter().fetch(limit=10)
