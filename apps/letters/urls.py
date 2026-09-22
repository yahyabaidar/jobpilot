from django.urls import path

from . import views

app_name = "letters"

urlpatterns = [
    path("", views.index, name="index"),
    path("offres/<int:pk>/lettre/demarrer/", views.start_letter, name="start_letter"),
    path("offres/<int:pk>/lettre/executer/", views.run_letter, name="run_letter"),
    path("lettre/<int:pk>/enregistrer/", views.save_letter, name="save_letter"),
    path("lettre/<int:pk>/pdf/", views.letter_pdf, name="letter_pdf"),
    path("offres/<int:pk>/cv/demarrer/", views.start_cv, name="start_cv"),
    path("offres/<int:pk>/cv/executer/", views.run_cv, name="run_cv"),
    path("cv/<int:pk>/enregistrer/", views.save_cv, name="save_cv"),
    path("cv/<int:pk>/pdf/", views.cv_pdf, name="cv_pdf"),
    path("offres/<int:pk>/entretien/demarrer/", views.start_interview, name="start_interview"),
    path("offres/<int:pk>/entretien/executer/", views.run_interview, name="run_interview"),
    path("entretien/<int:pk>/enregistrer/", views.save_interview, name="save_interview"),
]
