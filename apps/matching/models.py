from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

SCORE_VALIDATORS = [MinValueValidator(0), MaxValueValidator(100)]


class Match(models.Model):
    class Legitimacy(models.TextChoices):
        RELIABLE = "reliable", "Fiable"
        TO_VERIFY = "to_verify", "À vérifier"
        SUSPICIOUS = "suspicious", "Suspect"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="matches"
    )
    job_offer = models.ForeignKey("jobs.JobOffer", on_delete=models.CASCADE, related_name="matches")

    score = models.PositiveSmallIntegerField(validators=SCORE_VALIDATORS)
    skills_score = models.PositiveSmallIntegerField(validators=SCORE_VALIDATORS)
    experience_score = models.PositiveSmallIntegerField(validators=SCORE_VALIDATORS)
    education_score = models.PositiveSmallIntegerField(validators=SCORE_VALIDATORS)
    location_score = models.PositiveSmallIntegerField(validators=SCORE_VALIDATORS)
    language_score = models.PositiveSmallIntegerField(validators=SCORE_VALIDATORS)

    matched_skills = models.JSONField(default=list, blank=True)
    missing_skills = models.JSONField(default=list, blank=True)
    advice = models.TextField(blank=True)

    legitimacy = models.CharField(
        max_length=20, choices=Legitimacy.choices, default=Legitimacy.TO_VERIFY
    )
    legitimacy_reasons = models.JSONField(default=list, blank=True)

    administrative_notes = models.JSONField(
        "admissibilité administrative", default=list, blank=True
    )

    llm_model = models.CharField(max_length=100, blank=True)
    analyzed_at = models.DateTimeField(auto_now=True)
    duration_seconds = models.FloatField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "job_offer"], name="unique_match_per_user_offer"
            )
        ]

    def __str__(self) -> str:
        return f"{self.user} × {self.job_offer} = {self.score}"
