from unittest.mock import patch

import pytest
from django.urls import reverse

from apps.accounts.models import User
from apps.applications.models import Application
from apps.jobs.models import JobOffer
from apps.profiles.models import SearchPreference


@pytest.fixture
def user(db):
    return User.objects.create_user(email="user@example.com", password="un-mot-de-passe-solide")


def _login(client, user):
    client.login(email=user.email, password="un-mot-de-passe-solide")


def test_jobs_index_requires_login(client):
    response = client.get(reverse("jobs:index"))

    assert response.status_code == 302


@pytest.mark.django_db
def test_search_and_filters_return_expected_results(client, user):
    _login(client, user)
    JobOffer.objects.create(
        source="remotive",
        external_id="1",
        title="Python Developer",
        company="Acme",
        location="Paris",
        remote=True,
        url="https://a.example/1",
        contract_type="stage",
    )
    JobOffer.objects.create(
        source="arbeitnow",
        external_id="2",
        title="Java Developer",
        company="Beta",
        location="Berlin",
        remote=False,
        url="https://b.example/2",
        contract_type="stage",
    )

    response = client.get(reverse("jobs:index"), {"q": "Python"})
    assert b"Python Developer" in response.content
    assert b"Java Developer" not in response.content

    response = client.get(reverse("jobs:index"), {"source": "arbeitnow"})
    assert b"Java Developer" in response.content
    assert b"Python Developer" not in response.content

    response = client.get(reverse("jobs:index"), {"remote": "1"})
    assert b"Python Developer" in response.content
    assert b"Java Developer" not in response.content


@pytest.mark.django_db
def test_check_url_flags_disallowed_domain(client, user):
    _login(client, user)

    response = client.post(
        reverse("jobs:check_url"), {"url": "https://www.linkedin.com/jobs/view/1"}
    )
    assert b"n'autorise pas l'import automatique" in response.content

    response2 = client.post(reverse("jobs:check_url"), {"url": "https://example.com/jobs/1"})
    assert b"n'autorise pas" not in response2.content


@pytest.mark.django_db
@patch("apps.jobs.views.extract_job_offer")
def test_manual_flow_creates_offer_with_expected_fields(mock_extract, client, user):
    _login(client, user)
    mock_extract.return_value = {
        "title": "Ingénieur Data",
        "company": "DataCo",
        "location": "Lyon",
        "remote": True,
        "tags": ["Python", "SQL"],
        "language": "fr",
        "salary": "40-50k",
        "summary": "Résumé.",
    }

    analyze_response = client.post(
        reverse("jobs:manual_analyze"), {"pasted_text": "texte offre", "url": ""}
    )
    assert analyze_response.status_code == 200

    save_response = client.post(
        reverse("jobs:manual_save"),
        {
            "title": "Ingénieur Data",
            "company": "DataCo",
            "location": "Lyon",
            "remote": "1",
            "salary": "40-50k",
            "language": "fr",
            "tags": "Python, SQL",
            "description": "texte offre",
            "url": "",
        },
    )
    assert save_response.status_code == 302

    offer = JobOffer.objects.get(source="manuel")
    assert offer.title == "Ingénieur Data"
    assert offer.company == "DataCo"
    assert offer.remote is True
    assert offer.tags == ["Python", "SQL"]
    assert offer.added_by == user


@pytest.mark.django_db
def test_apply_creates_application_and_is_idempotent(client, user):
    _login(client, user)
    offer = JobOffer.objects.create(
        source="remotive",
        external_id="1",
        title="Python Developer",
        company="Acme",
        url="https://a.example/1",
    )

    response = client.post(reverse("jobs:apply", args=[offer.pk]))
    assert response.status_code == 200
    assert Application.objects.filter(user=user, job_offer=offer).count() == 1

    response2 = client.post(reverse("jobs:apply", args=[offer.pk]))
    assert response2.status_code == 200
    assert Application.objects.filter(user=user, job_offer=offer).count() == 1

    application = Application.objects.get(user=user, job_offer=offer)
    assert application.status == Application.Status.SENT


@pytest.mark.django_db
def test_detail_page_shows_apply_link_to_offer_url(client, user):
    _login(client, user)
    offer = JobOffer.objects.create(
        source="remotive",
        external_id="1",
        title="Python Developer",
        company="Acme",
        url="https://a.example/1",
    )

    response = client.get(reverse("jobs:detail", args=[offer.pk]))

    assert response.status_code == 200
    assert b"https://a.example/1" in response.content


@pytest.mark.django_db
def test_default_filter_shows_only_stage_without_preference(client, user):
    _login(client, user)
    JobOffer.objects.create(
        source="manuel",
        external_id="s1",
        title="Stage Python",
        url="https://a.example/s1",
        contract_type="stage",
    )
    JobOffer.objects.create(
        source="manuel",
        external_id="c1",
        title="CDI Python",
        url="https://a.example/c1",
        contract_type="cdi",
    )

    response = client.get(reverse("jobs:index"))

    assert b"Stage Python" in response.content
    assert b"CDI Python" not in response.content


@pytest.mark.django_db
def test_default_filter_follows_search_preference(client, user):
    _login(client, user)
    SearchPreference.objects.create(user=user, contract_types=["cdi"])
    JobOffer.objects.create(
        source="manuel",
        external_id="s1",
        title="Stage Python",
        url="https://a.example/s1",
        contract_type="stage",
    )
    JobOffer.objects.create(
        source="manuel",
        external_id="c1",
        title="CDI Python",
        url="https://a.example/c1",
        contract_type="cdi",
    )

    response = client.get(reverse("jobs:index"))

    assert b"CDI Python" in response.content
    assert b"Stage Python" not in response.content


@pytest.mark.django_db
def test_elargir_bypasses_default_contract_type_filter(client, user):
    _login(client, user)
    JobOffer.objects.create(
        source="manuel",
        external_id="s1",
        title="Stage Python",
        url="https://a.example/s1",
        contract_type="stage",
    )
    JobOffer.objects.create(
        source="manuel",
        external_id="c1",
        title="CDI Python",
        url="https://a.example/c1",
        contract_type="cdi",
    )

    response = client.get(reverse("jobs:index"), {"elargir": "1"})

    assert b"Stage Python" in response.content
    assert b"CDI Python" in response.content
