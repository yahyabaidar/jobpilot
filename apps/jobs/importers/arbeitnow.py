import requests

from apps.jobs.utils import clean_html_to_text, detect_language, parse_unix_timestamp

from .base import BaseImporter, ImporterError

ARBEITNOW_URL = "https://www.arbeitnow.com/api/job-board-api"


class ArbeitnowImporter(BaseImporter):
    source = "arbeitnow"

    def fetch(self, limit: int = 50) -> list[dict]:
        try:
            response = requests.get(ARBEITNOW_URL, timeout=15)
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise ImporterError(f"Arbeitnow est indisponible : {exc}") from exc

        jobs = payload.get("data")
        if not isinstance(jobs, list):
            raise ImporterError("Réponse Arbeitnow inattendue : champ « data » manquant.")

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
            "external_id": job["slug"],
            "title": job.get("title") or "",
            "company": job.get("company_name") or "",
            "location": job.get("location") or "",
            "remote": bool(job.get("remote")),
            "description": description,
            "url": job.get("url") or "",
            "salary": "",
            "tags": job.get("tags") or [],
            "published_at": parse_unix_timestamp(job.get("created_at")),
            "language": detect_language(description),
        }
