from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.applications.models import Application
from apps.applications.services import create_or_get_application, move_application
from apps.jobs.models import JobOffer
from apps.letters.models import CoverLetter, InterviewPrep, TailoredCV
from apps.matching.models import Match
from apps.profiles.models import Education, Experience, Profile, SearchPreference, Skill

DEMO_EMAIL = "demo@jobpilot.dev"
DEMO_PASSWORD = "Demo1234!"

SKILLS = [
    ("Python", "technical"),
    ("Django", "technical"),
    ("React", "technical"),
    ("SQL", "technical"),
    ("Docker", "tool"),
    ("Git", "tool"),
    ("Anglais", "language"),
    ("Travail en équipe", "soft_skill"),
]

# (title, company, location, contract_type, tags, description, duration_months, start_date)
OFFERS = [
    (
        "Stage Développeur Full-Stack Python/React",
        "TechCorp",
        "Paris, France",
        "stage",
        ["Python", "Django", "React", "SQL"],
        "Stage de fin d'études de 6 mois au sein d'une équipe produit. "
        "Convention de stage obligatoire.",
        6,
        "Mars 2027",
    ),
    (
        "Alternance Data Analyst",
        "DataFlow",
        "Lyon, France",
        "alternance",
        ["SQL", "Python", "Power BI"],
        "Alternance de 12 mois, analyse de données commerciales et tableaux de bord.",
        12,
        "Septembre 2027",
    ),
    (
        "Stage Ingénieur DevOps",
        "CloudNine",
        "Toulouse, France",
        "stage",
        ["Docker", "Kubernetes", "AWS", "Linux"],
        "Stage de 5 mois sur l'automatisation du déploiement continu.",
        5,
        "Avril 2027",
    ),
    (
        "CDI Développeur Backend Java",
        "BankSoft",
        "Paris, France",
        "cdi",
        ["Java", "Spring", "SQL"],
        "8 ans d'expérience minimum en développement backend Java requis. Poste senior.",
        None,
        "",
    ),
    (
        "Stage Machine Learning Engineer",
        "AI Labs",
        "Grenoble, France",
        "stage",
        ["Python", "Machine Learning", "SQL"],
        "Stage de fin d'études sur la détection d'anomalies. Niveau Bac+5 requis.",
        6,
        "Février 2027",
    ),
    (
        "Alternance Développeur Mobile Flutter",
        "MobileFirst",
        "Nantes, France",
        "alternance",
        ["Flutter", "Dart", "Git"],
        "Alternance de 24 mois, développement d'une application mobile grand public.",
        24,
        "Octobre 2027",
    ),
    (
        "CDD Support Technique Informatique",
        "HelpDesk Pro",
        "Marseille, France",
        "cdd",
        ["Windows", "Réseau", "Support"],
        "Contrat de 6 mois, support niveau 1 et 2 pour une clientèle professionnelle.",
        6,
        "Dès que possible",
    ),
    (
        "Technicien / Technicienne de hot line en informatique (H/F)",
        "MANPOWER FRANCE",
        "Lyon, France",
        "interim",
        ["Support", "Réseau"],
        "Mission intérimaire de 3 mois au sein d'un service support informatique.",
        3,
        "",
    ),
    (
        "Stage Ingénieur Cybersécurité",
        "SecureIT",
        "Rennes, France",
        "stage",
        ["Sécurité", "Linux", "Python"],
        "Stage de fin d'études, audit de sécurité et durcissement d'infrastructures. "
        "Nationalité française requise pour habilitation.",
        6,
        "Mars 2027",
    ),
    (
        "Freelance Développeur WordPress",
        "Studio Web",
        "Télétravail",
        "freelance",
        ["WordPress", "PHP", "CSS"],
        "Mission ponctuelle de refonte de site vitrine, à distance.",
        None,
        "",
    ),
    (
        "Alternance Ingénieur Cloud AWS",
        "CloudNine",
        "Bordeaux, France",
        "alternance",
        ["AWS", "Docker", "Python"],
        "Alternance de 12 mois sur la migration cloud d'applications internes.",
        12,
        "Septembre 2027",
    ),
    (
        "Stage Data Engineer",
        "BigData Solutions",
        "Paris, France",
        "stage",
        ["Python", "SQL", "Docker"],
        "Stage de fin d'études / Alternance possible, construction de pipelines de données.",
        6,
        "Janvier 2027",
    ),
    (
        "CDI Lead Developer Python",
        "ScaleUp",
        "Paris, France",
        "cdi",
        ["Python", "Django", "Leadership"],
        "Poste confirmé, 6 ans d'expérience minimum en encadrement technique requis.",
        None,
        "",
    ),
    (
        "Stage UX/UI + Frontend",
        "DesignTech",
        "Lyon, France",
        "stage",
        ["Figma", "React", "CSS"],
        "Stage de 4 mois, conception d'interfaces et intégration frontend.",
        4,
        "Mai 2027",
    ),
    (
        "Alternance QA Automation Engineer",
        "QualityFirst",
        "Toulouse, France",
        "alternance",
        ["Python", "Selenium", "Git"],
        "Alternance de 12 mois sur l'automatisation des tests d'une plateforme SaaS.",
        12,
        "Septembre 2027",
    ),
]

