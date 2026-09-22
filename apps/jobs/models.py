from django.conf import settings
from django.db import models


class JobOffer(models.Model):
    class Source(models.TextChoices):
        REMOTIVE = "remotive", "Remotive"
        ARBEITNOW = "arbeitnow", "Arbeitnow"
        MANUAL = "manuel", "Manuel"

    title = models.CharField("titre", max_length=255)
    company = models.CharField("entreprise", max_length=255, blank=True)
    location = models.CharField("lieu", max_length=255, blank=True)
    remote = models.BooleanField("télétravail", default=False)
    description = models.TextField("description", blank=True)
    url = models.URLField("URL", max_length=500, blank=True)
    source = models.CharField(max_length=20, choices=Source.choices)
    external_id = models.CharField(max_length=255)
    published_at = models.DateTimeField("date de publication", null=True, blank=True)
    imported_at = models.DateTimeField("date d'import", auto_now_add=True)
    tags = models.JSONField(default=list, blank=True)
    salary = models.CharField("salaire", max_length=255, blank=True)
    language = models.CharField("langue", max_length=10, blank=True)
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="job_offers",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["source", "external_id"], name="unique_source_external_id"
            )
        ]
        indexes = [
            models.Index(fields=["published_at"]),
            models.Index(fields=["source"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} — {self.company}"
