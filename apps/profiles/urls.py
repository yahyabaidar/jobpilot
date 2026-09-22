from django.urls import path

from . import views

app_name = "profiles"

urlpatterns = [
    path("", views.index, name="index"),
    path("cv/envoyer/", views.upload_cv, name="upload"),
    path("cv/<int:pk>/reanalyser/", views.reanalyze, name="reanalyze"),
    path("cv/<int:pk>/analyser/", views.analyze, name="analyze"),
    path("modifier/", views.update_profile, name="update"),
    path("competences/ajouter/", views.add_skill, name="add_skill"),
    path("competences/<int:pk>/supprimer/", views.delete_skill, name="delete_skill"),
]
