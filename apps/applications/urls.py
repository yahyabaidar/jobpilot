from django.urls import path

from . import views

app_name = "applications"

urlpatterns = [
    path("", views.index, name="index"),
    path("deplacer/", views.move, name="move"),
    path("<int:pk>/", views.detail, name="detail"),
    path("<int:pk>/notes/", views.save_notes, name="save_notes"),
    path("<int:pk>/supprimer/", views.delete, name="delete"),
]
