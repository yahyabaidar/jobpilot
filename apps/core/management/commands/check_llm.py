from django.conf import settings
from django.core.management.base import BaseCommand

from apps.core.llm import get_client


class Command(BaseCommand):
    help = "Vérifie la configuration LLM en effectuant un appel réel à l'API."

    def handle(self, *args, **options) -> None:
        client = get_client()

        self.stdout.write(f"Base URL : {settings.LLM_BASE_URL}")
        self.stdout.write(f"Modèle   : {settings.LLM_MODEL}")

        try:
            response = client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[{"role": "user", "content": "Réponds uniquement par: OK"}],
                timeout=30,
            )
        except Exception as exc:
            self.stderr.write(
                self.style.ERROR(f"Échec de l'appel au modèle « {settings.LLM_MODEL} » : {exc}")
            )
            self._list_available_models(client)
            return

        content = response.choices[0].message.content
        self.stdout.write(self.style.SUCCESS(f"Réponse du modèle : {content!r}"))
        usage = response.usage
        if usage is not None:
            self.stdout.write(
                f"Tokens utilisés : {usage.prompt_tokens} (prompt) + "
                f"{usage.completion_tokens} (réponse) = {usage.total_tokens}"
            )

    def _list_available_models(self, client) -> None:
        self.stdout.write("Modèles disponibles sur ce compte :")
        try:
            models = client.models.list()
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f"Impossible de lister les modèles : {exc}"))
            return

        for model in sorted(models.data, key=lambda m: m.id):
            self.stdout.write(f"  - {model.id}")
