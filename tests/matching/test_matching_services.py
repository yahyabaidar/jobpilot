from unittest.mock import patch

import pytest

from apps.accounts.models import User
from apps.jobs.models import JobOffer
from apps.matching.models import Match
from apps.matching.services import (
    WEIGHT_EDUCATION,
    WEIGHT_EXPERIENCE,
    WEIGHT_LANGUAGE,
    WEIGHT_LOCATION,
    WEIGHT_SKILLS,
    ProfileMissingError,
    analyze_match,
    compute_global_score,
    compute_skill_overlap,
)
from apps.profiles.models import Profile, Skill

LLM_RESPONSE = {
    "scores": {"competences": 80, "experience": 60, "formation": 100, "lieu": 100, "langue": 0},
    "competences_correspondantes": ["Python", "Django"],
    "competences_manquantes": ["PostgreSQL"],
    "conseil": "Bon profil, renforcez PostgreSQL.",
    "legitimite": {
        "niveau": "fiable",
        "raisons": ["Entreprise identifiable", "Description précise"],
    },
}


def test_compute_skill_overlap_gives_expected_score():
    profile_skills = {"python", "django", "docker"}
    offer_tags = {"python", "django", "postgresql"}

    result = compute_skill_overlap(profile_skills, offer_tags)

    assert result["matched"] == 2
    assert result["total_required"] == 3
    assert result["score"] == 67  # round(2/3 * 100)


def test_compute_skill_overlap_with_no_offer_tags():
    result = compute_skill_overlap({"python"}, set())

    assert result == {"matched": 0, "total_required": 0, "score": 0}


def test_compute_global_score_respects_weighting():
    axis_scores = {
        "skills_score": 80,
        "experience_score": 60,
        "education_score": 100,
        "location_score": 100,
        "language_score": 0,
    }

    score = compute_global_score(axis_scores)

    expected = round(
        80 * WEIGHT_SKILLS
        + 60 * WEIGHT_EXPERIENCE
        + 100 * WEIGHT_EDUCATION
        + 100 * WEIGHT_LOCATION
        + 0 * WEIGHT_LANGUAGE
    )
    assert score == expected
    total_weight = (
        WEIGHT_SKILLS + WEIGHT_EXPERIENCE + WEIGHT_EDUCATION + WEIGHT_LOCATION + WEIGHT_LANGUAGE
    )
    assert total_weight == 1.0


@pytest.fixture
def user_with_profile(db):
    user = User.objects.create_user(email="user@example.com", password="un-mot-de-passe-solide")
    profile = Profile.objects.create(user=user, title="Développeur Python")
    Skill.objects.create(profile=profile, display_name="Python", category="technical")
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
        tags=["python"],
    )


@patch("apps.matching.services.complete_json")
def test_analyze_match_creates_match_with_weighted_score(
    mock_complete_json, user_with_profile, offer
):
    mock_complete_json.return_value = LLM_RESPONSE

    match = analyze_match(user_with_profile, offer)

    assert match.skills_score == 80
    assert match.matched_skills == ["Python", "Django"]
    assert match.missing_skills == ["PostgreSQL"]
    assert match.legitimacy == Match.Legitimacy.RELIABLE
    assert match.score == compute_global_score(
        {
            "skills_score": 80,
            "experience_score": 60,
            "education_score": 100,
            "location_score": 100,
            "language_score": 0,
        }
    )


@patch("apps.matching.services.complete_json")
def test_reanalysis_updates_row_instead_of_duplicating(
    mock_complete_json, user_with_profile, offer
):
    mock_complete_json.return_value = LLM_RESPONSE
    analyze_match(user_with_profile, offer)

    updated_response = {**LLM_RESPONSE, "conseil": "Nouveau conseil."}
    mock_complete_json.return_value = updated_response
    analyze_match(user_with_profile, offer)

    assert Match.objects.filter(user=user_with_profile, job_offer=offer).count() == 1
    assert Match.objects.get(user=user_with_profile, job_offer=offer).advice == "Nouveau conseil."


@pytest.mark.django_db
def test_analyze_match_raises_when_profile_missing(offer):
    user = User.objects.create_user(
        email="noprofile@example.com", password="un-mot-de-passe-solide"
    )

    with pytest.raises(ProfileMissingError):
        analyze_match(user, offer)
