import time

from django.conf import settings

from apps.core.llm import complete_json
from apps.profiles.models import Profile, normalize_skill_name

from .models import Match

# Named, easy-to-change weights. Must sum to 1.0.
WEIGHT_SKILLS = 0.40
WEIGHT_EXPERIENCE = 0.25
WEIGHT_EDUCATION = 0.10
WEIGHT_LOCATION = 0.15
WEIGHT_LANGUAGE = 0.10

MAX_OFFER_TEXT_LENGTH = 6000

MATCH_SYSTEM_PROMPT = (
    "Tu es un expert en recrutement qui évalue la compatibilité entre le profil d'un candidat et "
    "une offre d'emploi. Réponds uniquement en JSON strict, en français. Base-toi uniquement sur "
    "les informations fournies, n'invente rien. Sois direct et honnête, y compris sur les signaux "
    "d'annonce douteuse : description très vague, promesses de salaire irréalistes, demande "
    "d'argent ou de documents personnels, entreprise non identifiable, offre visiblement "
    "republiée en boucle. Explique toujours pourquoi, en français."
)

MATCH_SCHEMA_HINT = """
Réponds uniquement avec un objet JSON de cette forme, sans aucun texte autour :
{
  "scores": {
    "competences": 0,
    "experience": 0,
    "formation": 0,
    "lieu": 0,
    "langue": 0
  },
  "competences_correspondantes": ["string"],
  "competences_manquantes": ["string"],
  "conseil": "string (1 à 2 phrases)",
  "legitimite": {
    "niveau": "fiable|a_verifier|suspect",
    "raisons": ["string"]
  }
}
Chaque score est un entier entre 0 et 100.
"""

_LEGITIMACY_LABELS = {
    "fiable": Match.Legitimacy.RELIABLE,
    "a verifier": Match.Legitimacy.TO_VERIFY,
    "suspect": Match.Legitimacy.SUSPICIOUS,
}

_AXIS_JSON_KEYS = {
    "skills_score": "competences",
    "experience_score": "experience",
    "education_score": "formation",
    "location_score": "lieu",
    "language_score": "langue",
}


class ProfileMissingError(Exception):
    pass


def compute_skill_overlap(profile_skill_names: set[str], offer_tag_names: set[str]) -> dict:
    """No-AI quick pass: overlap of normalized skill names. Used to ground the LLM prompt."""
    if not offer_tag_names:
        return {"matched": 0, "total_required": 0, "score": 0}
    matched = profile_skill_names & offer_tag_names
    total_required = len(offer_tag_names)
    score = round(len(matched) / total_required * 100)
    return {"matched": len(matched), "total_required": total_required, "score": score}


def compute_global_score(axis_scores: dict) -> int:
    weighted = (
        axis_scores["skills_score"] * WEIGHT_SKILLS
        + axis_scores["experience_score"] * WEIGHT_EXPERIENCE
        + axis_scores["education_score"] * WEIGHT_EDUCATION
        + axis_scores["location_score"] * WEIGHT_LOCATION
        + axis_scores["language_score"] * WEIGHT_LANGUAGE
    )
    return round(weighted)


def _clamp_score(value) -> int:
    try:
        value = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, min(100, value))


def _extract_axis_scores(data: dict) -> dict:
    raw = data.get("scores") or {}
    return {field: _clamp_score(raw.get(json_key)) for field, json_key in _AXIS_JSON_KEYS.items()}


def _resolve_legitimacy(data: dict) -> tuple[str, list]:
    legitimacy_data = data.get("legitimite") or {}
    key = str(legitimacy_data.get("niveau") or "").strip().lower().replace("_", " ")
    level = _LEGITIMACY_LABELS.get(key, Match.Legitimacy.TO_VERIFY)
    reasons = legitimacy_data.get("raisons") or []
    return level, reasons


def _build_prompt(profile: Profile, job_offer, quick: dict) -> str:
    skills_line = (
        ", ".join(f"{s.display_name} ({s.get_category_display()})" for s in profile.skills.all())
        or "aucune"
    )
    experiences_lines = (
        "\n".join(
            f"- {e.title} chez {e.company} ({e.start_date} - {e.end_date}) : {e.description}"
            for e in profile.experiences.all()
        )
        or "aucune"
    )
    educations_lines = (
        "\n".join(f"- {e.degree}, {e.institution} ({e.year})" for e in profile.educations.all())
        or "aucune"
    )

    return f"""Profil du candidat :
Titre : {profile.title or "non précisé"}
Résumé : {profile.summary or "non précisé"}
Ville : {profile.city or "non précisée"}
Années d'expérience : {profile.years_of_experience if profile.years_of_experience is not None
else "non précisé"}
Compétences : {skills_line}
Expériences :
{experiences_lines}
Formations :
{educations_lines}

Offre d'emploi :
Titre : {job_offer.title}
Entreprise : {job_offer.company or "non précisée"}
Lieu : {job_offer.location or "non précisé"}
Télétravail : {"oui" if job_offer.remote else "non"}
Salaire annoncé : {job_offer.salary or "non précisé"}
Mots-clés de l'offre : {", ".join(job_offer.tags) or "aucun"}
Description :
{job_offer.description[:MAX_OFFER_TEXT_LENGTH]}

Aperçu rapide calculé automatiquement (recoupement simple des mots-clés, à affiner avec le
profil complet) : {quick["matched"]} correspondance(s) sur {quick["total_required"]} mot(s)-clé(s)
de l'offre.
"""


def analyze_match(user, job_offer) -> Match:
    profile = (
        Profile.objects.filter(user=user)
        .prefetch_related("skills", "experiences", "educations")
        .first()
    )
    if profile is None:
        raise ProfileMissingError("Envoie d'abord ton CV.")

    profile_skill_names = {s.normalized_name for s in profile.skills.all()}
    offer_tag_names = {normalize_skill_name(tag) for tag in job_offer.tags if tag}
    quick = compute_skill_overlap(profile_skill_names, offer_tag_names)

    prompt = _build_prompt(profile, job_offer, quick)

    started = time.monotonic()
    data = complete_json(prompt, MATCH_SYSTEM_PROMPT, MATCH_SCHEMA_HINT)
    duration = time.monotonic() - started

    axis_scores = _extract_axis_scores(data)
    legitimacy, legitimacy_reasons = _resolve_legitimacy(data)

    match, _ = Match.objects.update_or_create(
        user=user,
        job_offer=job_offer,
        defaults={
            "score": compute_global_score(axis_scores),
            **axis_scores,
            "matched_skills": data.get("competences_correspondantes") or [],
            "missing_skills": data.get("competences_manquantes") or [],
            "advice": data.get("conseil") or "",
            "legitimacy": legitimacy,
            "legitimacy_reasons": legitimacy_reasons,
            "llm_model": settings.LLM_MODEL,
            "duration_seconds": duration,
        },
    )
    return match
