import "./style.css";

const app = document.querySelector<HTMLDivElement>("#app");
if (!app) throw new Error("Missing #app");

app.innerHTML = `
  <main class="container">
    <header class="header">
      <div class="brand">
        <div class="logo" aria-hidden="true">CT</div>
        <div>
          <div class="title">CaloTrack</div>
          <div class="subtitle">Suivi simple du déficit calorique</div>
        </div>
      </div>
    </header>

    <section class="card">
      <h1>Bienvenue</h1>
      <p>
        Cette page est un <strong>front statique</strong> déployé via <strong>Vite</strong> sur
        <strong>GitHub Pages</strong>.
      </p>
      <p>
        L’application complète est écrite en <strong>Streamlit</strong> et nécessite une base PostgreSQL ;
        elle doit être hébergée sur une plateforme qui exécute Python (ex. Streamlit Community Cloud).
      </p>
      <div class="actions">
        <a class="btn primary" href="https://streamlit.io/cloud" target="_blank" rel="noreferrer">
          Héberger l’app Streamlit
        </a>
        <a class="btn" href="https://github.com/" target="_blank" rel="noreferrer">
          Voir le repo
        </a>
      </div>
    </section>

    <footer class="footer">
      <span>© ${new Date().getFullYear()} CaloTrack</span>
    </footer>
  </main>
`;

