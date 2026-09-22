from django.core.management.base import BaseCommand

from apps.jobs.importers import IMPORTERS, ImporterError
from apps.jobs.services import upsert_job_offer


class Command(BaseCommand):
    help = "Importe des offres d'emploi depuis les API publiques (Remotive, Arbeitnow)."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--source", default="all", choices=[*IMPORTERS.keys(), "all"])
        parser.add_argument("--limit", type=int, default=50)

    def handle(self, *args, **options) -> None:
        source = options["source"]
        limit = options["limit"]
        sources = list(IMPORTERS.keys()) if source == "all" else [source]

        for source_name in sources:
            self._import_source(source_name, limit)

    def _import_source(self, source_name: str, limit: int) -> None:
        importer = IMPORTERS[source_name]()

        try:
            jobs = importer.fetch(limit=limit)
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
