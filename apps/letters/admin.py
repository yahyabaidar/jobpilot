from django.contrib import admin

from .models import CoverLetter, InterviewPrep, TailoredCV


@admin.register(CoverLetter)
class CoverLetterAdmin(admin.ModelAdmin):
    list_display = ["user", "job_offer", "language", "created_at"]
    list_filter = ["language"]
    search_fields = ["user__email", "job_offer__title", "job_offer__company"]


@admin.register(TailoredCV)
class TailoredCVAdmin(admin.ModelAdmin):
    list_display = ["user", "job_offer", "created_at"]
    search_fields = ["user__email", "job_offer__title", "job_offer__company"]


@admin.register(InterviewPrep)
class InterviewPrepAdmin(admin.ModelAdmin):
    list_display = ["user", "job_offer", "created_at"]
    search_fields = ["user__email", "job_offer__title", "job_offer__company"]
