from django import forms
from django.core.exceptions import ValidationError

from .models import CVDocument

MAX_CV_SIZE_BYTES = 5 * 1024 * 1024

FILE_INPUT_CLASSES = (
    "block w-full text-sm text-slate-600 dark:text-slate-300 "
    "file:mr-4 file:rounded-lg file:border-0 file:bg-primary-50 file:px-4 file:py-2.5 "
    "file:text-sm file:font-semibold file:text-primary-700 hover:file:bg-primary-100 "
    "dark:file:bg-primary-950 dark:file:text-primary-300"
)


class CVUploadForm(forms.ModelForm):
    file = forms.FileField(
        label="Fichier CV (PDF, 5 Mo maximum)",
        widget=forms.ClearableFileInput(attrs={"class": FILE_INPUT_CLASSES, "accept": ".pdf"}),
    )

    class Meta:
        model = CVDocument
        fields = ["file"]

    def clean_file(self):
        file = self.cleaned_data["file"]
        if not file.name.lower().endswith(".pdf"):
            raise ValidationError("Le fichier doit être un PDF.")
        if file.size > MAX_CV_SIZE_BYTES:
            raise ValidationError("Le fichier ne doit pas dépasser 5 Mo.")
        return file
