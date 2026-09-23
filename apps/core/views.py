from django.contrib.auth.decorators import login_required
from django.db import connection
from django.db.utils import Error as DatabaseError
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render

from apps.applications.models import Application

from .services import (
    get_applications_over_time,
    get_dashboard_stats,
    get_highlighted_internships,
    get_market_skills_stats,
    get_missing_skills_stats,
    get_score_distribution,
)


def home(request: HttpRequest) -> HttpResponse:
    return render(request, "core/home.html")


def health(request: HttpRequest) -> JsonResponse:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except DatabaseError:
        return JsonResponse({"status": "error", "database": "unreachable"}, status=503)
    return JsonResponse({"status": "ok"})


@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    stats = get_dashboard_stats(request.user)
    missing_skills = get_missing_skills_stats(request.user)
    market_skills = get_market_skills_stats()
    score_distribution = get_score_distribution(request.user)
    applications_over_time = get_applications_over_time(request.user)
    highlighted_internships = get_highlighted_internships(request.user)

    status_breakdown = [
        {"label": label, "value": stats["status_counts"].get(value, 0)}
        for value, label in Application.Status.choices
    ]

    stat_cards = [
        {"label": "CV analysé", "value": "Oui" if stats["has_profile"] else "Non"},
        {"label": "Offres en base", "value": stats["offer_count"]},
        {"label": "Offres analysées", "value": stats["analyzed_count"]},
        {"label": "Taux de réponse", "value": f"{stats['response_rate']}%"},
    ]

    return render(
        request,
        "core/dashboard.html",
        {
            "active_nav": "dashboard",
            "has_profile": stats["has_profile"],
            "stat_cards": stat_cards,
            "status_breakdown": status_breakdown,
            "missing_skills": missing_skills,
            "market_skills": market_skills,
            "score_distribution": score_distribution,
            "has_score_data": any(score_distribution["counts"]),
            "applications_over_time": applications_over_time,
            "highlighted_internships": highlighted_internships,
        },
    )
