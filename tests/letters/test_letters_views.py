import pytest
from django.urls import reverse

from apps.accounts.models import User
from apps.jobs.models import JobOffer
from apps.letters.models import CoverLetter, InterviewPrep, TailoredCV


@pytest.fixture
def owner(db):
    return User.objects.create_user(email="owner@example.com", password="un-mot-de-passe-solide")


@pytest.fixture
def other(db):
    return User.objects.create_user(email="other@example.com", password="un-mot-de-passe-solide")


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


def _login(client, user):
    client.login(email=user.email, password="un-mot-de-passe-solide")


@pytest.mark.django_db
def test_letter_pdf_export_returns_non_empty_pdf(client, owner, offer):
    letter = CoverLetter.objects.create(
        user=owner, job_offer=offer, language="fr", content="Madame, Monsieur, ..."
    )
    _login(client, owner)

    response = client.get(reverse("letters:letter_pdf", args=[letter.pk]))

    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
    assert len(response.content) > 0


@pytest.mark.django_db
def test_cv_pdf_export_returns_non_empty_pdf(client, owner, offer):
    tailored_cv = TailoredCV.objects.create(
        user=owner,
        job_offer=offer,
        content={"titre": "Dev", "resume": "R", "competences": ["Python"], "experiences": []},
    )
    _login(client, owner)

    response = client.get(reverse("letters:cv_pdf", args=[tailored_cv.pk]))

    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
    assert len(response.content) > 0


@pytest.mark.django_db
def test_user_cannot_access_another_users_letter_pdf(client, owner, other, offer):
    letter = CoverLetter.objects.create(
        user=owner, job_offer=offer, language="fr", content="Contenu."
    )
    _login(client, other)

    response = client.get(reverse("letters:letter_pdf", args=[letter.pk]))

    assert response.status_code == 404


@pytest.mark.django_db
def test_user_cannot_access_another_users_cv_pdf(client, owner, other, offer):
    tailored_cv = TailoredCV.objects.create(
        user=owner, job_offer=offer, content={"titre": "Dev", "competences": [], "experiences": []}
    )
    _login(client, other)

    response = client.get(reverse("letters:cv_pdf", args=[tailored_cv.pk]))

    assert response.status_code == 404


@pytest.mark.django_db
def test_user_cannot_save_another_users_letter(client, owner, other, offer):
    letter = CoverLetter.objects.create(
        user=owner, job_offer=offer, language="fr", content="Original."
    )
    _login(client, other)

    response = client.post(reverse("letters:save_letter", args=[letter.pk]), {"content": "Piraté."})

    assert response.status_code == 404
    letter.refresh_from_db()
    assert letter.content == "Original."


@pytest.mark.django_db
def test_user_cannot_save_another_users_interview_prep(client, owner, other, offer):
    interview = InterviewPrep.objects.create(user=owner, job_offer=offer, questions=[])
    _login(client, other)

    response = client.post(reverse("letters:save_interview", args=[interview.pk]))

    assert response.status_code == 404
