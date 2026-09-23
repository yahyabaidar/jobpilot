import unicodedata

from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models


def normalize_skill_name(name: str) -> str:
    stripped = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    return stripped.strip().lower()


def cv_upload_path(instance: "CVDocument", filename: str) -> str:
    return f"cv/{instance.user_id}/{filename}"


class CVDocument(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "En attente"
        PROCESSING = "processing", "En cours"
        DONE = "done", "Terminé"
        ERROR = "error", "Erreur"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cv_documents"
    )
    file = models.FileField(upload_to=cv_upload_path, validators=[FileExtensionValidator(["pdf"])])
    original_name = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    error_message = models.TextField(blank=True)
    extracted_text = models.TextField(blank=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self) -> str:
        return f"{self.original_name} ({self.user})"


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    title = models.CharField("titre", max_length=255, blank=True)
    summary = models.TextField("résumé", blank=True)
    years_of_experience = models.PositiveIntegerField("années d'expérience", null=True, blank=True)
    city = models.CharField("ville", max_length=255, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Profil de {self.user}"


class Skill(models.Model):
    class Category(models.TextChoices):
        TECHNICAL = "technical", "Technique"
        TOOL = "tool", "Outil"
        LANGUAGE = "language", "Langue"
        SOFT_SKILL = "soft_skill", "Savoir-être"

    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="skills")
    normalized_name = models.CharField(max_length=100)
    display_name = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=Category.choices)

    class Meta:
        ordering = ["category", "display_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["profile", "normalized_name"], name="unique_skill_per_profile"
            )
        ]

    def __str__(self) -> str:
        return self.display_name

    def save(self, *args, **kwargs):
        if not self.normalized_name:
            self.normalized_name = normalize_skill_name(self.display_name)
        super().save(*args, **kwargs)


class Experience(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="experiences")
    title = models.CharField("poste", max_length=255)
    company = models.CharField("entreprise", max_length=255, blank=True)
    start_date = models.CharField("date de début", max_length=50, blank=True)
    end_date = models.CharField("date de fin", max_length=50, blank=True)
    description = models.TextField("description", blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self) -> str:
        return f"{self.title} — {self.company}"


def _default_contract_types() -> list[str]:
    return ["stage"]


def _default_countries() -> list[str]:
    return ["France"]


class SearchPreference(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="search_preference"
    )
    contract_types = models.JSONField("types de contrat visés", default=_default_contract_types)
    countries = models.JSONField("pays visés", default=_default_countries)
    cities = models.JSONField("villes visées", default=list, blank=True)
    remote_ok = models.BooleanField("télétravail accepté", default=True)
    desired_duration_months = models.PositiveSmallIntegerField(
        "durée souhaitée (mois)", null=True, blank=True
    )
    desired_start_date = models.CharField("date de début souhaitée", max_length=100, blank=True)
    languages = models.JSONField("langues", default=list, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Préférences de {self.user}"


class Education(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="educations")
    degree = models.CharField("diplôme", max_length=255)
    institution = models.CharField("établissement", max_length=255, blank=True)
    year = models.CharField("année", max_length=20, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self) -> str:
        return f"{self.degree} — {self.institution}"
