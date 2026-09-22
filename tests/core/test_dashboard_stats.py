import pytest

from apps.accounts.models import User
from apps.applications.models import Application
from apps.core.services import (
    get_dashboard_stats,
    get_missing_skills_stats,
    get_score_distribution,
)
from apps.jobs.models import JobOffer
from apps.matching.models import Match


@pytest.fixture
def user(db):
    return User.objects.create_user(email="user@example.com", password="un-mot-de-passe-solide")


def _offer(n):
    return JobOffer.objects.create(
        source="manuel", external_id=f"offer-{n}", title=f"Poste {n}", url=f"https://ex.com/{n}"
    )


def _match(user, offer, score, missing_skills):
    return Match.objects.create(
        user=user,
        job_offer=offer,
        score=score,
        skills_score=score,
        experience_score=score,
        education_score=score,
        location_score=score,
        language_score=score,
        matched_skills=[],
        missing_skills=missing_skills,
    )


@pytest.mark.django_db
def test_response_rate_computed_correctly(user):
    offers = [_offer(i) for i in range(5)]
    statuses = ["sent", "sent", "interview", "offer", "rejected"]
    for offer, status in zip(offers, statuses, strict=True):
        Application.objects.create(user=user, job_offer=offer, status=status)

    stats = get_dashboard_stats(user)

    assert stats["status_counts"] == {"sent": 2, "interview": 1, "offer": 1, "rejected": 1}
    assert stats["response_rate"] == 40  # (interview+offer)=2 / (sent+interview+offer+rejected)=5


@pytest.mark.django_db
def test_response_rate_does_not_divide_by_zero(user):
    stats = get_dashboard_stats(user)

    assert stats["response_rate"] == 0


@pytest.mark.django_db
def test_missing_skills_ranks_most_frequent_first(user):
    offers = [_offer(i) for i in range(4)]
    _match(user, offers[0], 50, ["Docker", "SQL"])
    _match(user, offers[1], 50, ["Docker"])
    _match(user, offers[2], 50, ["Docker", "AWS"])
    _match(user, offers[3], 50, ["SQL"])

    results = get_missing_skills_stats(user)

    assert results[0]["skill"] == "Docker"
    assert results[0]["count"] == 3
    assert results[1]["skill"] == "SQL"
    assert results[1]["count"] == 2


@pytest.mark.django_db
def test_score_distribution_buckets_by_ten(user):
    offers = [_offer(i) for i in range(3)]
    _match(user, offers[0], 5, [])
    _match(user, offers[1], 15, [])
    _match(user, offers[2], 95, [])

    result = get_score_distribution(user)

    assert result["counts"][0] == 1  # 0-9
    assert result["counts"][1] == 1  # 10-19
    assert result["counts"][9] == 1  # 90-100
    assert sum(result["counts"]) == 3
    assert result["labels"][-1] == "90-100"


@pytest.mark.django_db
def test_offer_count_and_analyzed_count(user):
    offers = [_offer(i) for i in range(3)]
    _match(user, offers[0], 50, [])

    stats = get_dashboard_stats(user)

    assert stats["offer_count"] == 3
    assert stats["analyzed_count"] == 1
    assert stats["has_profile"] is False
