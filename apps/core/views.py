from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from apps.applications.models import Application
from apps.jobs.models import JobOffer
from apps.profiles.models import CVDocument, Skill


def home(request: HttpRequest) -> HttpResponse:
    return render(request, "core/home.html")


@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    cv_count = CVDocument.objects.filter(user=request.user).count()
    skill_count = Skill.objects.filter(profile__user=request.user).count()
    offer_count = JobOffer.objects.count()
    application_count = Application.objects.filter(user=request.user).count()
    stats = [
        {"label": "CV importés", "value": cv_count},
        {"label": "Compétences détectées", "value": skill_count},
        {"label": "Offres importées", "value": offer_count},
        {"label": "Candidatures suivies", "value": application_count},
    ]
    return render(
        request,
        "core/dashboard.html",
        {"active_nav": "dashboard", "stats": stats},
    )
