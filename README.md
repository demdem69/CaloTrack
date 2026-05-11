# CaloTrack
An open source tool for monitoring your calorie deficit

## Architecture de déploiement

- `web/`: frontend React + Vite, déployé sur GitHub Pages
- `api/`: backend FastAPI, déployé sur Render
- Aiven PostgreSQL: base de données distante utilisée par l’API

## Pré-requis

- Node.js 20+ (frontend)
- Python 3.11+ (backend)

## Lancer en local

```bash
cd web
npm install
npm run dev
```

Backend (dans un autre terminal):

```bash
cd api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn api.main:app --reload --port 8000
```

## Configuration de déploiement

### 1) Aiven PostgreSQL

Utilise la connexion PostgreSQL fournie par Aiven.

- Hôte : `DB_HOST`
- Port : `14530`
- Base : `defaultdb`
- Utilisateur : `DB_USER`
- Mot de passe : `DB_PASSWORD`
- SSL : `sslmode=require`

Le fichier `api/.env.example` montre les variables nécessaires.

### 2) Render pour l’API

Le fichier `render.yaml` définit le service Render pour l’API.

- buildCommand: `pip install -r api/requirements.txt`
- startCommand: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
- variables non synchronisées pour les secrets : `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `CORS_ORIGINS`

Dans Render, ajoute aussi :

- `DB_PORT=14530`
- `DB_NAME=defaultdb`
- `DB_SSLMODE=require`

### 3) GitHub Pages pour le frontend

Le workflow `.github/workflows/deploy-pages.yml` publie `web/dist` sur GitHub Pages.

La variable `VITE_API_BASE_URL` doit être définie dans les variables GitHub Actions du repository.

Exemple de valeur :

- `https://<ton-service>.onrender.com`

### 4) CORS

Pour que l’API accepte les requêtes depuis GitHub Pages, configure `CORS_ORIGINS` sur Render avec le domaine du site Pages :

- `https://<ton-user>.github.io`

ou avec un domaine custom si tu utilises un custom domain.

### 5) Tester en production

- Ouvre le site GitHub Pages
- Vérifie que l’API est atteignable via le front
- Vérifie `/health` sur l’URL Render
