# Déploiement sur Render

Ce guide décrit le déploiement de JobPilot sur [Render](https://render.com) à partir du fichier
`render.yaml` déjà présent à la racine du dépôt. Il ne remplace pas la création du compte ni la
saisie des identifiants — ça, c'est à toi de le faire dans l'interface Render.

## 1. Créer le compte Render

1. Va sur https://render.com et crée un compte (le plus simple : « Sign up with GitHub », ça
   simplifie l'étape suivante).
2. Vérifie ton adresse e-mail si Render te le demande.

## 2. Déployer le Blueprint

1. Pousse ton code sur GitHub si ce n'est pas déjà fait (`git push`).
2. Dans le tableau de bord Render, clique sur **New +** → **Blueprint**.
3. Connecte le dépôt GitHub `jobpilot` (Render te demandera d'autoriser l'accès à ton compte
   GitHub la première fois).
4. Render détecte automatiquement `render.yaml` à la racine et te propose de créer :
   - un service web `jobpilot` (construit avec le `Dockerfile` du dépôt),
   - une base `jobpilot-db` (PostgreSQL, plan gratuit).
5. Clique sur **Apply**. Render crée les deux ressources. Le premier build prend quelques minutes
   (construction de l'image Docker, `collectstatic`, etc.).

## 3. Renseigner les variables d'environnement

`render.yaml` génère automatiquement `SECRET_KEY` et relie `DATABASE_URL` à la base créée. Les
variables suivantes sont volontairement laissées vides (`sync: false`) — va dans
**jobpilot → Environment** et complète-les avant le premier déploiement utile :

| Variable | Où la trouver | Exemple |
|---|---|---|
| `ALLOWED_HOSTS` | l'URL que Render attribue au service (visible en haut de la page du service) | `jobpilot.onrender.com` |
| `CSRF_TRUSTED_ORIGINS` | la même URL, avec le schéma `https://` | `https://jobpilot.onrender.com` |
| `LLM_BASE_URL` | ton fournisseur LLM (Groq recommandé pour le coût) | `https://api.groq.com/openai/v1` |
| `LLM_API_KEY` | ta clé API Groq (https://console.groq.com) | — |
| `LLM_MODEL` | un modèle de production actuellement disponible sur ton compte Groq | `openai/gpt-oss-120b` (vérifie avec `check_llm`, voir plus bas) |
| `FRANCE_TRAVAIL_CLIENT_ID` | ton application créée sur https://francetravail.io | — |
| `FRANCE_TRAVAIL_CLIENT_SECRET` | idem | — |

Si tu n'as pas encore de clé France Travail, laisse ces deux variables vides : la source est
simplement désactivée avec un message clair, l'import des autres sources (Remotive, Arbeitnow)
continue de fonctionner normalement.

Après avoir renseigné les variables, clique sur **Save, rebuild, and deploy** (ou attends le
prochain déploiement automatique après un `git push`).

## 4. Vérifier que ça tourne

- Ouvre `https://<ton-service>.onrender.com/health/` → doit répondre `{"status": "ok"}`.
- Ouvre `https://<ton-service>.onrender.com/` → la page d'accueil doit s'afficher.
- Depuis l'onglet **Shell** du service Render, vérifie la configuration LLM :
  ```bash
  python manage.py check_llm
  ```

## 5. Créer ton premier compte

L'inscription est publique (`/comptes/inscription/`) : crée simplement ton compte depuis le
navigateur, comme n'importe quel visiteur. Si tu as besoin d'un accès admin Django
(`/admin/`), ouvre l'onglet **Shell** du service Render et lance :

```bash
python manage.py createsuperuser
```

## 6. Erreurs fréquentes

**`DisallowedHost at /`**
`ALLOWED_HOSTS` n'est pas renseigné ou ne correspond pas exactement au domaine Render (sans
`https://`, sans slash final). Vérifie la valeur exacte affichée en haut de la page du service.

**`CSRF verification failed` en essayant de se connecter ou de soumettre un formulaire**
`CSRF_TRUSTED_ORIGINS` manque ou n'a pas le schéma `https://`. Contrairement à `ALLOWED_HOSTS`,
cette variable a besoin du schéma complet.

**Le service met plusieurs dizaines de secondes à répondre après une période d'inactivité**
Normal sur le plan gratuit Render : le service « s'endort » après 15 minutes sans trafic et se
réveille à la première requête. Pas un bug de l'application.

**Mes CV/documents ont disparu après un redéploiement**
Le plan gratuit Render n'offre pas de disque persistant : `MEDIA_ROOT` (les CV uploadés) vit sur
un disque éphémère, effacé à chaque déploiement ou redémarrage. C'est documenté dans
`config/settings/prod.py`. Pour un usage réel au-delà d'une démo, il faut brancher un stockage
externe (S3, Cloudflare R2, Backblaze B2…) via `django-storages` et la variable
`MEDIA_STORAGE_BACKEND` — aucune autre modification de code n'est nécessaire, les CV passent déjà
par l'abstraction de stockage de Django.

**La base de données PostgreSQL gratuite Render expire après 90 jours**
Limite du plan gratuit Render, pas de JobPilot. Render t'enverra un rappel par e-mail avant
l'expiration ; il faut alors créer une nouvelle base ou passer sur un plan payant.

**`python manage.py check_llm` échoue avec « model_not_found »**
Le modèle choisi n'est plus disponible sur ton compte Groq. La commande liste automatiquement les
modèles réellement accessibles sur ta clé — choisis-en un dans la liste et mets à jour
`LLM_MODEL`.

**Les imports d'offres ne remontent rien**
Vérifie les logs du service (onglet **Logs**) : chaque source échoue avec un message explicite
si son API est indisponible ou ses identifiants absents, sans jamais faire planter l'import des
autres sources.
