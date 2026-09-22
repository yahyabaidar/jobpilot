from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from apps.core.llm import LLMError

from .forms import CVUploadForm
from .models import CVDocument, Profile, Skill, normalize_skill_name
from .services import CVParsingError, analyze_cv


def _profile_for(request: HttpRequest) -> Profile | None:
    return (
        Profile.objects.filter(user=request.user)
        .prefetch_related("skills", "experiences", "educations")
        .first()
    )


@login_required
def index(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "profiles/index.html",
        {
            "active_nav": "profile",
            "profile": _profile_for(request),
            "cv_document": CVDocument.objects.filter(user=request.user).first(),
            "upload_form": CVUploadForm(),
        },
    )


@login_required
@require_POST
def upload_cv(request: HttpRequest) -> HttpResponse:
    form = CVUploadForm(request.POST, request.FILES)
    if not form.is_valid():
        return render(
            request,
            "profiles/partials/_profile_panel.html",
            {
                "profile": _profile_for(request),
                "cv_document": CVDocument.objects.filter(user=request.user).first(),
                "upload_form": form,
            },
        )

    cv_document = form.save(commit=False)
    cv_document.user = request.user
    cv_document.original_name = form.cleaned_data["file"].name
    cv_document.save()
    return render(request, "profiles/partials/_processing.html", {"cv_document": cv_document})


@login_required
@require_POST
def reanalyze(request: HttpRequest, pk: int) -> HttpResponse:
    cv_document = get_object_or_404(CVDocument, pk=pk, user=request.user)
    return render(request, "profiles/partials/_processing.html", {"cv_document": cv_document})


@login_required
@require_POST
def analyze(request: HttpRequest, pk: int) -> HttpResponse:
    cv_document = get_object_or_404(CVDocument, pk=pk, user=request.user)

    try:
        analyze_cv(cv_document)
    except (CVParsingError, LLMError) as exc:
        return render(
            request,
            "profiles/partials/_profile_panel.html",
            {
                "profile": _profile_for(request),
                "cv_document": cv_document,
                "upload_form": CVUploadForm(),
                "toast_tag": "error",
                "toast_text": f"Échec de l'analyse du CV : {exc}",
            },
        )

    return render(
        request,
        "profiles/partials/_profile_panel.html",
        {
            "profile": _profile_for(request),
            "cv_document": cv_document,
            "upload_form": CVUploadForm(),
            "toast_tag": "success",
            "toast_text": "Votre CV a été analysé avec succès.",
        },
    )


@login_required
@require_POST
def update_profile(request: HttpRequest) -> HttpResponse:
    profile = get_object_or_404(Profile, user=request.user)
    profile.title = request.POST.get("title", "").strip()
    profile.summary = request.POST.get("summary", "").strip()
    profile.save(update_fields=["title", "summary"])
    return render(
        request,
        "profiles/partials/_profile_panel.html",
        {
            "profile": _profile_for(request),
            "cv_document": CVDocument.objects.filter(user=request.user).first(),
            "upload_form": CVUploadForm(),
        },
    )


@login_required
@require_POST
def add_skill(request: HttpRequest) -> HttpResponse:
    profile = get_object_or_404(Profile, user=request.user)
    display_name = request.POST.get("display_name", "").strip()
    category = request.POST.get("category", Skill.Category.TECHNICAL)

    if display_name:
        normalized = normalize_skill_name(display_name)
        if not profile.skills.filter(normalized_name=normalized).exists():
            Skill.objects.create(
                profile=profile,
                display_name=display_name,
                normalized_name=normalized,
                category=category,
            )

    return render(request, "profiles/partials/_skills.html", {"profile": profile})


@login_required
@require_POST
def delete_skill(request: HttpRequest, pk: int) -> HttpResponse:
    skill = get_object_or_404(Skill, pk=pk, profile__user=request.user)
    profile = skill.profile
    skill.delete()
    return render(request, "profiles/partials/_skills.html", {"profile": profile})
