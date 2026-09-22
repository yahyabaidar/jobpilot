import json
from collections import defaultdict

from django.contrib.auth.decorators import login_required
from django.db.models import IntegerField, OuterRef, Subquery
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.matching.models import Match

from .models import Application
from .services import move_application

STALE_AFTER_DAYS = 14


def _annotated_applications(user):
    match_score_subquery = Match.objects.filter(user=user, job_offer=OuterRef("job_offer")).values(
        "score"
    )[:1]
    return (
        Application.objects.filter(user=user)
        .select_related("job_offer")
        .annotate(my_score=Subquery(match_score_subquery, output_field=IntegerField()))
        .order_by("position", "-applied_at")
    )


def _attach_dot_color(applications: list[Application]) -> None:
    now = timezone.now()
    for application in applications:
        days = (now - application.status_changed_at).days
        if application.status == Application.Status.SENT and days > STALE_AFTER_DAYS:
            application.dot_color = "amber"
        elif days > STALE_AFTER_DAYS:
            application.dot_color = "slate"
        elif days > 7:
            application.dot_color = "slate"
        else:
            application.dot_color = "emerald"


def _build_columns(user) -> list[dict]:
    applications = list(_annotated_applications(user))
    _attach_dot_color(applications)

    by_status = defaultdict(list)
    for application in applications:
        by_status[application.status].append(application)

    return [
        {"value": value, "label": label, "applications": by_status.get(value, [])}
        for value, label in Application.Status.choices
    ]


@login_required
def index(request: HttpRequest) -> HttpResponse:
    columns = _build_columns(request.user)
    has_any_application = any(column["applications"] for column in columns)
    return render(
        request,
        "applications/index.html",
        {
            "active_nav": "applications",
            "columns": columns,
            "has_any_application": has_any_application,
        },
    )


@login_required
@require_POST
def move(request: HttpRequest) -> HttpResponse:
    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({"ok": False, "error": "Requête invalide."}, status=400)

    application_id = payload.get("application_id")
    new_status = payload.get("status")
    ordered_ids_raw = payload.get("ordered_ids") or []

    if new_status not in Application.Status.values:
        return JsonResponse({"ok": False, "error": "Statut invalide."}, status=400)

    try:
        ordered_ids = [int(x) for x in ordered_ids_raw]
    except (TypeError, ValueError):
        return JsonResponse({"ok": False, "error": "Requête invalide."}, status=400)

    application = get_object_or_404(Application, pk=application_id, user=request.user)
    move_application(application, new_status, ordered_ids)

    return JsonResponse({"ok": True})


@login_required
def detail(request: HttpRequest, pk: int) -> HttpResponse:
    application = get_object_or_404(
        Application.objects.select_related("job_offer"), pk=pk, user=request.user
    )
    match = Match.objects.filter(user=request.user, job_offer=application.job_offer).first()
    return render(
        request,
        "applications/partials/_detail_panel.html",
        {"application": application, "match": match},
    )


@login_required
@require_POST
def save_notes(request: HttpRequest, pk: int) -> HttpResponse:
    application = get_object_or_404(
        Application.objects.select_related("job_offer"), pk=pk, user=request.user
    )
    application.notes = request.POST.get("notes", "").strip()
    application.save(update_fields=["notes"])
    match = Match.objects.filter(user=request.user, job_offer=application.job_offer).first()
    return render(
        request,
        "applications/partials/_detail_panel.html",
        {
            "application": application,
            "match": match,
            "toast_tag": "success",
            "toast_text": "Notes enregistrées.",
        },
    )


@login_required
@require_POST
def delete(request: HttpRequest, pk: int) -> HttpResponse:
    application = get_object_or_404(Application, pk=pk, user=request.user)
    application.delete()

    columns = _build_columns(request.user)
    has_any_application = any(column["applications"] for column in columns)
    return render(
        request,
        "applications/partials/_board.html",
        {
            "columns": columns,
            "has_any_application": has_any_application,
            "close_panel": True,
            "toast_tag": "success",
            "toast_text": "Candidature retirée du suivi.",
        },
    )
