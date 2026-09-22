import pytest
from django.urls import reverse

from apps.accounts.models import User


@pytest.mark.django_db
def test_signup_creates_user_and_logs_in(client):
    response = client.post(
        reverse("accounts:signup"),
        {
            "email": "nouveau@example.com",
            "first_name": "Alex",
            "password1": "un-mot-de-passe-solide",
            "password2": "un-mot-de-passe-solide",
        },
    )

    assert response.status_code == 302
    assert response.url == reverse("core:dashboard")
    assert User.objects.filter(email="nouveau@example.com").exists()

    dashboard_response = client.get(reverse("core:dashboard"))
    assert dashboard_response.status_code == 200


@pytest.mark.django_db
def test_login_with_email_and_password(client):
    User.objects.create_user(email="user@example.com", password="un-mot-de-passe-solide")

    response = client.post(
        reverse("accounts:login"),
        {"username": "user@example.com", "password": "un-mot-de-passe-solide"},
    )

    assert response.status_code == 302
    assert response.url == reverse("core:dashboard")


@pytest.mark.django_db
def test_logout(client):
    User.objects.create_user(email="user@example.com", password="un-mot-de-passe-solide")
    client.login(email="user@example.com", password="un-mot-de-passe-solide")

    response = client.post(reverse("accounts:logout"))

    assert response.status_code == 302
    dashboard_response = client.get(reverse("core:dashboard"))
    assert dashboard_response.status_code == 302
