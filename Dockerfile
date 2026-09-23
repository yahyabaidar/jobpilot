# syntax=docker/dockerfile:1

# ---- builder: install dependencies into a venv, kept separate from the runtime layer ----
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# ---- runtime: slim image, non-root user, static files pre-collected ----
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=config.settings.prod

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY . .

# Placeholder values so Django can load settings for collectstatic at build time — it never
# touches the database. The real platform (Render, ...) MUST provide its own SECRET_KEY and
# DATABASE_URL at container runtime, which take precedence over these; see docs/DEPLOIEMENT.md.
RUN SECRET_KEY=build-only-placeholder \
    DATABASE_URL=postgres://user:pass@localhost:5432/placeholder \
    python manage.py collectstatic --noinput

COPY --chmod=755 docker-entrypoint.sh /docker-entrypoint.sh

RUN addgroup --system app \
    && adduser --system --group app \
    && mkdir -p /app/media \
    && chown -R app:app /app

USER app

EXPOSE 8000

ENTRYPOINT ["/docker-entrypoint.sh"]
