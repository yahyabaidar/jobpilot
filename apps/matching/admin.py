from django.contrib import admin

from .models import Match


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ["user", "job_offer", "score", "legitimacy", "analyzed_at"]
    list_filter = ["legitimacy"]
    search_fields = ["user__email", "job_offer__title", "job_offer__company"]
