import requests
from django.conf import settings

from apps.jobs.utils import (
    clean_html_to_text,
    deduce_contract_type,
    detect_language,
    parse_iso_datetime,
)

from .base import BaseImporter, ImporterError

TOKEN_URL = "https://entreprise.francetravail.fr/connexion/oauth2/access_token"
SEARCH_URL = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"
SCOPE = "api_offresdemploiv2 o2dsoffre"


class FranceTravailImporter(BaseImporter):
    source = "france_travail"

    def fetch(self, limit: int = 50) -> list[dict]:
        client_id = settings.FRANCE_TRAVAIL_CLIENT_ID
        client_secret = settings.FRANCE_TRAVAIL_CLIENT_SECRET
        if not client_id or not client_secret:
            raise ImporterError(
                "France Travail n'est pas configuré : renseignez FRANCE_TRAVAIL_CLIENT_ID et "
                "FRANCE_TRAVAIL_CLIENT_SECRET dans .env pour activer cette source."
            )

        token = self._get_access_token(client_id, client_secret)
        jobs = self._search(token, limit)

        normalized = []
        for job in jobs:
            try:
                normalized.append(self._normalize(job))
            except (KeyError, TypeError):
                continue
        return normalized

    def _get_access_token(self, client_id: str, client_secret: str) -> str:
        try:
            response = requests.post(
                TOKEN_URL,
                params={"realm": "/partenaire"},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "scope": f"{SCOPE} application_{client_id}",
                },
                timeout=15,
            )
            response.raise_for_status()
            return response.json()["access_token"]
        except (requests.RequestException, ValueError, KeyError) as exc:
            raise ImporterError(f"Authentification France Travail échouée : {exc}") from exc

    def _search(self, token: str, limit: int) -> list[dict]:
        range_end = max(0, min(limit, 150) - 1)
        try:
            response = requests.get(
                SEARCH_URL,
                headers={"Authorization": f"Bearer {token}"},
                params={"motsCles": "informatique", "range": f"0-{range_end}", "sort": 1},
                timeout=15,
            )
            if response.status_code not in (200, 206):
                response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise ImporterError(f"France Travail est indisponible : {exc}") from exc

        jobs = payload.get("resultats")
        if not isinstance(jobs, list):
            raise ImporterError("Réponse France Travail inattendue : champ « resultats » manquant.")
        return jobs[:limit]

    def _normalize(self, job: dict) -> dict:
        description = clean_html_to_text(job.get("description") or "")
        lieu = job.get("lieuTravail") or {}
        entreprise = job.get("entreprise") or {}
        origine = job.get("origineOffre") or {}
        salaire = job.get("salaire") or {}
        competences = job.get("competences") or []

        return {
            "source": self.source,
            "external_id": str(job["id"]),
            "title": job.get("intitule") or "",
            "company": entreprise.get("nom") or "",
            "location": lieu.get("libelle") or "",
            "remote": False,
            "description": description,
            "url": origine.get("urlOrigine") or "",
            "salary": salaire.get("libelle") or "",
            "tags": [c.get("libelle") for c in competences if c.get("libelle")],
            "published_at": parse_iso_datetime(job.get("dateCreation")),
            "language": detect_language(description) or "fr",
            "contract_type": deduce_contract_type(
                job.get("typeContratLibelle") or "", is_alternance=bool(job.get("alternance"))
            ),
        }
