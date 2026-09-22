from django.urls import path

from . import views

app_name = "jobs"

urlpatterns = [
    path("", views.index, name="index"),
    path("importer/", views.start_import, name="start_import"),
    path("importer/executer/", views.run_import, name="run_import"),
    path("verifier-url/", views.check_url, name="check_url"),
    path("ajouter/", views.manual_create, name="manual_create"),
    path("ajouter/analyser/", views.manual_analyze, name="manual_analyze"),
    path("ajouter/enregistrer/", views.manual_save, name="manual_save"),
    path("<int:pk>/", views.detail, name="detail"),
    path("<int:pk>/postuler/", views.apply, name="apply"),
]
