import io
from unittest.mock import patch

import pytest
from django.core.files.base import ContentFile
from pdf_utils import build_empty_pdf, build_minimal_pdf

from apps.accounts.models import User
from apps.core.llm import LLMError
from apps.profiles.models import CVDocument, Profile, Skill
from apps.profiles.services import CVParsingError, extract_text, parse_cv, save_profile

CV_LLM_RESPONSE = {
    "titre": "Développeuse Python",
    "resume": "5 ans d'expérience en développement web.",
    "ville": "Lyon",
    "annees_experience": 5,
    "competences": [
        {"nom": "Python", "categorie": "technique"},
        {"nom": "python", "categorie": "technique"},
        {"nom": "Docker", "categorie": "outil"},
        {"nom": "Anglais", "categorie": "langue"},
    ],
    "experiences": [
        {
            "poste": "Développeuse backend",
            "entreprise": "Acme",
            "date_debut": "2020",
            "date_fin": "2024",
            "description": "API Django.",
        }
    ],
    "formations": [
        {"diplome": "Master Informatique", "etablissement": "Université de Lyon", "annee": "2019"}
    ],
}


def test_extract_text_returns_content_from_pdf():
    pdf_bytes = build_minimal_pdf("Bonjour, ceci est un CV de test.")

    text = extract_text(io.BytesIO(pdf_bytes))

    assert "Bonjour, ceci est un CV de test." in text


def test_extract_text_raises_on_empty_pdf():
    pdf_bytes = build_empty_pdf()

    with pytest.raises(CVParsingError):
        extract_text(io.BytesIO(pdf_bytes))


@patch("apps.profiles.services.complete_json")
def test_parse_cv_uses_mocked_llm_client(mock_complete_json):
    mock_complete_json.return_value = CV_LLM_RESPONSE

    data = parse_cv("texte de CV quelconque")

    assert data["titre"] == "Développeuse Python"
    assert data["ville"] == "Lyon"
    assert len(data["competences"]) == 4
    mock_complete_json.assert_called_once()


@patch("apps.profiles.services.complete_json")
def test_parse_cv_propagates_llm_error(mock_complete_json):
    mock_complete_json.side_effect = LLMError("échec du modèle")

    with pytest.raises(LLMError):
        parse_cv("texte de CV quelconque")


@pytest.mark.django_db
def test_save_profile_creates_skills_experiences_and_educations():
    user = User.objects.create_user(email="cv@example.com", password="un-mot-de-passe-solide")

    profile = save_profile(user, CV_LLM_RESPONSE)

    assert profile.title == "Développeuse Python"
    assert profile.years_of_experience == 5
    assert profile.skills.count() == 3  # "Python" and "python" are deduplicated
    assert profile.experiences.count() == 1
    assert profile.educations.count() == 1
    assert set(profile.skills.values_list("normalized_name", flat=True)) == {
        "python",
        "docker",
        "anglais",
    }


@pytest.mark.django_db
def test_save_profile_replaces_existing_profile():
    user = User.objects.create_user(email="cv@example.com", password="un-mot-de-passe-solide")
    save_profile(user, CV_LLM_RESPONSE)

    new_data = {
        **CV_LLM_RESPONSE,
        "titre": "Lead Developer",
        "competences": [{"nom": "Go", "categorie": "technique"}],
    }
    profile = save_profile(user, new_data)

    assert Profile.objects.filter(user=user).count() == 1
    assert profile.title == "Lead Developer"
    assert profile.skills.count() == 1
    assert Skill.objects.filter(profile=profile, normalized_name="go").exists()


@pytest.mark.django_db
def test_user_cannot_access_another_users_cv(client):
    owner = User.objects.create_user(email="owner@example.com", password="un-mot-de-passe-solide")
    other = User.objects.create_user(email="other@example.com", password="un-mot-de-passe-solide")
    cv_document = CVDocument.objects.create(user=owner, original_name="cv.pdf")
    cv_document.file.save("cv.pdf", ContentFile(build_minimal_pdf("CV")), save=True)

    client.login(email=other.email, password="un-mot-de-passe-solide")
    response = client.post(f"/profil/cv/{cv_document.pk}/analyser/")

    assert response.status_code == 404
