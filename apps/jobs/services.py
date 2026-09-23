from apps.core.llm import complete_json

from .models import JobOffer

MANUAL_JOB_SYSTEM_PROMPT = (
    "Tu es un assistant qui extrait les informations clés d'une offre d'emploi collée par "
    "l'utilisateur. Réponds uniquement en JSON strict, en français. N'invente aucune information "
    "absente du texte fourni. Pour le type de contrat, choisis exactement une valeur parmi "
    "stage, alternance, cdi, cdd, freelance, inconnu — déduis-la du texte (mots comme « stage », "
    "« alternance », « CDI », « CDD », « freelance », « indépendant ») et réponds « inconnu » si "
    "le texte ne permet pas de trancher."
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
  "resume": "string",
  "type_contrat": "stage|alternance|cdi|cdd|freelance|inconnu",
  "duree_mois": 0,
  "date_debut": "string"
}
"""

MAX_MANUAL_TEXT_LENGTH = 8000

_VALID_CONTRACT_TYPES = {value for value, _ in JobOffer.ContractType.choices}


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
        "contract_type": data.get("contract_type") or JobOffer.ContractType.UNKNOWN,
        "duration_months": data.get("duration_months"),
        "start_date": data.get("start_date", ""),
    }
    return JobOffer.objects.update_or_create(
        source=data["source"],
        external_id=data["external_id"],
        defaults=defaults,
    )


def extract_job_offer(pasted_text: str) -> dict:
    prompt = f"Voici le texte d'une offre d'emploi :\n\n{pasted_text[:MAX_MANUAL_TEXT_LENGTH]}"
    data = complete_json(prompt, MANUAL_JOB_SYSTEM_PROMPT, MANUAL_JOB_SCHEMA_HINT)

    contract_type = str(data.get("type_contrat") or "").strip().lower()
    if contract_type not in _VALID_CONTRACT_TYPES:
        contract_type = JobOffer.ContractType.UNKNOWN

    try:
        duration_months = int(data.get("duree_mois"))
    except (TypeError, ValueError):
        duration_months = None

    return {
        "title": data.get("titre") or "",
        "company": data.get("entreprise") or "",
        "location": data.get("lieu") or "",
        "remote": bool(data.get("teletravail")),
        "tags": data.get("competences") or [],
        "language": (data.get("langue") or "")[:10],
        "salary": data.get("salaire") or "",
        "summary": data.get("resume") or "",
        "contract_type": contract_type,
        "duration_months": duration_months,
        "start_date": (data.get("date_debut") or "").strip()[:100],
    }
