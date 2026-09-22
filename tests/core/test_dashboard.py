import pytest
from django.urls import reverse

from apps.accounts.models import User


def test_dashboard_redirects_when_anonymous(client):
    response = client.get(reverse("core:dashboard"))

    assert response.status_code == 302
    assert reverse("accounts:login") in response.url


@pytest.mark.django_db
def test_dashboard_accessible_when_authenticated(client):
    User.objects.create_user(email="user@example.com", password="un-mot-de-passe-solide")
    client.login(email="user@example.com", password="un-mot-de-passe-solide")

    response = client.get(reverse("core:dashboard"))

    assert response.status_code == 200
