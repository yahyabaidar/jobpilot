from django.urls import path

from . import views

app_name = "matching"

urlpatterns = [
    path("offres/<int:pk>/analyser/demarrer/", views.start_analyze, name="start_analyze"),
    path("offres/<int:pk>/analyser/executer/", views.run_analyze, name="run_analyze"),
    path("lot/demarrer/", views.start_batch, name="start_batch"),
    path("lot/etape/", views.batch_step, name="batch_step"),
]