# indices into OFFERS (0-based) that get a pre-computed Match, with (score axes..., legitimacy)
MATCHES = {
    0: {
        "skills": 90,
        "experience": 85,
        "education": 90,
        "location": 100,
        "language": 100,
        "matched": ["Python", "Django", "React"],
        "missing": ["SQL avancé"],
        "advice": "Bon profil pour ce stage, compétences alignées avec l'offre.",
        "legitimacy": Match.Legitimacy.RELIABLE,
        "reasons": [],
        "admin_notes": ["Convention de stage obligatoire"],
    },
    1: {
        "skills": 60,
        "experience": 70,
        "education": 80,
        "location": 100,
        "language": 90,
        "matched": ["Python", "SQL"],
        "missing": ["Power BI"],
        "advice": "Correspond bien, une montée en compétence sur Power BI serait un plus.",
        "legitimacy": Match.Legitimacy.RELIABLE,
        "reasons": [],
        "admin_notes": [],
    },
    2: {
        "skills": 55,
        "experience": 75,
        "education": 80,
        "location": 90,
        "language": 100,
        "matched": ["Docker"],
        "missing": ["Kubernetes", "AWS"],
        "advice": "Bonnes bases DevOps, Kubernetes et AWS restent à approfondir.",
        "legitimacy": Match.Legitimacy.RELIABLE,
        "reasons": [],
        "admin_notes": [],
    },
    3: {
        "skills": 30,
        "experience": 5,
        "education": 60,
        "location": 100,
        "language": 100,
        "matched": ["SQL"],
        "missing": ["Java", "Spring"],
        "advice": "Ce poste vise un profil confirmé : 8 ans d'expérience sont exigés.",
        "legitimacy": Match.Legitimacy.RELIABLE,
        "reasons": [],
        "admin_notes": [],
    },
    4: {
        "skills": 70,
        "experience": 80,
        "education": 90,
        "location": 80,
        "language": 100,
        "matched": ["Python", "SQL"],
        "missing": ["Machine Learning"],
        "advice": "Profil pertinent pour ce stage recherche.",
        "legitimacy": Match.Legitimacy.RELIABLE,
        "reasons": [],
        "admin_notes": ["Niveau Bac+5 requis"],
    },
    7: {
        "skills": 20,
        "experience": 40,
        "education": 50,
        "location": 90,
        "language": 100,
        "matched": [],
        "missing": ["Réseau", "Support"],
        "advice": "Peu aligné avec le profil de développeur ciblé.",
        "legitimacy": Match.Legitimacy.TO_VERIFY,
        "reasons": ["Entreprise d'intérim, mission courte non précisée en détail"],
        "admin_notes": [],
    },
    11: {
        "skills": 85,
        "experience": 80,
        "education": 85,
        "location": 100,
        "language": 100,
        "matched": ["Python", "SQL", "Docker"],
        "missing": [],
        "advice": "Excellente correspondance pour ce stage.",
        "legitimacy": Match.Legitimacy.RELIABLE,
        "reasons": [],
        "admin_notes": [],
    },
    13: {
        "skills": 65,
        "experience": 70,
        "education": 75,
        "location": 100,
        "language": 90,
        "matched": ["React"],
        "missing": ["Figma"],
        "advice": "Bon profil frontend, Figma serait à découvrir rapidement.",
        "legitimacy": Match.Legitimacy.RELIABLE,
        "reasons": [],
        "admin_notes": [],
    },
}

