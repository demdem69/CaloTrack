# CaloTrack
An open source tool for monitoring your calorie deficit

## Architecture

- `web/`: frontend Vite (déployable sur GitHub Pages)
- `api/`: backend FastAPI (à héberger ailleurs) qui se connecte à PostgreSQL (Aiven)

### Pré-requis

- Node.js 20+ (frontend)
- Python 3.11+ (backend)

### Lancer en local

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

### Déploiement sur GitHub Pages

1. Pousse les changements sur la branche `main`.
2. Sur GitHub, va dans **Settings → Pages**.
3. Dans **Build and deployment**, choisis **Source: GitHub Actions**.
4. Le workflow `Deploy web to GitHub Pages` va builder `web/` et publier automatiquement.

Le site sera disponible à l’URL:
- `https://<ton-user>.github.io/<nom-du-repo>/`

> Note: GitHub Pages est statique. Le backend `api/` doit être déployé sur une plateforme qui exécute Python et expose HTTPS.
