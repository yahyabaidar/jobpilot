import pdfplumber
from django.db import transaction

from apps.core.llm import LLMError, complete_json

from .models import CVDocument, Education, Experience, Profile, Skill, normalize_skill_name

MAX_CV_TEXT_LENGTH = 12000

CV_SYSTEM_PROMPT = (
    "Tu es un expert en recrutement. Tu extrais les informations d'un CV et tu les structures "
    "en JSON strict, en français. N'invente aucune information absente du texte fourni. "
    "Si une information est manquante, utilise une chaîne vide ou une liste vide."
)

CV_JSON_SCHEMA_HINT = """
Réponds uniquement avec un objet JSON de cette forme, sans aucun texte autour :
{
  "titre": "string",
  "resume": "string",
  "ville": "string",
  "annees_experience": 0,
  "competences": [{"nom": "string", "categorie": "technique|outil|langue|savoir-être"}],
  "experiences": [
    {
      "poste": "string", "entreprise": "string",
      "date_debut": "string", "date_fin": "string", "description": "string"
    }
  ],
  "formations": [{"diplome": "string", "etablissement": "string", "annee": "string"}]
}
"""

_CATEGORY_LABELS = {
    "technique": Skill.Category.TECHNICAL,
    "outil": Skill.Category.TOOL,
    "langue": Skill.Category.LANGUAGE,
    "savoir-etre": Skill.Category.SOFT_SKILL,
    "savoir etre": Skill.Category.SOFT_SKILL,
}


class CVParsingError(Exception):
    pass


def extract_text(file_obj) -> str:
    try:
        with pdfplumber.open(file_obj) as pdf:
            pages_text = [page.extract_text() or "" for page in pdf.pages]
    except Exception as exc:
        raise CVParsingError(f"Impossible de lire le fichier PDF : {exc}") from exc

    text = "\n".join(page.strip() for page in pages_text if page.strip())
    if not text:
        raise CVParsingError(
            "Aucun texte n'a pu être extrait de ce PDF. Il est peut-être vide ou scanné (image)."
        )
    return text


def parse_cv(text: str) -> dict:
    prompt = f"Voici le texte extrait d'un CV :\n\n{text[:MAX_CV_TEXT_LENGTH]}"
    data = complete_json(prompt, CV_SYSTEM_PROMPT, CV_JSON_SCHEMA_HINT)
    return {
        "titre": data.get("titre") or "",
        "resume": data.get("resume") or "",
        "ville": data.get("ville") or "",
        "annees_experience": data.get("annees_experience") or None,
        "competences": data.get("competences") or [],
        "experiences": data.get("experiences") or [],
        "formations": data.get("formations") or [],
    }


def _resolve_category(raw: str) -> str:
    return _CATEGORY_LABELS.get(normalize_skill_name(raw or ""), Skill.Category.TECHNICAL)


def save_profile(user, data: dict) -> Profile:
    with transaction.atomic():
        profile, _ = Profile.objects.update_or_create(
            user=user,
            defaults={
                "title": data.get("titre", ""),
                "summary": data.get("resume", ""),
                "years_of_experience": data.get("annees_experience") or None,
                "city": data.get("ville", ""),
            },
        )
        profile.skills.all().delete()
        profile.experiences.all().delete()
        profile.educations.all().delete()

        seen_names = set()
        skills = []
        for raw in data.get("competences", []):
            display_name = (raw.get("nom") or "").strip()
            if not display_name:
                continue
            normalized = normalize_skill_name(display_name)
            if normalized in seen_names:
                continue
            seen_names.add(normalized)
            skills.append(
                Skill(
                    profile=profile,
                    display_name=display_name,
                    normalized_name=normalized,
                    category=_resolve_category(raw.get("categorie", "")),
                )
            )
        Skill.objects.bulk_create(skills)

        experiences = []
        for index, raw in enumerate(data.get("experiences", [])):
            title = (raw.get("poste") or "").strip()
            if not title:
                continue
            experiences.append(
                Experience(
                    profile=profile,
                    title=title,
                    company=(raw.get("entreprise") or "").strip(),
                    start_date=(raw.get("date_debut") or "").strip(),
                    end_date=(raw.get("date_fin") or "").strip(),
                    description=(raw.get("description") or "").strip(),
                    order=index,
                )
            )
        Experience.objects.bulk_create(experiences)

        educations = []
        for index, raw in enumerate(data.get("formations", [])):
            degree = (raw.get("diplome") or "").strip()
            if not degree:
                continue
            educations.append(
                Education(
                    profile=profile,
                    degree=degree,
                    institution=(raw.get("etablissement") or "").strip(),
                    year=str(raw.get("annee") or "").strip(),
                    order=index,
                )
            )
        Education.objects.bulk_create(educations)

    return profile


def analyze_cv(cv_document: CVDocument) -> Profile:
    cv_document.status = CVDocument.Status.PROCESSING
    cv_document.save(update_fields=["status"])

    try:
        cv_document.file.open("rb")
        try:
            text = extract_text(cv_document.file)
        finally:
            cv_document.file.close()

        data = parse_cv(text)
        profile = save_profile(cv_document.user, data)
    except (CVParsingError, LLMError) as exc:
        cv_document.status = CVDocument.Status.ERROR
        cv_document.error_message = str(exc)
        cv_document.save(update_fields=["status", "error_message"])
        raise

    cv_document.status = CVDocument.Status.DONE
    cv_document.error_message = ""
    cv_document.extracted_text = text
    cv_document.save(update_fields=["status", "error_message", "extracted_text"])
    return profile
