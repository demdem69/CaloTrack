# CaloTrack
An open source tool for monitoring your calorie deficit

## Déploiement GitHub Pages (Vite)

Ce dépôt contient aussi un petit site statique Vite dans `web/`, déployable via GitHub Pages.

### Pré-requis

- Node.js 20+

### Lancer en local

```bash
cd web
npm install
npm run dev
```

### Déploiement sur GitHub Pages

1. Pousse les changements sur la branche `main`.
2. Sur GitHub, va dans **Settings → Pages**.
3. Dans **Build and deployment**, choisis **Source: GitHub Actions**.
4. Le workflow `Deploy web to GitHub Pages` va builder `web/` et publier automatiquement.

Le site sera disponible à l’URL:
- `https://<ton-user>.github.io/<nom-du-repo>/`

> Note: l’application principale (`streamlit_app.py`) nécessite Python + PostgreSQL et ne peut pas être hébergée sur GitHub Pages (statique uniquement).
