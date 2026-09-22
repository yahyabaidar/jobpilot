from django.conf import settings

from apps.core.llm import complete_json
from apps.profiles.models import Profile, normalize_skill_name

from .models import CoverLetter, InterviewPrep, TailoredCV

MAX_OFFER_TEXT_LENGTH = 6000

LETTER_SYSTEM_PROMPTS = {
    "fr": (
        "Tu rédiges des lettres de motivation professionnelles en français. Ton ton est "
        "professionnel et sobre, jamais de flatterie creuse. Tu ne dois JAMAIS attribuer au "
        "candidat une compétence, un diplôme ou une expérience absente du profil fourni. "
        "La lettre fait entre 250 et 350 mots. Réponds uniquement en JSON strict."
    ),
    "en": (
        "You write professional cover letters in English. Your tone is professional and sober, "
        "never with hollow flattery. You must NEVER attribute to the candidate a skill, degree, "
        "or experience absent from the provided profile. The letter is 250 to 350 words long. "
        "Reply with strict JSON only."
    ),
}

LETTER_SCHEMA_HINT = """
Réponds uniquement avec un objet JSON de cette forme, sans aucun texte autour :
{"lettre": "string (250 à 350 mots)"}
"""

TAILORED_CV_SYSTEM_PROMPT = (
    "Tu adaptes le CV d'un candidat pour une offre précise : tu réordonnes et reformules ses "
    "VRAIES expériences et compétences pour mettre en avant leur pertinence, en intégrant les "
    "mots-clés de l'offre pour les filtres ATS. RÈGLE ABSOLUE : tu ne dois JAMAIS inventer une "
    "expérience, un diplôme ou une compétence qui n'est pas explicitement présente dans le "
    "profil fourni. Réponds uniquement en JSON strict, en français."
)

TAILORED_CV_SCHEMA_HINT = """
Réponds uniquement avec un objet JSON de cette forme, sans aucun texte autour :
{
  "titre": "string",
  "resume": "string",
  "competences": ["string"],
  "experiences": [{"poste": "string", "entreprise": "string", "description": "string"}]
}
"""

INTERVIEW_SYSTEM_PROMPT = (
    "Tu prépares un candidat à un entretien pour une offre précise. Tu proposes des questions "
    "probables et, pour chacune, une trame de réponse au format STAR (Situation, Tâche, Action, "
    "Résultat) fondée sur les VRAIES expériences du profil fourni. N'invente aucune expérience. "
    "Réponds uniquement en JSON strict, en français."
)

INTERVIEW_SCHEMA_HINT = """
Réponds uniquement avec un objet JSON de cette forme, avec exactement 5 questions dont au moins
une portant sur une compétence qui manque au candidat par rapport à l'offre :
{
  "questions": [
    {
      "question": "string",
      "situation": "string",
      "tache": "string",
      "action": "string",
      "resultat": "string"
    }
  ]
}
"""


class ProfileMissingError(Exception):
    pass


def _get_profile_or_raise(user) -> Profile:
    profile = (
        Profile.objects.filter(user=user)
        .prefetch_related("skills", "experiences", "educations")
        .first()
    )
    if profile is None:
        raise ProfileMissingError("Envoie d'abord ton CV.")
    return profile


def _format_profile(profile: Profile) -> str:
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
    return f"""Titre : {profile.title or "non précisé"}
Résumé : {profile.summary or "non précisé"}
Ville : {profile.city or "non précisée"}
Compétences : {skills_line}
Expériences :
{experiences_lines}
Formations :
{educations_lines}"""


def _format_offer(job_offer) -> str:
    return f"""Titre : {job_offer.title}
Entreprise : {job_offer.company or "non précisée"}
Lieu : {job_offer.location or "non précisé"}
Télétravail : {"oui" if job_offer.remote else "non"}
Mots-clés : {", ".join(job_offer.tags) or "aucun"}
Description :
{job_offer.description[:MAX_OFFER_TEXT_LENGTH]}"""


def generate_cover_letter(user, job_offer, language: str = "fr") -> CoverLetter:
    if language not in CoverLetter.Language.values:
        language = CoverLetter.Language.FR

    profile = _get_profile_or_raise(user)
    system = LETTER_SYSTEM_PROMPTS.get(language, LETTER_SYSTEM_PROMPTS["fr"])
    prompt = f"""Profil du candidat :
{_format_profile(profile)}

Offre d'emploi :
{_format_offer(job_offer)}"""

    data = complete_json(prompt, system, LETTER_SCHEMA_HINT)
    content = str(data.get("lettre") or "").strip()

    return CoverLetter.objects.create(
        user=user,
        job_offer=job_offer,
        language=language,
        content=content,
        llm_model=settings.LLM_MODEL,
    )


def _sanitize_tailored_cv(data: dict, profile: Profile) -> dict:
    allowed_skills = {s.normalized_name: s.display_name for s in profile.skills.all()}
    kept_skills = []
    for raw in data.get("competences") or []:
        normalized = normalize_skill_name(str(raw))
        if normalized in allowed_skills and allowed_skills[normalized] not in kept_skills:
            kept_skills.append(allowed_skills[normalized])

    allowed_titles = {normalize_skill_name(e.title) for e in profile.experiences.all()}
    kept_experiences = []
    for raw in data.get("experiences") or []:
        title = str(raw.get("poste") or "").strip()
        if normalize_skill_name(title) in allowed_titles:
            kept_experiences.append(
                {
                    "poste": title,
                    "entreprise": str(raw.get("entreprise") or "").strip(),
                    "description": str(raw.get("description") or "").strip(),
                }
            )

    return {
        "titre": str(data.get("titre") or profile.title or "").strip(),
        "resume": str(data.get("resume") or "").strip(),
        "competences": kept_skills,
        "experiences": kept_experiences,
    }


def generate_tailored_cv(user, job_offer) -> TailoredCV:
    profile = _get_profile_or_raise(user)
    prompt = f"""Profil du candidat :
{_format_profile(profile)}

Offre d'emploi :
{_format_offer(job_offer)}"""

    data = complete_json(prompt, TAILORED_CV_SYSTEM_PROMPT, TAILORED_CV_SCHEMA_HINT)
    content = _sanitize_tailored_cv(data, profile)

    return TailoredCV.objects.create(
        user=user, job_offer=job_offer, content=content, llm_model=settings.LLM_MODEL
    )


def generate_interview_prep(user, job_offer) -> InterviewPrep:
    profile = _get_profile_or_raise(user)
    prompt = f"""Profil du candidat :
{_format_profile(profile)}

Offre d'emploi :
{_format_offer(job_offer)}"""

    data = complete_json(prompt, INTERVIEW_SYSTEM_PROMPT, INTERVIEW_SCHEMA_HINT)
    questions = []
    for raw in (data.get("questions") or [])[:5]:
        questions.append(
            {
                "question": str(raw.get("question") or "").strip(),
                "situation": str(raw.get("situation") or "").strip(),
                "tache": str(raw.get("tache") or "").strip(),
                "action": str(raw.get("action") or "").strip(),
                "resultat": str(raw.get("resultat") or "").strip(),
            }
        )

    return InterviewPrep.objects.create(
        user=user, job_offer=job_offer, questions=questions, llm_model=settings.LLM_MODEL
    )
