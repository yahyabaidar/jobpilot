from unittest.mock import patch

import pytest

from apps.accounts.models import User
from apps.jobs.models import JobOffer
from apps.matching.services import analyze_match
from apps.profiles.models import Profile, Skill

STAGE_LLM_RESPONSE = {
    "scores": {"competences": 90, "experience": 85, "formation": 90, "lieu": 100, "langue": 100},
    "competences_correspondantes": ["Python"],
    "competences_manquantes": [],
    "conseil": "Bon profil pour ce stage.",
    "legitimite": {"niveau": "fiable", "raisons": []},
    "admissibilite": ["Convention de stage obligatoire"],
}

CDI_LLM_RESPONSE = {
    "scores": {"competences": 60, "experience": 5, "formation": 60, "lieu": 100, "langue": 100},
    "competences_correspondantes": ["Python"],
    "competences_manquantes": [],
    "conseil": "Ce poste vise un profil confirmé.",
    "legitimite": {"niveau": "fiable", "raisons": []},
    "admissibilite": [],
}


@pytest.fixture
def student(db):
    user = User.objects.create_user(email="student@example.com", password="un-mot-de-passe-solide")
    profile = Profile.objects.create(user=user, title="Étudiant ingénieur", years_of_experience=0)
    Skill.objects.create(profile=profile, display_name="Python", category="technical")
    return user


@patch("apps.matching.services.complete_json")
def test_internship_offer_is_not_penalized_on_experience_axis(mock_complete_json, student):
    mock_complete_json.return_value = STAGE_LLM_RESPONSE
    offer = JobOffer.objects.create(
        source="manuel",
        external_id="stage-1",
        title="Stage Python",
        url="https://ex.com/1",
        contract_type=JobOffer.ContractType.STAGE,
    )

    match = analyze_match(student, offer)

    assert match.experience_score == 85
    assert match.administrative_notes == ["Convention de stage obligatoire"]


@patch("apps.matching.services.complete_json")
def test_senior_cdi_offer_reflects_experience_gap(mock_complete_json, student):
    mock_complete_json.return_value = CDI_LLM_RESPONSE
    offer = JobOffer.objects.create(
        source="manuel",
        external_id="cdi-1",
        title="Lead Dev Python",
        url="https://ex.com/2",
        contract_type=JobOffer.ContractType.CDI,
    )

    match = analyze_match(student, offer)

    assert match.experience_score == 5
    assert "profil confirmé" in match.advice
