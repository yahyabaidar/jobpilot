from django.contrib import admin

from .models import JobOffer


@admin.register(JobOffer)
class JobOfferAdmin(admin.ModelAdmin):
    list_display = ["title", "company", "source", "remote", "published_at", "imported_at"]
    list_filter = ["source", "remote"]
    search_fields = ["title", "company", "location"]
