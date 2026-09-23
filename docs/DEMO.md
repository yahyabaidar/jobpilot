# Script de démonstration (1 min 30)

Prépare l'environnement avant d'enregistrer :

```bash
docker compose up -d
docker compose exec web python manage.py seed_demo
```

Connecte-toi avec `demo@jobpilot.dev` / `Demo1234!` — le compte a déjà un profil de recherche de
stage, 15 offres (stages, alternances et quelques CDI/CDD/intérim pour montrer le filtre par type
de contrat), 8 analyses et 10 candidatures réparties dans le Kanban, donc rien à attendre à
l'écran.

## Déroulé, étape par étape

| Temps | Ce que tu montres | Ce que tu dis (ou sous-titres) |
|---|---|---|
| 0:00–0:10 | Page d'accueil publique, clique sur « Créer un compte » puis « Connexion » avec le compte démo. | « JobPilot m'aide à trouver mon stage de fin d'études : il analyse mon CV, note les offres selon mon profil d'étudiant, et prépare mes candidatures. » |
| 0:10–0:25 | Tableau de bord : fais défiler les 4 chiffres clés, la section « Stages correspondant à tes préférences », puis les 4 graphiques. Bascule le thème clair/sombre pour montrer que les graphiques se recolorent instantanément. | « Tout est calculé sur mes vraies données : compétences qui me manquent, marché, mes scores, mes candidatures dans le temps. » |
| 0:25–0:35 | Onglet Offres : montre le filtre « Stage » coché par défaut (alternance et autres contrats accessibles en un clic), le badge de score coloré sur les cartes. | « Par défaut je ne vois que des stages — c'est ce que je cherche. L'alternance et les autres contrats restent à portée de clic. » |
| 0:35–0:55 | Ouvre une offre déjà analysée (ex. « Stage Développeur Full-Stack Python/React ») : montre le score, le radar 5 axes, les compétences en vert/rouge, le badge de légitimité, l'encadré admissibilité si présent. | « Le score s'adapte à mon profil d'étudiant — pas de pénalité pour manque d'expérience pro sur un stage. » |
| 0:55–1:10 | Sur la même page, ouvre l'onglet Lettre (montre un brouillon déjà généré) puis l'onglet Entretien (accordéon avec une question). | « Lettre, CV adapté et préparation d'entretien générés à partir de mon vrai profil, jamais inventés. » |
| 1:10–1:25 | Onglet Candidatures : glisse une carte d'une colonne à une autre pour montrer le Kanban en direct. Ouvre le panneau latéral d'une carte pour montrer les notes. | « Je suis mes candidatures par glisser-déposer, avec l'historique des statuts. » |
| 1:25–1:30 | Retour au tableau de bord ou à la page d'accueil pour clore. | « Construit étape par étape, testé, et prêt à déployer. » |

## Astuces pour l'enregistrement

- Réduis la fenêtre à une taille raisonnable (1280×800 par exemple) avant de démarrer, pour que le
  GIF reste léger.
- Le clic sur le bouton de thème doit être visible à l'écran assez longtemps pour que le
  changement de couleur des graphiques soit perceptible dans le GIF.
- Évite de cliquer sur « Postuler » (ouvre un vrai lien externe) ou sur « Régénérer » (déclenche
  un vrai appel IA, donc un temps d'attente) pendant l'enregistrement — utilise plutôt les
  documents déjà générés par `seed_demo`.
- Si tu relances la démo plusieurs fois, `seed_demo` est idempotent : il réinitialise le profil,
  les offres, les analyses et les candidatures du compte démo à chaque exécution.
