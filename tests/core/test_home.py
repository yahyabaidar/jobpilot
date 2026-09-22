from django.urls import reverse


def test_home_page_returns_200(client):
    response = client.get(reverse("core:home"))

    assert response.status_code == 200
