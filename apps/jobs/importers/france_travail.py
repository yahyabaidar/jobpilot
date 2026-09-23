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

# France Travail has no dedicated "stage" code: real internship postings are coded as
# natureContrat "E2" (Contrat apprentissage) or "FS" (Cont. professionnalisation), often with
# typeContrat=CDD and alternance=true — confirmed by querying /referentiel/naturesContrats and
# by inspecting real "Stage de fin d'études / Alternance" postings returned by the search API.
DEFAULT_NATURE_CONTRAT = "E2,FS"
DEFAULT_KEYWORDS = "développeur,développement,python,java,web,data,informatique"


class FranceTravailImporter(BaseImporter):
    source = "france_travail"

    def fetch(
        self,
        limit: int = 50,
        contract_type: str | None = None,
        keywords: str | None = None,
        **kwargs,
    ) -> list[dict]:
        client_id = settings.FRANCE_TRAVAIL_CLIENT_ID
        client_secret = settings.FRANCE_TRAVAIL_CLIENT_SECRET
        if not client_id or not client_secret:
            raise ImporterError(
                "France Travail n'est pas configuré : renseignez FRANCE_TRAVAIL_CLIENT_ID et "
                "FRANCE_TRAVAIL_CLIENT_SECRET dans .env pour activer cette source."
            )

        token = self._get_access_token(client_id, client_secret)
        jobs = self._search(
            token,
            limit,
            contract_type or DEFAULT_NATURE_CONTRAT,
            keywords or DEFAULT_KEYWORDS,
        )

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

    def _search(self, token: str, limit: int, nature_contrat: str, keywords: str) -> list[dict]:
        # motsCles matches with AND semantics between comma-joined terms (narrows results), so a
        # broad "développeur,python,java,..." search returns almost nothing combined. To get an OR
        # across keywords, one query is issued per term and results are merged by id — confirmed
        # empirically: a single term + natureContrat=E2,FS reliably returns real internship/
        # alternance postings, while joining several terms in one motsCles collapses to ~0 results.
        terms = [term.strip() for term in (keywords or "").split(",") if term.strip()] or [""]

        merged: dict[str, dict] = {}
        for term in terms:
            for job in self._search_one(token, limit, nature_contrat, term):
                job_id = job.get("id")
                if job_id is not None and job_id not in merged:
                    merged[job_id] = job
            if len(merged) >= limit:
                break

        return list(merged.values())[:limit]

    def _search_one(self, token: str, limit: int, nature_contrat: str, keyword: str) -> list[dict]:
        range_end = max(0, min(limit, 150) - 1)
        params = {"range": f"0-{range_end}", "sort": 1}
        if keyword:
            params["motsCles"] = keyword
        if nature_contrat:
            params["natureContrat"] = nature_contrat

        try:
            response = requests.get(
                SEARCH_URL,
                headers={"Authorization": f"Bearer {token}"},
                params=params,
                timeout=15,
            )
            if response.status_code == 204:
                return []
            if response.status_code not in (200, 206):
                response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise ImporterError(f"France Travail est indisponible : {exc}") from exc

        jobs = payload.get("resultats")
        if not isinstance(jobs, list):
            raise ImporterError("Réponse France Travail inattendue : champ « resultats » manquant.")
        return jobs

    def _normalize(self, job: dict) -> dict:
        description = clean_html_to_text(job.get("description") or "")
        lieu = job.get("lieuTravail") or {}
        entreprise = job.get("entreprise") or {}
        origine = job.get("origineOffre") or {}
        salaire = job.get("salaire") or {}
        competences = job.get("competences") or []
        contract_label = (
            f"{job.get('intitule') or ''} {job.get('typeContratLibelle') or ''} "
            f"{job.get('natureContrat') or ''}"
        )

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
                contract_label, is_alternance=bool(job.get("alternance"))
            ),
        }
