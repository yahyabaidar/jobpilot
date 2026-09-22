from django.conf import settings
from django.db import models


class Application(models.Model):
    class Status(models.TextChoices):
        TO_APPLY = "to_apply", "À postuler"
        SENT = "sent", "Envoyée"
        INTERVIEW = "interview", "Entretien"
        OFFER = "offer", "Offre reçue"
        REJECTED = "rejected", "Refus"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="applications"
    )
    job_offer = models.ForeignKey(
        "jobs.JobOffer", on_delete=models.CASCADE, related_name="applications"
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SENT)
    applied_at = models.DateField(auto_now_add=True)
    status_changed_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "job_offer"], name="unique_application")
        ]
        ordering = ["-applied_at"]

    def __str__(self) -> str:
        return f"{self.user} → {self.job_offer}"


class StatusChange(models.Model):
    application = models.ForeignKey(
        Application, on_delete=models.CASCADE, related_name="status_changes"
    )
    status = models.CharField(max_length=20, choices=Application.Status.choices)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["changed_at"]

    def __str__(self) -> str:
        return f"{self.application} → {self.status} ({self.changed_at:%Y-%m-%d})"