# (offer index, application status, days_ago applied)
APPLICATIONS = [
    (0, Application.Status.INTERVIEW, 18),
    (1, Application.Status.SENT, 10),
    (2, Application.Status.SENT, 7),
    (4, Application.Status.OFFER, 25),
    (7, Application.Status.REJECTED, 20),
    (11, Application.Status.INTERVIEW, 14),
    (13, Application.Status.SENT, 3),
    (5, Application.Status.TO_APPLY, 0),
    (9, Application.Status.TO_APPLY, 0),
    (12, Application.Status.SENT, 1),
]


class Command(BaseCommand):
    help = "Crée un compte de démonstration avec profil, offres, analyses et candidatures."

    def handle(self, *args, **options) -> None:
        user = self._create_user()
        profile = self._create_profile(user)
        offers = self._create_offers()
        self._create_matches(user, offers)
        self._create_applications(user, offers)
        self._create_documents(user, offers)

        self.stdout.write(self.style.SUCCESS("Compte de démonstration prêt :"))
        self.stdout.write(f"  email      : {DEMO_EMAIL}")
        self.stdout.write(f"  mot de passe : {DEMO_PASSWORD}")
        self.stdout.write(f"  profil     : {profile.title}")
        self.stdout.write(f"  offres     : {len(offers)}")
        self.stdout.write(f"  analyses   : {len(MATCHES)}")
        self.stdout.write(f"  candidatures : {len(APPLICATIONS)}")

    def _create_user(self):
        User = get_user_model()
        user, _ = User.objects.get_or_create(email=DEMO_EMAIL, defaults={"first_name": "Demo"})
        user.first_name = "Demo"
        user.set_password(DEMO_PASSWORD)
        user.save()
        return user

    def _create_profile(self, user):
        Profile.objects.filter(user=user).delete()
        profile = Profile.objects.create(
            user=user,
            title="Étudiant ingénieur informatique",
            summary=(
                "Étudiant en 4e année d'école d'ingénieur informatique, à la recherche d'un "
                "stage de fin d'études en développement logiciel. Projets académiques en "
                "Python/Django et React, un stage précédent de 3 mois en développement web."
            ),
            years_of_experience=0,
            city="Casablanca, Maroc",
        )
        for display_name, category in SKILLS:
            Skill.objects.create(profile=profile, display_name=display_name, category=category)
        Experience.objects.create(
            profile=profile,
            title="Stage développeur web",
            company="StartupLocale",
            start_date="Juin 2026",
            end_date="Août 2026",
            description="Développement de fonctionnalités sur une application Django/React.",
            order=0,
        )
        Experience.objects.create(
            profile=profile,
            title="Projet académique — plateforme de gestion associative",
            company="École d'ingénieurs",
            start_date="2026",
            end_date="2026",
            description=(
                "Conception et développement full-stack en équipe de 4, méthodologie agile."
            ),
            order=1,
        )
        Education.objects.create(
            profile=profile,
            degree="Diplôme d'ingénieur informatique (en cours)",
            institution="École Nationale des Sciences Appliquées",
            year="2023-2027",
            order=0,
        )
        SearchPreference.objects.update_or_create(
            user=user,
            defaults={
                "contract_types": ["stage", "alternance"],
                "countries": ["France"],
                "cities": [],
                "remote_ok": True,
                "desired_duration_months": 6,
                "desired_start_date": "Mars 2027",
                "languages": ["Français", "Anglais"],
            },
        )
        return profile

    def _create_offers(self):
        offers = []
        for i, (
            title,
            company,
            location,
            contract_type,
            tags,
            description,
            duration,
            start,
        ) in enumerate(OFFERS):
            offer, _ = JobOffer.objects.update_or_create(
                source=JobOffer.Source.MANUAL,
                external_id=f"demo-{i}",
                defaults={
                    "title": title,
                    "company": company,
                    "location": location,
                    "remote": location == "Télétravail",
                    "description": description,
                    "url": f"https://example.com/offres/demo-{i}",
                    "contract_type": contract_type,
                    "duration_months": duration,
                    "start_date": start,
                    "tags": tags,
                    "language": "fr",
                    "published_at": timezone.now() - timedelta(days=30 - i),
                },
            )
            offers.append(offer)
        return offers

    def _create_matches(self, user, offers):
        Match.objects.filter(user=user).delete()
        for index, data in MATCHES.items():
            axis_scores = {
                "skills_score": data["skills"],
                "experience_score": data["experience"],
                "education_score": data["education"],
                "location_score": data["location"],
                "language_score": data["language"],
            }
            score = round(
                axis_scores["skills_score"] * 0.40
                + axis_scores["experience_score"] * 0.25
                + axis_scores["education_score"] * 0.10
                + axis_scores["location_score"] * 0.15
                + axis_scores["language_score"] * 0.10
            )
            Match.objects.create(
                user=user,
                job_offer=offers[index],
                score=score,
                **axis_scores,
                matched_skills=data["matched"],
                missing_skills=data["missing"],
                advice=data["advice"],
                legitimacy=data["legitimacy"],
                legitimacy_reasons=data["reasons"],
                administrative_notes=data["admin_notes"],
                llm_model="demo-seed",
            )

    def _create_documents(self, user, offers):
        offer = offers[0]  # "Stage Développeur Full-Stack Python/React"

        CoverLetter.objects.filter(user=user, job_offer=offer).delete()
        CoverLetter.objects.create(
            user=user,
            job_offer=offer,
            language="fr",
            content=(
                "Madame, Monsieur,\n\n"
                "Étudiant en 4e année d'école d'ingénieur informatique, je vous propose ma "
                "candidature pour le stage de fin d'études de développeur full-stack Python/React "
                "au sein de TechCorp.\n\n"
                "Au cours de mes projets académiques et d'un premier stage de trois mois, j'ai "
                "développé des applications web complètes avec Django et React, de la "
                "modélisation des données à l'intégration frontend. Je porte une attention "
                "particulière à la qualité du code et au travail en équipe agile.\n\n"
                "Rejoindre votre équipe produit serait l'occasion de mettre ces compétences au "
                "service d'un produit à plus grande échelle, tout en continuant à progresser sur "
                "les bonnes pratiques de développement.\n\n"
                "Je reste à votre disposition pour un entretien.\n\n"
                "Cordialement,\nDemo"
            ),
            llm_model="demo-seed",
        )

        TailoredCV.objects.filter(user=user, job_offer=offer).delete()
        TailoredCV.objects.create(
            user=user,
            job_offer=offer,
            content={
                "titre": "Étudiant ingénieur informatique — Développement Full-Stack",
                "resume": (
                    "Étudiant en 4e année, spécialisé en développement web Python/Django et "
                    "React, à la recherche d'un stage de fin d'études."
                ),
                "competences": ["Python", "Django", "React", "SQL", "Git"],
                "experiences": [
                    {
                        "poste": "Stage développeur web",
                        "entreprise": "StartupLocale",
                        "description": (
                            "Développement de fonctionnalités sur une application Django/React "
                            "en équipe, revue de code et tests."
                        ),
                    },
                    {
                        "poste": "Projet académique — plateforme de gestion associative",
                        "entreprise": "École d'ingénieurs",
                        "description": (
                            "Conception et développement full-stack en équipe de 4, méthodologie "
                            "agile, déploiement continu."
                        ),
                    },
                ],
            },
            llm_model="demo-seed",
        )

        InterviewPrep.objects.filter(user=user, job_offer=offer).delete()
        InterviewPrep.objects.create(
            user=user,
            job_offer=offer,
            questions=[
                {
                    "question": (
                        "Parlez-nous d'un projet où vous avez utilisé Django et React ensemble."
                    ),
                    "situation": (
                        "Projet académique de plateforme de gestion associative en équipe de 4."
                    ),
                    "tache": "Concevoir l'API Django et l'intégrer à une interface React.",
                    "action": (
                        "Mise en place d'une API REST, gestion des états côté frontend, "
                        "tests unitaires."
                    ),
                    "resultat": (
                        "Plateforme livrée dans les délais, adoptée par deux associations "
                        "partenaires."
                    ),
                },
                {
                    "question": (
                        "Comment gérez-vous le travail en équipe sur un projet de développement ?"
                    ),
                    "situation": "Stage de trois mois au sein d'une petite équipe produit.",
                    "tache": "Contribuer à une base de code partagée sans ralentir l'équipe.",
                    "action": (
                        "Revues de code systématiques, communication régulière, découpage en "
                        "tâches claires."
                    ),
                    "resultat": (
                        "Intégration réussie dès la première semaine, fonctionnalités livrées "
                        "sans régression."
                    ),
                },
                {
                    "question": (
                        "Quelle est votre expérience avec les bases de données relationnelles ?"
                    ),
                    "situation": "Utilisation de PostgreSQL sur plusieurs projets académiques.",
                    "tache": "Modéliser des schémas de données cohérents et performants.",
                    "action": (
                        "Conception de modèles Django, optimisation de requêtes, gestion des "
                        "migrations."
                    ),
                    "resultat": (
                        "Aucune régression de performance constatée malgré la montée en charge "
                        "des données de test."
                    ),
                },
                {
                    "question": (
                        "Le poste nécessite de l'anglais professionnel : comment évaluez-vous "
                        "votre niveau ?"
                    ),
                    "situation": (
                        "Cours et projets en anglais technique durant la formation d'ingénieur."
                    ),
                    "tache": (
                        "Comprendre une documentation technique et échanger avec des "
                        "interlocuteurs anglophones."
                    ),
                    "action": (
                        "Pratique régulière via la documentation officielle et des projets "
                        "open source en anglais."
                    ),
                    "resultat": (
                        "Niveau suffisant pour suivre une réunion technique, en progression "
                        "continue."
                    ),
                },
                {
                    "question": "Comment réagissez-vous face à un bug difficile à reproduire ?",
                    "situation": "Bug intermittent rencontré lors du stage précédent.",
                    "tache": "Identifier la cause sans reproduction fiable en local.",
                    "action": (
                        "Ajout de journaux détaillés, isolation progressive des composants, "
                        "tests ciblés."
                    ),
                    "resultat": (
                        "Cause identifiée (condition de concurrence) et corrigée en une journée."
                    ),
                },
            ],
            llm_model="demo-seed",
        )

    def _create_applications(self, user, offers):
        Application.objects.filter(user=user).delete()
        for index, status, days_ago in APPLICATIONS:
            offer = offers[index]
            application, _ = create_or_get_application(user, offer)
            if status != Application.Status.SENT:
                move_application(application, status, [application.pk])
            applied_at = timezone.now().date() - timedelta(days=days_ago)
            Application.objects.filter(pk=application.pk).update(applied_at=applied_at)
