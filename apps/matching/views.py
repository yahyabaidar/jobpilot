from django.contrib.auth.decorators import login_required
from django.db.models import F
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from apps.core.llm import LLMError
from apps.jobs.models import JobOffer
from apps.profiles.models import Profile

from .models import Match
from .services import ProfileMissingError, analyze_match

BATCH_ANALYZE_LIMIT = 20


@login_required
@require_POST
def start_analyze(request: HttpRequest, pk: int) -> HttpResponse:
    offer = get_object_or_404(JobOffer, pk=pk)
    return render(request, "matching/partials/_analyzing.html", {"offer": offer})


@login_required
@require_POST
def run_analyze(request: HttpRequest, pk: int) -> HttpResponse:
    offer = get_object_or_404(JobOffer, pk=pk)

    try:
        match = analyze_match(request.user, offer)
    except ProfileMissingError:
        return render(
            request,
            "matching/partials/_score_panel.html",
            {"offer": offer, "match": None, "has_profile": False},
        )
    except LLMError as exc:
        return render(
            request,
            "matching/partials/_analysis_error.html",
            {"offer": offer, "error": str(exc)},
        )

    return render(
        request,
        "matching/partials/_score_result.html",
        {"offer": offer, "match": match, "toast_tag": "success", "toast_text": "Analyse terminée."},
    )


@login_required
@require_POST
def start_batch(request: HttpRequest) -> HttpResponse:
    if not Profile.objects.filter(user=request.user).exists():
        return render(request, "matching/partials/_batch_complete.html", {"profile_missing": True})

    analyzed_ids = Match.objects.filter(user=request.user).values_list("job_offer_id", flat=True)
    pending_ids = list(
        JobOffer.objects.exclude(id__in=analyzed_ids)
        .order_by(F("published_at").desc(nulls_last=True))
        .values_list("id", flat=True)[:BATCH_ANALYZE_LIMIT]
    )
    if not pending_ids:
        return render(request, "matching/partials/_batch_complete.html", {"already_done": True})

    return render(
        request,
        "matching/partials/_batch_progress.html",
        {"remaining_ids": pending_ids, "total": len(pending_ids), "done": 0},
    )


@login_required
@require_POST
def batch_step(request: HttpRequest) -> HttpResponse:
    remaining_raw = request.POST.get("remaining_ids", "")
    remaining_ids = [int(x) for x in remaining_raw.split(",") if x.strip().isdigit()]
    total = int(request.POST.get("total") or len(remaining_ids))
    done = int(request.POST.get("done") or 0)

    if not remaining_ids:
        return render(request, "matching/partials/_batch_complete.html", {"done": done})

    current_id, *rest = remaining_ids
    offer = JobOffer.objects.filter(pk=current_id).first()
    if offer is not None:
        try:
            analyze_match(request.user, offer)
        except (ProfileMissingError, LLMError):
            pass

    return render(
        request,
        "matching/partials/_batch_progress.html",
        {"remaining_ids": rest, "total": total, "done": done + 1},
    )
