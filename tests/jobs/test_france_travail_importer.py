from unittest.mock import Mock, patch

import pytest
import requests

from apps.jobs.importers.base import ImporterError
from apps.jobs.importers.france_travail import DEFAULT_KEYWORDS, FranceTravailImporter

STAGE_OFFER = {
    "id": "123ABC",
    "intitule": "Stage de fin d'études / Alternance - Sujet : Data (H/F)",
    "description": "<p>Stage de fin d'études en développement Python/Django.</p>",
    "dateCreation": "2026-01-15T10:00:00.000Z",
    "lieuTravail": {"libelle": "Paris (75)", "commune": "75056"},
    "entreprise": {"nom": "TechFR"},
    "typeContrat": "CDD",
    "typeContratLibelle": "CDD - 6 Mois",
    "natureContrat": "Contrat apprentissage",
    "alternance": True,
    "salaire": {"libelle": "Selon profil"},
    "competences": [{"code": "123", "libelle": "Python"}, {"code": "124", "libelle": "Django"}],
    "origineOffre": {"origine": "1", "urlOrigine": "https://candidat.francetravail.fr/offres/123"},
}

ALTERNANCE_OFFER = {
    "id": "456DEF",
    "intitule": "Alternance Développeur Backend Java",
    "description": "<p>Alternance en développement backend.</p>",
    "dateCreation": "2026-01-16T10:00:00.000Z",
    "lieuTravail": {"libelle": "Rennes (35)"},
    "entreprise": {"nom": "ISCOD"},
    "typeContrat": "CDD",
    "typeContratLibelle": "CDD - 12 Mois",
    "natureContrat": "Contrat apprentissage",
    "alternance": True,
    "salaire": {},
    "competences": [],
    "origineOffre": {"urlOrigine": "https://candidat.francetravail.fr/offres/456"},
}

INTERIM_OFFER = {
    "id": "789GHI",
    "intitule": "Technicien / Technicienne de hot line en informatique (H/F)",
    "description": "<p>Mission intérimaire au sein d'un service support.</p>",
    "dateCreation": "2026-01-17T10:00:00.000Z",
    "lieuTravail": {"libelle": "Lyon (69)"},
    "entreprise": {"nom": "MANPOWER FRANCE"},
    "typeContrat": "MIS",
    "typeContratLibelle": "Mission intérimaire",
    "natureContrat": "",
    "alternance": False,
    "salaire": {},
    "competences": [],
    "origineOffre": {"urlOrigine": "https://candidat.francetravail.fr/offres/789"},
}


def _token_response():
    response = Mock()
    response.raise_for_status = Mock()
    response.json.return_value = {"access_token": "fake-token", "expires_in": 1200}
    return response


def _search_response(offers, status_code=200):
    response = Mock()
    response.status_code = status_code
    response.raise_for_status = Mock()
    response.json.return_value = {"resultats": offers}
    return response


def _empty_response():
    response = Mock()
    response.status_code = 204
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
    mock_get.return_value = _search_response([STAGE_OFFER])

    jobs = FranceTravailImporter().fetch(limit=10, keywords="python")

    assert len(jobs) == 1
    job = jobs[0]
    assert job["source"] == "france_travail"
    assert job["external_id"] == "123ABC"
    assert job["title"] == "Stage de fin d'études / Alternance - Sujet : Data (H/F)"
    assert job["company"] == "TechFR"
    assert job["location"] == "Paris (75)"
    assert job["url"] == "https://candidat.francetravail.fr/offres/123"
    assert job["tags"] == ["Python", "Django"]
    assert job["published_at"] is not None

    # explicit "stage" wording wins even though the API also flags it as alternance=true
    assert job["contract_type"] == "stage"


@patch("apps.jobs.importers.france_travail.requests.get")
@patch("apps.jobs.importers.france_travail.requests.post")
def test_fetch_classifies_pure_alternance_and_interim_offers(mock_post, mock_get, with_credentials):
    mock_post.return_value = _token_response()
    mock_get.return_value = _search_response([ALTERNANCE_OFFER, INTERIM_OFFER])

    jobs = FranceTravailImporter().fetch(limit=10, keywords="python")

    by_id = {job["external_id"]: job for job in jobs}
    assert by_id["456DEF"]["contract_type"] == "alternance"
    assert by_id["789GHI"]["contract_type"] == "interim"


@patch("apps.jobs.importers.france_travail.requests.get")
@patch("apps.jobs.importers.france_travail.requests.post")
def test_fetch_uses_default_nature_contrat_and_queries_one_request_per_keyword(
    mock_post, mock_get, with_credentials
):
    mock_post.return_value = _token_response()
    mock_get.return_value = _search_response([STAGE_OFFER])

    FranceTravailImporter().fetch(limit=10)

    expected_terms = len(DEFAULT_KEYWORDS.split(","))
    assert mock_get.call_count == expected_terms
    for call in mock_get.call_args_list:
        assert call.kwargs["params"]["natureContrat"] == "E2,FS"
        assert call.kwargs["params"]["motsCles"] in DEFAULT_KEYWORDS.split(",")


@patch("apps.jobs.importers.france_travail.requests.get")
@patch("apps.jobs.importers.france_travail.requests.post")
def test_fetch_deduplicates_offers_returned_by_multiple_keywords(
    mock_post, mock_get, with_credentials
):
    mock_post.return_value = _token_response()
    # every keyword query returns the same offer — must be merged into a single result
    mock_get.return_value = _search_response([STAGE_OFFER])

    jobs = FranceTravailImporter().fetch(limit=10, keywords="python,java")

    assert len(jobs) == 1


@patch("apps.jobs.importers.france_travail.requests.get")
@patch("apps.jobs.importers.france_travail.requests.post")
def test_fetch_treats_204_as_no_results_for_a_keyword(mock_post, mock_get, with_credentials):
    mock_post.return_value = _token_response()
    mock_get.side_effect = [_empty_response(), _search_response([ALTERNANCE_OFFER])]

    jobs = FranceTravailImporter().fetch(limit=10, keywords="rare-term,python")

    assert len(jobs) == 1
    assert jobs[0]["external_id"] == "456DEF"


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
        FranceTravailImporter().fetch(limit=10, keywords="python")
