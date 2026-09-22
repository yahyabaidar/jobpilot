from unittest.mock import patch

import pytest
from django.urls import reverse

from apps.accounts.models import User
from apps.jobs.models import JobOffer
from apps.matching.models import Match
from apps.profiles.models import Profile, Skill

LLM_RESPONSE = {
    "scores": {"competences": 80, "experience": 60, "formation": 100, "lieu": 100, "langue": 0},
    "competences_correspondantes": ["Python"],
    "competences_manquantes": ["SQL"],
    "conseil": "Conseil.",
    "legitimite": {"niveau": "fiable", "raisons": ["Description claire"]},
}


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


def _login(client, user):
    client.login(email=user.email, password="un-mot-de-passe-solide")


@pytest.mark.django_db
@patch("apps.matching.services.complete_json")
def test_user_never_sees_another_users_match(mock_complete_json, client, offer):
    mock_complete_json.return_value = LLM_RESPONSE

    owner = User.objects.create_user(email="owner@example.com", password="un-mot-de-passe-solide")
    profile = Profile.objects.create(user=owner)
    Skill.objects.create(profile=profile, display_name="Python", category="technical")
    _login(client, owner)
    client.post(reverse("matching:run_analyze", args=[offer.pk]))
    assert Match.objects.filter(user=owner, job_offer=offer).exists()

    other = User.objects.create_user(email="other@example.com", password="un-mot-de-passe-solide")
    other_client = client.__class__()
    _login(other_client, other)

    response = other_client.get(reverse("jobs:detail", args=[offer.pk]))

    assert response.status_code == 200
    assert b"Envoie d'abord ton CV" in response.content
    assert str(LLM_RESPONSE["conseil"]).encode() not in response.content


@pytest.mark.django_db
def test_run_analyze_without_profile_shows_invite_not_error(client, offer):
    user = User.objects.create_user(
        email="noprofile@example.com", password="un-mot-de-passe-solide"
    )
    _login(client, user)

    response = client.post(reverse("matching:run_analyze", args=[offer.pk]))

    assert response.status_code == 200
    assert b"Envoie d'abord ton CV" in response.content
    assert not Match.objects.filter(user=user, job_offer=offer).exists()


@pytest.mark.django_db
@patch("apps.matching.services.complete_json")
def test_reanalyze_via_view_updates_not_duplicates(mock_complete_json, client, offer):
    mock_complete_json.return_value = LLM_RESPONSE
    user = User.objects.create_user(email="user@example.com", password="un-mot-de-passe-solide")
    profile = Profile.objects.create(user=user)
    Skill.objects.create(profile=profile, display_name="Python", category="technical")
    _login(client, user)

    client.post(reverse("matching:run_analyze", args=[offer.pk]))
    client.post(reverse("matching:run_analyze", args=[offer.pk]))

    assert Match.objects.filter(user=user, job_offer=offer).count() == 1
