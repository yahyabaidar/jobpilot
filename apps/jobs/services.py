from apps.core.llm import complete_json

from .models import JobOffer

MANUAL_JOB_SYSTEM_PROMPT = (
    "Tu es un assistant qui extrait les informations clés d'une offre d'emploi collée par "
    "l'utilisateur. Réponds uniquement en JSON strict, en français. N'invente aucune information "
    "absente du texte fourni."
)

MANUAL_JOB_SCHEMA_HINT = """
Réponds uniquement avec un objet JSON de cette forme, sans aucun texte autour :
{
  "titre": "string",
  "entreprise": "string",
  "lieu": "string",
  "teletravail": true,
  "competences": ["string"],
  "langue": "fr|en|de|...",
  "salaire": "string",
  "resume": "string"
}
"""

MAX_MANUAL_TEXT_LENGTH = 8000


def upsert_job_offer(data: dict) -> tuple[JobOffer, bool]:
    """Create or update a JobOffer from normalized importer data. Returns (offer, created)."""
    defaults = {
        "title": data["title"],
        "company": data.get("company", ""),
        "location": data.get("location", ""),
        "remote": data.get("remote", False),
        "description": data.get("description", ""),
        "url": data.get("url", ""),
        "salary": data.get("salary", ""),
        "tags": data.get("tags", []),
        "published_at": data.get("published_at"),
        "language": data.get("language", ""),
    }
    return JobOffer.objects.update_or_create(
        source=data["source"],
        external_id=data["external_id"],
        defaults=defaults,
    )


def extract_job_offer(pasted_text: str) -> dict:
    prompt = f"Voici le texte d'une offre d'emploi :\n\n{pasted_text[:MAX_MANUAL_TEXT_LENGTH]}"
    data = complete_json(prompt, MANUAL_JOB_SYSTEM_PROMPT, MANUAL_JOB_SCHEMA_HINT)
    return {
        "title": data.get("titre") or "",
        "company": data.get("entreprise") or "",
        "location": data.get("lieu") or "",
        "remote": bool(data.get("teletravail")),
        "tags": data.get("competences") or [],
        "language": (data.get("langue") or "")[:10],
        "salary": data.get("salaire") or "",
        "summary": data.get("resume") or "",
    }
