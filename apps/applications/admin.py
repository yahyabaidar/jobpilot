from django.contrib import admin

from .models import Application, StatusChange


class StatusChangeInline(admin.TabularInline):
    model = StatusChange
    extra = 0


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ["user", "job_offer", "status", "applied_at", "status_changed_at"]
    list_filter = ["status"]
    search_fields = ["user__email", "job_offer__title", "job_offer__company"]
    inlines = [StatusChangeInline]
