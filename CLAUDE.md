# JobPilot — AI job search assistant

Portfolio project (GitHub + LinkedIn). A Django web app that:
1. parses a user's CV (PDF) with an LLM into a structured profile,
2. imports job offers (public APIs + manual paste),
3. scores each offer against the profile (score /100, matched & missing skills, advice),
4. generates tailored cover letters (FR/EN, PDF export),
5. tracks applications in a Kanban board + analytics dashboard.

The goal is a **clean, professional, deployed** project: readable code, tests, CI, good README.

## Stack
- Python 3.12, Django 5, PostgreSQL 16 (Docker Compose for local dev)
- Front: Django templates + **HTMX** + **Tailwind** (CDN in V1), Alpine.js only if really needed
- Charts: Chart.js · Drag & drop: SortableJS
- LLM: `openai` Python SDK against any **OpenAI-compatible** endpoint, configured by env vars
  `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` (works with Groq, Gemini, OpenAI…)
- Config: `django-environ` + `.env` (never commit `.env`; keep `.env.example` up to date)
- Tests: `pytest` + `pytest-django` · Lint/format: `ruff`
- Prod: `gunicorn` + `whitenoise`, deployed on Render (or Railway)

## Project layout
```
config/            settings (base.py, dev.py, prod.py), urls, wsgi/asgi
apps/
  accounts/        auth (signup/login/logout)
  profiles/        CV upload, parsing, skills
  jobs/            JobOffer model, importers, list/detail
  matching/        scoring (rule-based + LLM), Match model
  letters/         cover letter generation + PDF
  applications/    Kanban + dashboard
  core/            shared: base templates, LLM client (core/llm.py), utils
templates/         base.html, partials/, one folder per app
static/
tests/             mirrors apps/
```

## Conventions
- Code, identifiers, commits, docstrings: **English**. User-facing UI text: **French**.
- Business logic lives in `services.py` modules, not in views. Views stay thin.
- All LLM calls go through `apps/core/llm.py` (one place for client, retries, JSON parsing).
  LLM responses must be requested as JSON and validated before saving.
- In tests, **never call the real LLM** — mock `apps/core/llm.py`.
- HTMX partials live in `templates/<app>/partials/`.
- Type hints on services; small functions; no dead code.
- Commits: Conventional Commits (`feat:`, `fix:`, `chore:`, `test:`, `docs:`).

## Commands
```
docker compose up --build           # run app + db
docker compose exec web python manage.py migrate
docker compose exec web pytest
ruff check . && ruff format .
```

## Working rules for Claude Code
- We build the project **one step at a time**. Only do what the current step asks; do not
  start the next step.
- Before coding a step, briefly state the plan (files to create/modify).
- At the end of a step: run migrations, `ruff`, and the tests; fix anything failing; then give
  me a short summary + **a manual test checklist** so I can validate in the browser.
- Do not commit automatically: propose the commit message and wait for my validation.
