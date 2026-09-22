from datetime import timedelta
from uuid import uuid4

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import F, IntegerField, OuterRef, Q, Subquery
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.applications.models import Application
from apps.core.llm import LLMError
from apps.jobs.importers import IMPORTERS
from apps.jobs.services import extract_job_offer, upsert_job_offer
from apps.jobs.utils import is_disallowed_source
from apps.matching.models import Match
from apps.profiles.models import Profile

from .models import JobOffer

PERIOD_DAYS = {"7": 7, "30": 30, "90": 90}
FRIENDLY_SOURCE_NAMES = {"remotive": "Remotive", "arbeitnow": "Arbeitnow"}


def _is_htmx(request: HttpRequest) -> bool:
    return request.headers.get("HX-Request") == "true"


def _list_context(request: HttpRequest) -> dict:
    match_score_subquery = Match.objects.filter(user=request.user, job_offer=OuterRef("pk")).values(
        "score"
    )[:1]
    offers = JobOffer.objects.annotate(
        my_score=Subquery(match_score_subquery, output_field=IntegerField())
    )

    query = request.GET.get("q", "").strip()
    if query:
        offers = offers.filter(
            Q(title__icontains=query)
            | Q(company__icontains=query)
            | Q(description__icontains=query)
        )

    source = request.GET.get("source", "")
    if source:
        offers = offers.filter(source=source)

    remote = request.GET.get("remote", "")
    if remote == "1":
        offers = offers.filter(remote=True)

    location = request.GET.get("location", "").strip()
    if location:
        offers = offers.filter(location__icontains=location)

    period = request.GET.get("period", "")
    days = PERIOD_DAYS.get(period)
    if days:
        since = timezone.now() - timedelta(days=days)
        offers = offers.filter(published_at__gte=since)

    min_score = request.GET.get("min_score", "").strip()
    if min_score.isdigit():
        offers = offers.filter(my_score__gte=int(min_score))

    sort = request.GET.get("sort", "")
    if sort == "score":
        offers = offers.order_by(
            F("my_score").desc(nulls_last=True), F("published_at").desc(nulls_last=True)
        )
    else:
        offers = offers.order_by(F("published_at").desc(nulls_last=True), "-imported_at")

    paginator = Paginator(offers, 12)
    page_obj = paginator.get_page(request.GET.get("page"))

    return {
        "page_obj": page_obj,
        "query": query,
        "selected_source": source,
        "remote": remote,
        "location": location,
        "period": period,
        "min_score": min_score,
        "sort": sort,
        "sources": JobOffer.Source.choices,
        "has_any_offer": JobOffer.objects.exists(),
    }


@login_required
def index(request: HttpRequest) -> HttpResponse:
    context = _list_context(request)
    context["active_nav"] = "jobs"
    template = "jobs/partials/_results.html" if _is_htmx(request) else "jobs/index.html"
    return render(request, template, context)


@login_required
@require_POST
def start_import(request: HttpRequest) -> HttpResponse:
    return render(request, "jobs/partials/_importing.html", {})


@login_required
@require_POST
def run_import(request: HttpRequest) -> HttpResponse:
    total_created = 0
    failed_sources = []

    for source_name, importer_cls in IMPORTERS.items():
        try:
            jobs = importer_cls().fetch(limit=50)
        except Exception:
            failed_sources.append(source_name)
            continue

        for data in jobs:
            if not data.get("title") or not data.get("url"):
                continue
            _, was_created = upsert_job_offer(data)
            if was_created:
                total_created += 1

    if failed_sources:
        names = ", ".join(FRIENDLY_SOURCE_NAMES.get(s, s) for s in failed_sources)
        toast_tag = "warning" if total_created else "error"
        toast_text = (
            f"{names} indisponible pour le moment. "
            f"{total_created} nouvelle(s) offre(s) importée(s) depuis les autres sources. "
            "Vous pouvez aussi ajouter une offre manuellement."
        )
    else:
        toast_tag = "success"
        toast_text = f"{total_created} nouvelle(s) offre(s) importée(s)."

    context = _list_context(request)
    context["toast_tag"] = toast_tag
    context["toast_text"] = toast_text
    return render(request, "jobs/partials/_results.html", context)


