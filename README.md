# JobPilot

Assistant IA de recherche d'emploi : analyse de CV, matching d'offres, génération de lettres de motivation et suivi des candidatures.

## Lancer le projet

```bash
cp .env.example .env
docker compose up --build
docker compose exec web python manage.py migrate
```

L'application est disponible sur http://localhost:8000

## Tests et qualité

```bash
docker compose exec web pytest
docker compose exec web ruff check .
```
