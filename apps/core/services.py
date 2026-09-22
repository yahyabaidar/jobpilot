from django.db import connection
from django.db.models import Case, Count, IntegerField, Value, When
from django.db.models.functions import TruncWeek

from apps.applications.models import Application
from apps.jobs.models import JobOffer
from apps.matching.models import Match
from apps.profiles.models import Profile

SENT_OR_LATER_STATUSES = [
    Application.Status.SENT,
    Application.Status.INTERVIEW,
    Application.Status.OFFER,
    Application.Status.REJECTED,
]
RESPONSE_STATUSES = [Application.Status.INTERVIEW, Application.Status.OFFER]

SKILL_FREQUENCY_LIMIT = 8


def get_dashboard_stats(user) -> dict:
    has_profile = Profile.objects.filter(user=user).exists()
    offer_count = JobOffer.objects.count()
    analyzed_count = Match.objects.filter(user=user).count()

    status_rows = Application.objects.filter(user=user).values("status").annotate(n=Count("id"))
    status_counts = {row["status"]: row["n"] for row in status_rows}

    sent_or_later = sum(status_counts.get(s, 0) for s in SENT_OR_LATER_STATUSES)
    responses = sum(status_counts.get(s, 0) for s in RESPONSE_STATUSES)
    response_rate = round(responses / sent_or_later * 100) if sent_or_later else 0

    return {
        "has_profile": has_profile,
        "offer_count": offer_count,
        "analyzed_count": analyzed_count,
        "status_counts": status_counts,
        "response_rate": response_rate,
    }


def _skill_frequency(sql: str, params: list, limit: int) -> list[dict]:
    with connection.cursor() as cursor:
        cursor.execute(sql, [*params, limit])
        rows = cursor.fetchall()
    return [{"skill": skill, "count": count} for skill, count in rows]


def get_missing_skills_stats(user, limit: int = SKILL_FREQUENCY_LIMIT) -> list[dict]:
    sql = """
        SELECT MIN(skill) AS skill, COUNT(*) AS offer_count
        FROM matching_match, jsonb_array_elements_text(missing_skills) AS skill
        WHERE user_id = %s
        GROUP BY LOWER(skill)
        ORDER BY offer_count DESC, skill ASC
        LIMIT %s
    """
    return _skill_frequency(sql, [user.id], limit)


def get_market_skills_stats(limit: int = SKILL_FREQUENCY_LIMIT) -> list[dict]:
    sql = """
        SELECT MIN(skill) AS skill, COUNT(*) AS offer_count
        FROM jobs_joboffer, jsonb_array_elements_text(tags) AS skill
        GROUP BY LOWER(skill)
        ORDER BY offer_count DESC, skill ASC
        LIMIT %s
    """
    return _skill_frequency(sql, [], limit)


def get_score_distribution(user) -> dict:
    bucket_expr = Case(
        *[When(score__gte=i * 10, score__lt=(i + 1) * 10, then=Value(i)) for i in range(9)],
        default=Value(9),
        output_field=IntegerField(),
    )
    rows = (
        Match.objects.filter(user=user)
        .annotate(bucket=bucket_expr)
        .values("bucket")
        .annotate(n=Count("id"))
    )
    counts_by_bucket = {row["bucket"]: row["n"] for row in rows}
    counts = [counts_by_bucket.get(i, 0) for i in range(10)]
    labels = [f"{i * 10}-{i * 10 + 9}" for i in range(9)] + ["90-100"]
    return {"labels": labels, "counts": counts}


def get_applications_over_time(user) -> dict:
    rows = (
        Application.objects.filter(user=user)
        .annotate(week=TruncWeek("applied_at"))
        .values("week")
        .annotate(n=Count("id"))
        .order_by("week")
    )
    labels = []
    counts = []
    cumulative = 0
    for row in rows:
        cumulative += row["n"]
        labels.append(row["week"].strftime("%d %b"))
        counts.append(cumulative)
    return {"labels": labels, "counts": counts}
