## Déploiement (Front GitHub Pages + API Render + DB Aiven)

### 1) Préparer Aiven PostgreSQL

Dans Aiven, récupère les infos de connexion (Overview / Connection information):

- **DB name**: `defaultdb`
- **Port**: `14530`
- **Host**
- **User**
- **Password**
- **SSL**: requis (on utilise `sslmode=require`)

### 2) Déployer l’API sur Render

Option A (recommandé): via `render.yaml`

- Sur Render: **New → Blueprint**
- Sélectionne le repo GitHub `CaloTrack`
- Render va détecter `render.yaml` et créer le service `calotrack-api`

Renseigne ensuite les variables d’environnement (dans le service Render):

- `DB_HOST` = host Aiven
- `DB_USER` = user Aiven
- `DB_PASSWORD` = password Aiven
- `CORS_ORIGINS` = `https://demdem69.github.io` (et éventuellement `http://localhost:5173` séparé par virgule)

Les variables déjà fixées:

- `DB_PORT=14530`
- `DB_NAME=defaultdb`
- `DB_SSLMODE=require`

Teste l’API:

- Ouvre `/health` sur l’URL Render de l’API (doit répondre `{"status":"ok"}`)

### 3) Connecter le Front (GitHub Pages) à l’API

Le front lit `VITE_API_BASE_URL` au **build**.

Sur GitHub: **Settings → Secrets and variables → Actions → Variables → New repository variable**

- Name: `VITE_API_BASE_URL`
- Value: `https://<ton-service>.onrender.com`

Ensuite, push sur `main` (ou relance le workflow Pages). Le build injectera cette URL.

### 4) Déployer le Front sur GitHub Pages

- GitHub: **Settings → Pages**
- Source: **GitHub Actions**
- Attends le workflow `Deploy web to GitHub Pages`

### 5) Test end-to-end

- Ouvre le site Pages
- Crée un foyer (Register)
- Connecte-toi (Login)
- Ajoute un membre (la section "Paramètres (demo API)" doit lister/ajouter)

