## Déploiement (Front GitHub Pages + API Render + DB Aiven)

### 1) Préparer Aiven PostgreSQL

Dans Aiven, crée une base PostgreSQL et récupère les informations de connexion :

- **DB_HOST** : nom de l’hôte Aiven
- **DB_PORT** : `14530`
- **DB_NAME** : `defaultdb`
- **DB_USER** : utilisateur Aiven
- **DB_PASSWORD** : mot de passe Aiven
- **DB_SSLMODE** : `require`

Le projet contient déjà `api/.env.example` avec ces variables.

### 2) Déployer l’API sur Render

Le fichier `render.yaml` définit le service Render pour l’API.

- Sur Render : **New → Blueprint**
- Sélectionne le repo GitHub `CaloTrack`
- Render détecte `render.yaml` et crée le service `calotrack-api`

Dans Render, configure ensuite ces variables d’environnement :

- `DB_HOST` = hôte Aiven
- `DB_USER` = utilisateur Aiven
- `DB_PASSWORD` = mot de passe Aiven
- `CORS_ORIGINS` = `https://<ton-user>.github.io` (ou ton domaine custom)

Les variables préconfigurées dans `render.yaml` sont :

- `DB_PORT=14530`
- `DB_NAME=defaultdb`
- `DB_SSLMODE=require`

### 3) Configurer GitHub Pages pour le frontend

Le front se compile avec `VITE_API_BASE_URL`.

Sur GitHub : **Settings → Secrets and variables → Actions → Variables → New repository variable**

- Name : `VITE_API_BASE_URL`
- Value : `https://<ton-service>.onrender.com`

Le workflow `.github/workflows/deploy-pages.yml` utilise cette variable pendant le build.

### 4) Vérifier CORS

Sur Render, `CORS_ORIGINS` doit contenir le domaine de ton site GitHub Pages :

- `https://<ton-user>.github.io`

et si nécessaire :

- `http://localhost:5173` pour le développement local.

### 5) Tester l’intégration

- Déploie le backend sur Render
- Déploie le frontend sur GitHub Pages
- Ouvre le site Pages
- Vérifie que l’API `/health` répond bien
- Teste l’authentification et l’ajout des utilisateurs

