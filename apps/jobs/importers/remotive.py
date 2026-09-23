import requests

from apps.jobs.utils import (
    clean_html_to_text,
    deduce_contract_type,
    detect_language,
    parse_iso_datetime,
)

from .base import BaseImporter, ImporterError

REMOTIVE_URL = "https://remotive.com/api/remote-jobs"


class RemotiveImporter(BaseImporter):
    source = "remotive"

    def fetch(self, limit: int = 50) -> list[dict]:
        try:
            response = requests.get(REMOTIVE_URL, params={"limit": limit}, timeout=15)
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise ImporterError(f"Remotive est indisponible : {exc}") from exc

        jobs = payload.get("jobs")
        if not isinstance(jobs, list):
            raise ImporterError("Réponse Remotive inattendue : champ « jobs » manquant.")

        normalized = []
        for job in jobs[:limit]:
            try:
                normalized.append(self._normalize(job))
            except (KeyError, TypeError):
                continue
        return normalized

    def _normalize(self, job: dict) -> dict:
        description = clean_html_to_text(job.get("description") or "")
        return {
            "source": self.source,
            "external_id": str(job["id"]),
            "title": job.get("title") or "",
            "company": job.get("company_name") or "",
            "location": job.get("candidate_required_location") or "",
            "remote": True,
            "description": description,
            "url": job.get("url") or "",
            "salary": job.get("salary") or "",
            "tags": job.get("tags") or [],
            "published_at": parse_iso_datetime(job.get("publication_date")),
            "language": detect_language(description),
            "contract_type": deduce_contract_type(job.get("job_type") or ""),
        }
