from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from apps.core.llm import LLMError
from apps.jobs.models import JobOffer

from .models import CoverLetter, InterviewPrep, TailoredCV
from .pdf import (
    letter_pdf_filename,
    render_letter_pdf,
    render_tailored_cv_pdf,
    tailored_cv_pdf_filename,
)
from .services import (
    ProfileMissingError,
    generate_cover_letter,
    generate_interview_prep,
    generate_tailored_cv,
)


@login_required
def index(request: HttpRequest) -> HttpResponse:
    return render(request, "letters/index.html", {"active_nav": "letters"})


# --- Lettre de motivation -----------------------------------------------


@login_required
@require_POST
def start_letter(request: HttpRequest, pk: int) -> HttpResponse:
    offer = get_object_or_404(JobOffer, pk=pk)
    language = request.POST.get("language", "fr")
    return render(
        request, "letters/partials/_letter_generating.html", {"offer": offer, "language": language}
    )


@login_required
@require_POST
def run_letter(request: HttpRequest, pk: int) -> HttpResponse:
    offer = get_object_or_404(JobOffer, pk=pk)
    language = request.POST.get("language", "fr")

    try:
        letter = generate_cover_letter(request.user, offer, language=language)
    except ProfileMissingError:
        return render(request, "letters/partials/_profile_missing.html", {})
    except LLMError as exc:
        return render(
            request,
            "letters/partials/_generation_error.html",
            {"offer": offer, "error": str(exc), "kind": "letter"},
        )

    return render(
        request,
        "letters/partials/_letter_tab.html",
        {
            "offer": offer,
            "letter": letter,
            "toast_tag": "success",
            "toast_text": "Lettre générée.",
        },
    )


@login_required
@require_POST
def save_letter(request: HttpRequest, pk: int) -> HttpResponse:
    letter = get_object_or_404(CoverLetter, pk=pk, user=request.user)
    letter.content = request.POST.get("content", "").strip()
    letter.save(update_fields=["content"])
    return render(
        request,
        "letters/partials/_letter_tab.html",
        {
            "offer": letter.job_offer,
            "letter": letter,
            "toast_tag": "success",
            "toast_text": "Lettre enregistrée.",
        },
    )


@login_required
def letter_pdf(request: HttpRequest, pk: int) -> HttpResponse:
    letter = get_object_or_404(CoverLetter, pk=pk, user=request.user)
    response = HttpResponse(render_letter_pdf(letter), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{letter_pdf_filename(letter)}"'
    return response


# --- CV adapté ------------------------------------------------------------


@login_required
@require_POST
def start_cv(request: HttpRequest, pk: int) -> HttpResponse:
    offer = get_object_or_404(JobOffer, pk=pk)
    return render(request, "letters/partials/_cv_generating.html", {"offer": offer})


@login_required
@require_POST
def run_cv(request: HttpRequest, pk: int) -> HttpResponse:
    offer = get_object_or_404(JobOffer, pk=pk)

    try:
        tailored_cv = generate_tailored_cv(request.user, offer)
    except ProfileMissingError:
        return render(request, "letters/partials/_profile_missing.html", {})
    except LLMError as exc:
        return render(
            request,
            "letters/partials/_generation_error.html",
            {"offer": offer, "error": str(exc), "kind": "cv"},
        )

    return render(
        request,
        "letters/partials/_cv_tab.html",
        {
            "offer": offer,
            "tailored_cv": tailored_cv,
            "toast_tag": "success",
            "toast_text": "CV adapté généré.",
        },
    )


@login_required
@require_POST
def save_cv(request: HttpRequest, pk: int) -> HttpResponse:
    tailored_cv = get_object_or_404(TailoredCV, pk=pk, user=request.user)

    experience_count = int(request.POST.get("experience_count") or 0)
    experiences = []
    for i in range(experience_count):
        poste = request.POST.get(f"experience_poste_{i}", "").strip()
        if not poste:
            continue
        experiences.append(
            {
                "poste": poste,
                "entreprise": request.POST.get(f"experience_entreprise_{i}", "").strip(),
                "description": request.POST.get(f"experience_description_{i}", "").strip(),
            }
        )

    tailored_cv.content = {
        "titre": request.POST.get("titre", "").strip(),
        "resume": request.POST.get("resume", "").strip(),
        "competences": [
            s.strip() for s in request.POST.get("competences", "").split(",") if s.strip()
        ],
        "experiences": experiences,
    }
    tailored_cv.save(update_fields=["content"])

    return render(
        request,
        "letters/partials/_cv_tab.html",
        {
            "offer": tailored_cv.job_offer,
            "tailored_cv": tailored_cv,
            "toast_tag": "success",
            "toast_text": "CV adapté enregistré.",
        },
    )


@login_required
def cv_pdf(request: HttpRequest, pk: int) -> HttpResponse:
    tailored_cv = get_object_or_404(TailoredCV, pk=pk, user=request.user)
    response = HttpResponse(render_tailored_cv_pdf(tailored_cv), content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="{tailored_cv_pdf_filename(tailored_cv)}"'
    )
    return response


# --- Préparation d'entretien -----------------------------------------------


@login_required
@require_POST
def start_interview(request: HttpRequest, pk: int) -> HttpResponse:
    offer = get_object_or_404(JobOffer, pk=pk)
    return render(request, "letters/partials/_interview_generating.html", {"offer": offer})


@login_required
@require_POST
def run_interview(request: HttpRequest, pk: int) -> HttpResponse:
    offer = get_object_or_404(JobOffer, pk=pk)

    try:
        interview = generate_interview_prep(request.user, offer)
    except ProfileMissingError:
        return render(request, "letters/partials/_profile_missing.html", {})
    except LLMError as exc:
        return render(
            request,
            "letters/partials/_generation_error.html",
            {"offer": offer, "error": str(exc), "kind": "interview"},
        )

    return render(
        request,
        "letters/partials/_interview_tab.html",
        {
            "offer": offer,
            "interview": interview,
            "toast_tag": "success",
            "toast_text": "Préparation d'entretien générée.",
        },
    )


@login_required
@require_POST
def save_interview(request: HttpRequest, pk: int) -> HttpResponse:
    interview = get_object_or_404(InterviewPrep, pk=pk, user=request.user)

    question_count = int(request.POST.get("question_count") or 0)
    questions = []
    for i in range(question_count):
        question = request.POST.get(f"question_{i}", "").strip()
        if not question:
            continue
        questions.append(
            {
                "question": question,
                "situation": request.POST.get(f"situation_{i}", "").strip(),
                "tache": request.POST.get(f"tache_{i}", "").strip(),
                "action": request.POST.get(f"action_{i}", "").strip(),
                "resultat": request.POST.get(f"resultat_{i}", "").strip(),
            }
        )

    interview.questions = questions
    interview.save(update_fields=["questions"])

    messages.success(request, "Préparation d'entretien enregistrée.")
    return render(
        request,
        "letters/partials/_interview_tab.html",
        {
            "offer": interview.job_offer,
            "interview": interview,
            "toast_tag": "success",
            "toast_text": "Préparation enregistrée.",
        },
    )
