from django.contrib import admin

from .models import Application


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ["user", "job_offer", "status", "applied_at"]
    list_filter = ["status"]
    search_fields = ["user__email", "job_offer__title", "job_offer__company"]
