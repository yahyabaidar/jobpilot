from django.core.management.base import BaseCommand

from apps.jobs.importers import IMPORTERS, ImporterError
from apps.jobs.services import upsert_job_offer


class Command(BaseCommand):
    help = (
        "Importe des offres d'emploi depuis les API publiques (Remotive, Arbeitnow, "
        "France Travail)."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument("--source", default="all", choices=[*IMPORTERS.keys(), "all"])
        parser.add_argument("--limit", type=int, default=50)
        parser.add_argument(
            "--contract-type",
            default=None,
            help=(
                "France Travail uniquement : codes natureContrat à cibler (ex. E2,FS pour "
                "apprentissage/professionnalisation, les codes les plus proches d'un stage). "
                "Par défaut, orienté stage/alternance."
            ),
        )
        parser.add_argument(
            "--keywords",
            default=None,
            help=(
                "France Travail uniquement : mots-clés de recherche (motsCles), "
                "séparés par des virgules."
            ),
        )

    def handle(self, *args, **options) -> None:
        source = options["source"]
        limit = options["limit"]
        fetch_kwargs = {
            "contract_type": options["contract_type"],
            "keywords": options["keywords"],
        }
        sources = list(IMPORTERS.keys()) if source == "all" else [source]

        for source_name in sources:
            self._import_source(source_name, limit, fetch_kwargs)

    def _import_source(self, source_name: str, limit: int, fetch_kwargs: dict) -> None:
        importer = IMPORTERS[source_name]()

        try:
            jobs = importer.fetch(limit=limit, **fetch_kwargs)
        except ImporterError as exc:
            self.stderr.write(self.style.ERROR(f"[{source_name}] {exc}"))
            return
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f"[{source_name}] Erreur inattendue : {exc}"))
            return

        created = updated = ignored = 0
        for data in jobs:
            if not data.get("title") or not data.get("url"):
                ignored += 1
                continue
            _, was_created = upsert_job_offer(data)
            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"[{source_name}] {len(jobs)} reçues : {created} créées, "
                f"{updated} mises à jour, {ignored} ignorées"
            )
        )
