import json

import pytest
from django.urls import reverse

from apps.accounts.models import User
from apps.applications.models import Application, StatusChange
from apps.jobs.models import JobOffer


@pytest.fixture
def user(db):
    return User.objects.create_user(email="user@example.com", password="un-mot-de-passe-solide")


@pytest.fixture
def other(db):
    return User.objects.create_user(email="other@example.com", password="un-mot-de-passe-solide")


def _login(client, user):
    client.login(email=user.email, password="un-mot-de-passe-solide")


def _offer(n=1):
    return JobOffer.objects.create(
        source="manuel", external_id=f"offer-{n}", title=f"Poste {n}", url=f"https://ex.com/{n}"
    )


@pytest.mark.django_db
def test_drag_and_drop_updates_status_position_and_history(client, user):
    _login(client, user)
    offer1, offer2 = _offer(1), _offer(2)
    app1 = Application.objects.create(user=user, job_offer=offer1, status="sent", position=0)
    app2 = Application.objects.create(user=user, job_offer=offer2, status="sent", position=1)

    response = client.post(
        reverse("applications:move"),
        data=json.dumps(
            {"application_id": app1.pk, "status": "interview", "ordered_ids": [app1.pk]}
        ),
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}

    app1.refresh_from_db()
    assert app1.status == "interview"
    assert app1.position == 0
    assert StatusChange.objects.filter(application=app1, status="interview").exists()

    # reordering within the same column
    response2 = client.post(
        reverse("applications:move"),
        data=json.dumps({"application_id": app2.pk, "status": "sent", "ordered_ids": [app2.pk]}),
        content_type="application/json",
    )
    assert response2.status_code == 200
    app2.refresh_from_db()
    assert app2.position == 0


@pytest.mark.django_db
def test_move_requires_login(client):
    response = client.post(
        reverse("applications:move"),
        data=json.dumps({"application_id": 1, "status": "sent", "ordered_ids": []}),
        content_type="application/json",
    )
    assert response.status_code == 302


@pytest.mark.django_db
def test_user_only_sees_own_applications(client, user, other):
    offer = _offer()
    app = Application.objects.create(user=other, job_offer=offer, status="sent")

    _login(client, user)
    response = client.get(reverse("applications:detail", args=[app.pk]))
    assert response.status_code == 404

    response2 = client.post(
        reverse("applications:move"),
        data=json.dumps({"application_id": app.pk, "status": "interview", "ordered_ids": []}),
        content_type="application/json",
    )
    assert response2.status_code == 404

    app.refresh_from_db()
    assert app.status == "sent"


@pytest.mark.django_db
def test_board_only_shows_own_applications(client, user, other):
    my_offer = _offer(1)
    their_offer = _offer(2)
    Application.objects.create(user=user, job_offer=my_offer, status="sent")
    Application.objects.create(user=other, job_offer=their_offer, status="sent")

    _login(client, user)
    response = client.get(reverse("applications:index"))

    assert response.status_code == 200
    assert my_offer.title.encode() in response.content
    assert their_offer.title.encode() not in response.content


@pytest.mark.django_db
def test_save_notes_and_delete(client, user):
    _login(client, user)
    offer = _offer()
    app = Application.objects.create(user=user, job_offer=offer, status="sent")

    response = client.post(
        reverse("applications:save_notes", args=[app.pk]), {"notes": "À relancer."}
    )
    assert response.status_code == 200
    app.refresh_from_db()
    assert app.notes == "À relancer."

    response2 = client.post(reverse("applications:delete", args=[app.pk]))
    assert response2.status_code == 200
    assert not Application.objects.filter(pk=app.pk).exists()
