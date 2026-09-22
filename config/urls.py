from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("comptes/", include("apps.accounts.urls")),
    path("profil/", include("apps.profiles.urls")),
    path("offres/", include("apps.jobs.urls")),
    path("candidatures/", include("apps.applications.urls")),
    path("lettres/", include("apps.letters.urls")),
    path("", include("apps.core.urls")),
]