@login_required
@require_POST
def check_url(request: HttpRequest) -> HttpResponse:
    url = request.POST.get("url", "").strip()
    return render(
        request,
        "jobs/partials/_url_notice.html",
        {"url": url, "blocked": is_disallowed_source(url)},
    )


@login_required
def manual_create(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        pasted_text = request.POST.get("pasted_text", "").strip()
        url = request.POST.get("url", "").strip()
        if not pasted_text:
            return render(
                request,
                "jobs/partials/_manual_paste_form.html",
                {
                    "url": url,
                    "pasted_text": pasted_text,
                    "error": "Collez le texte de l'offre avant de continuer.",
                },
            )
        return render(
            request,
            "jobs/partials/_manual_analyzing.html",
            {"pasted_text": pasted_text, "url": url},
        )

    return render(request, "jobs/manual_create.html", {"active_nav": "jobs"})


@login_required
@require_POST
def manual_analyze(request: HttpRequest) -> HttpResponse:
    pasted_text = request.POST.get("pasted_text", "").strip()
    url = request.POST.get("url", "").strip()

    try:
        extracted = extract_job_offer(pasted_text)
    except LLMError as exc:
        return render(
            request,
            "jobs/partials/_manual_paste_form.html",
            {
                "url": url,
                "pasted_text": pasted_text,
                "error": f"L'analyse de l'offre a échoué : {exc}",
            },
        )

    return render(
        request,
        "jobs/partials/_manual_preview.html",
        {"extracted": extracted, "url": url, "pasted_text": pasted_text},
    )


@login_required
@require_POST
def manual_save(request: HttpRequest) -> HttpResponse:
    title = request.POST.get("title", "").strip()
    if not title:
        messages.error(request, "Le titre est obligatoire.")
        return redirect("jobs:manual_create")

    tags = [tag.strip() for tag in request.POST.get("tags", "").split(",") if tag.strip()]

    offer = JobOffer.objects.create(
        source=JobOffer.Source.MANUAL,
        external_id=uuid4().hex,
        title=title,
        company=request.POST.get("company", "").strip(),
        location=request.POST.get("location", "").strip(),
        remote=request.POST.get("remote") == "1",
        description=request.POST.get("description", "").strip(),
        url=request.POST.get("url", "").strip(),
        salary=request.POST.get("salary", "").strip(),
        language=request.POST.get("language", "").strip()[:10],
        tags=tags,
        added_by=request.user,
        published_at=timezone.now(),
    )
    messages.success(request, "Offre ajoutée avec succès.")
    return redirect("jobs:detail", pk=offer.pk)


@login_required
def detail(request: HttpRequest, pk: int) -> HttpResponse:
    offer = get_object_or_404(JobOffer, pk=pk)
    already_applied = Application.objects.filter(user=request.user, job_offer=offer).exists()
    match = Match.objects.filter(user=request.user, job_offer=offer).first()
    has_profile = Profile.objects.filter(user=request.user).exists()
    return render(
        request,
        "jobs/detail.html",
        {
            "active_nav": "jobs",
            "offer": offer,
            "already_applied": already_applied,
            "match": match,
            "has_profile": has_profile,
        },
    )


@login_required
@require_POST
def apply(request: HttpRequest, pk: int) -> HttpResponse:
    offer = get_object_or_404(JobOffer, pk=pk)
    if not offer.url:
        return HttpResponseBadRequest("Cette offre n'a pas de lien.")

    _, created = Application.objects.get_or_create(
        user=request.user, job_offer=offer, defaults={"status": Application.Status.SENT}
    )
    text = (
        "Offre ajoutée à vos candidatures." if created else "Vous aviez déjà postulé à cette offre."
    )
    return render(request, "partials/_toast_oob.html", {"tag": "success", "text": text})
