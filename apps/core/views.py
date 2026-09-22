from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from apps.profiles.models import CVDocument, Skill


def home(request: HttpRequest) -> HttpResponse:
    return render(request, "core/home.html")


@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    cv_count = CVDocument.objects.filter(user=request.user).count()
    skill_count = Skill.objects.filter(profile__user=request.user).count()
    stats = [
        {"label": "CV importés", "value": cv_count},
        {"label": "Compétences détectées", "value": skill_count},
        {"label": "Offres importées", "value": 0},
        {"label": "Candidatures suivies", "value": 0},
    ]
    return render(
        request,
        "core/dashboard.html",
        {"active_nav": "dashboard", "stats": stats},
    )
