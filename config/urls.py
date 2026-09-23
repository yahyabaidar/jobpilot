from django.contrib import admin
from django.urls import include, path

from apps.core.views import health

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health, name="health"),
    path("comptes/", include("apps.accounts.urls")),
    path("profil/", include("apps.profiles.urls")),
    path("offres/", include("apps.jobs.urls")),
    path("analyse/", include("apps.matching.urls")),
    path("candidatures/", include("apps.applications.urls")),
    path("lettres/", include("apps.letters.urls")),
    path("", include("apps.core.urls")),
]
