# Architecture

## App responsibilities

| App | Responsibility |
|---|---|
| `apps/accounts` | Custom `User` model (email as username, no username field), signup/login/logout. |
| `apps/core` | Landing page, dashboard (aggregate stats + charts), the shared LLM client (`llm.py`), dashboard aggregate queries (`services.py`), `/health/`. |
| `apps/profiles` | CV upload + AI parsing into a structured `Profile` (skills, experience, education), and `SearchPreference` (contract types, countries, desired start date — used both to filter the job list and to inform the AI matching prompt). |
| `apps/jobs` | `JobOffer` model, one importer per source (`apps/jobs/importers/`) behind a common `fetch(limit, **kwargs) -> list[dict]` interface, the manual paste-and-extract flow, search/filtering, and the "Postuler" action. |
| `apps/matching` | `Match`: the 5-axis compatibility score, legitimacy check, and administrative-eligibility notes for one (user, offer) pair. One LLM call per analysis; a no-AI keyword overlap pass grounds the prompt first. |
| `apps/letters` | Cover letter / tailored CV / interview prep generation (one LLM call each, from the same profile+offer context) and their PDF export. |
| `apps/applications` | The Kanban board: `Application` (status, position, notes) and `StatusChange` history, drag-and-drop persistence. |

Business logic lives in each app's `services.py`; views stay thin (fetch, call a service, render).
All LLM calls go through `apps/core/llm.py`, which is the only place that knows about the
OpenAI-compatible client, retries a malformed JSON response once, and raises `LLMError` with a
message safe to show a user.

## Request flow: analyzing one offer

This is the path from clicking "Analyser cette offre" on an offer detail page to the score
appearing, without a full page reload:

```mermaid
sequenceDiagram
    participant Browser
    participant Django as Django view (apps/matching)
    participant Service as apps/matching/services.py
    participant DB as PostgreSQL
    participant LLM as Groq API

    Browser->>Django: POST /analyse/offres/<id>/analyser/demarrer/
    Django-->>Browser: loading spinner partial (hx-trigger="load")
    Browser->>Django: POST /analyse/offres/<id>/analyser/executer/
    Django->>Service: analyze_match(user, job_offer)
    Service->>DB: fetch Profile + skills/experience/education
    Service->>Service: compute_skill_overlap() — no-AI quick pass, grounds the prompt
    Service->>LLM: complete_json(prompt, system, schema_hint)
    LLM-->>Service: JSON — 5 axis scores, matched/missing skills, advice, legitimacy, admin notes
    Service->>Service: compute_global_score() — weighted average, named constants
    Service->>DB: Match.objects.update_or_create(user, job_offer)
    Django-->>Browser: score panel partial (radar chart, badges, advice)
```

Reanalysis reuses the exact same endpoint — `update_or_create` means the row is replaced, never
duplicated, and the cached `Match` is shown on every subsequent page load with no further AI call
until the user explicitly asks to reanalyze.

## Data model

```mermaid
erDiagram
    User ||--o| Profile : has
    User ||--o| SearchPreference : has
    User ||--o{ CVDocument : uploads
    Profile ||--o{ Skill : has
    Profile ||--o{ Experience : has
    Profile ||--o{ Education : has

    User ||--o{ JobOffer : "adds manually (added_by)"
    JobOffer ||--o{ Match : "scored per user"
    User ||--o{ Match : analyzes

    User ||--o{ Application : tracks
    JobOffer ||--o{ Application : "tracked as"
    Application ||--o{ StatusChange : history

    User ||--o{ CoverLetter : generates
    JobOffer ||--o{ CoverLetter : "for offer"
    User ||--o{ TailoredCV : generates
    JobOffer ||--o{ TailoredCV : "for offer"
    User ||--o{ InterviewPrep : generates
    JobOffer ||--o{ InterviewPrep : "for offer"

    JobOffer {
        string title
        string company
        string contract_type
        string source
        string external_id
        json tags
    }
    Match {
        int score
        int skills_score
        int experience_score
        int education_score
        int location_score
        int language_score
        json matched_skills
        json missing_skills
        json administrative_notes
        string legitimacy
    }
    Application {
        string status
        int position
        text notes
        datetime status_changed_at
    }
```

Notes on a few deliberate choices:

- **`Match` is unique per `(user, job_offer)`** — reanalyzing updates the row instead of growing
  a history, since only the latest compatibility score is ever meaningful.
- **`CoverLetter`, `TailoredCV`, `InterviewPrep` are *not* unique per offer** — every "Régénérer"
  click creates a new row, ordered newest-first, so past versions aren't lost.
- **`Application` carries its own `position`** (drag-and-drop order within a Kanban column) and
  `status_changed_at`, updated only on an actual status change — `StatusChange` rows are the
  append-only audit log used for the "candidatures par statut" dashboard stats.
