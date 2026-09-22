import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.accounts.models import User
from apps.profiles.models import CVDocument


@pytest.fixture
def user(db):
    return User.objects.create_user(email="user@example.com", password="un-mot-de-passe-solide")


def _login(client, user):
    client.login(email=user.email, password="un-mot-de-passe-solide")


@pytest.mark.django_db
def test_non_pdf_upload_is_rejected(client, user):
    _login(client, user)
    upload = SimpleUploadedFile("cv.txt", b"pas un pdf", content_type="text/plain")

    response = client.post("/profil/cv/envoyer/", {"file": upload})

    assert response.status_code == 200
    assert b"doit \xc3\xaatre un PDF" in response.content
    assert not CVDocument.objects.filter(user=user).exists()


@pytest.mark.django_db
def test_oversized_pdf_upload_is_rejected(client, user):
    _login(client, user)
    oversized_content = b"%PDF-1.4\n" + b"0" * (5 * 1024 * 1024 + 1)
    upload = SimpleUploadedFile("cv.pdf", oversized_content, content_type="application/pdf")

    response = client.post("/profil/cv/envoyer/", {"file": upload})

    assert response.status_code == 200
    assert b"5 Mo" in response.content
    assert not CVDocument.objects.filter(user=user).exists()


def test_profile_page_requires_login(client):
    response = client.get("/profil/")

    assert response.status_code == 302
