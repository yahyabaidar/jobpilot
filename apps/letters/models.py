from django.conf import settings
from django.db import models


class CoverLetter(models.Model):
    class Language(models.TextChoices):
        FR = "fr", "Français"
        EN = "en", "English"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cover_letters"
    )
    job_offer = models.ForeignKey(
        "jobs.JobOffer", on_delete=models.CASCADE, related_name="cover_letters"
    )
    language = models.CharField(max_length=5, choices=Language.choices, default=Language.FR)
    content = models.TextField(blank=True)
    llm_model = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Lettre pour {self.job_offer} ({self.user})"


class TailoredCV(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tailored_cvs"
    )
    job_offer = models.ForeignKey(
        "jobs.JobOffer", on_delete=models.CASCADE, related_name="tailored_cvs"
    )
    content = models.JSONField(default=dict, blank=True)
    llm_model = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"CV adapté pour {self.job_offer} ({self.user})"


class InterviewPrep(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="interview_preps"
    )
    job_offer = models.ForeignKey(
        "jobs.JobOffer", on_delete=models.CASCADE, related_name="interview_preps"
    )
    questions = models.JSONField(default=list, blank=True)
    llm_model = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Préparation d'entretien pour {self.job_offer} ({self.user})"
