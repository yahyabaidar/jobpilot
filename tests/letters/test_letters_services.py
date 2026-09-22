from unittest.mock import patch

import pytest

from apps.accounts.models import User
from apps.jobs.models import JobOffer
from apps.letters.models import CoverLetter, TailoredCV
from apps.letters.services import (
    ProfileMissingError,
    generate_cover_letter,
    generate_interview_prep,
    generate_tailored_cv,
)
from apps.profiles.models import Experience, Profile, Skill

LETTER_LLM_RESPONSE = {"lettre": "Madame, Monsieur, " + "mot " * 250}

TAILORED_CV_LLM_RESPONSE_WITH_FABRICATION = {
    "titre": "Développeur Python",
    "resume": "Résumé.",
    "competences": ["Python", "Kubernetes"],  # Kubernetes is NOT in the profile
    "experiences": [
        {"poste": "Développeur backend", "entreprise": "Acme", "description": "API Django."},
        {"poste": "CEO", "entreprise": "FakeCorp", "description": "Direction générale."},
    ],
}

INTERVIEW_LLM_RESPONSE = {
    "questions": [
        {
            "question": f"Question {i}",
            "situation": "Situation",
            "tache": "Tâche",
            "action": "Action",
            "resultat": "Résultat",
        }
        for i in range(5)
    ]
}


@pytest.fixture
def user_with_profile(db):
    user = User.objects.create_user(email="user@example.com", password="un-mot-de-passe-solide")
    profile = Profile.objects.create(user=user, title="Développeur Python")
    Skill.objects.create(profile=profile, display_name="Python", category="technical")
    Experience.objects.create(profile=profile, title="Développeur backend", company="Acme")
    return user


@pytest.fixture
def offer(db):
    return JobOffer.objects.create(
        source="manuel",
        external_id="1",
        title="Développeur Python",
        company="Acme",
        url="https://example.com/1",
        description="desc",
    )


@patch("apps.letters.services.complete_json")
def test_generate_cover_letter_fr_and_en_creates_history(
    mock_complete_json, user_with_profile, offer
):
    mock_complete_json.return_value = LETTER_LLM_RESPONSE

    letter_fr = generate_cover_letter(user_with_profile, offer, language="fr")
    letter_en = generate_cover_letter(user_with_profile, offer, language="en")

    assert letter_fr.language == "fr"
    assert letter_en.language == "en"
    assert CoverLetter.objects.filter(user=user_with_profile, job_offer=offer).count() == 2

    most_recent = CoverLetter.objects.filter(user=user_with_profile, job_offer=offer).first()
    assert most_recent.pk == letter_en.pk


@patch("apps.letters.services.complete_json")
def test_generate_cover_letter_raises_when_profile_missing(mock_complete_json, offer):
    mock_complete_json.return_value = LETTER_LLM_RESPONSE
    user = User.objects.create_user(
        email="noprofile@example.com", password="un-mot-de-passe-solide"
    )

    with pytest.raises(ProfileMissingError):
        generate_cover_letter(user, offer)


@patch("apps.letters.services.complete_json")
def test_tailored_cv_filters_fabricated_skills_and_experience(
    mock_complete_json, user_with_profile, offer
):
    mock_complete_json.return_value = TAILORED_CV_LLM_RESPONSE_WITH_FABRICATION

    tailored_cv = generate_tailored_cv(user_with_profile, offer)

    assert tailored_cv.content["competences"] == ["Python"]
    assert "Kubernetes" not in tailored_cv.content["competences"]
    experience_titles = [e["poste"] for e in tailored_cv.content["experiences"]]
    assert experience_titles == ["Développeur backend"]
    assert "CEO" not in experience_titles
    assert TailoredCV.objects.count() == 1


@patch("apps.letters.services.complete_json")
def test_generate_interview_prep_returns_five_questions(
    mock_complete_json, user_with_profile, offer
):
    mock_complete_json.return_value = INTERVIEW_LLM_RESPONSE

    interview = generate_interview_prep(user_with_profile, offer)

    assert len(interview.questions) == 5
    assert all(q["situation"] for q in interview.questions)
