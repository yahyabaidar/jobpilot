from django.conf import settings
from django.db import models


class Application(models.Model):
    class Status(models.TextChoices):
        SENT = "sent", "Envoyée"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="applications"
    )
    job_offer = models.ForeignKey(
        "jobs.JobOffer", on_delete=models.CASCADE, related_name="applications"
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SENT)
    applied_at = models.DateField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "job_offer"], name="unique_application")
        ]
        ordering = ["-applied_at"]

    def __str__(self) -> str:
        return f"{self.user} → {self.job_offer}"
