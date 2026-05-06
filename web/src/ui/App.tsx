import React, { useEffect, useMemo, useState } from "react";
import { API_BASE_URL } from "../config";

type AuthState =
  | { status: "loggedOut" }
  | { status: "loggedIn"; groupId: string; password: string };

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "content-type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = (await res.json()) as { detail?: unknown };
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      // ignore
    }
    throw new Error(detail);
  }
  return (await res.json()) as T;
}

export function App() {
  const [auth, setAuth] = useState<AuthState>({ status: "loggedOut" });
  const [mode, setMode] = useState<"login" | "create">("login");
  const [groupId, setGroupId] = useState("");
  const [pw, setPw] = useState("");
  const [error, setError] = useState<string | null>(null);

  const [health, setHealth] = useState<"unknown" | "ok" | "down">("unknown");
  const allGroups = useMemo(() => [], []);

  useEffect(() => {
    api<{ status: string }>("/health")
      .then(() => setHealth("ok"))
      .catch(() => setHealth("down"));
  }, []);

  async function onSubmit() {
    setError(null);
    const gid = groupId.trim();
    if (!gid) return setError("Nom du foyer requis.");
    if (!pw) return setError("Mot de passe requis.");

    if (mode === "login") {
      try {
        await api<{ group_id: string }>("/auth/login", {
          method: "POST",
          body: JSON.stringify({ group_id: gid, password: pw }),
        });
        setAuth({ status: "loggedIn", groupId: gid, password: pw });
        setPw("");
        return;
      } catch (e) {
        return setError(e instanceof Error ? e.message : "Erreur de connexion.");
      }
    }

    try {
      await api<{ group_id: string }>("/auth/register", {
        method: "POST",
        body: JSON.stringify({ group_id: gid, password: pw }),
      });
      setAuth({ status: "loggedIn", groupId: gid, password: pw });
      setPw("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur lors de la création.");
    }
  }

  if (auth.status === "loggedIn") {
    return (
      <Shell
        groupId={auth.groupId}
        password={auth.password}
        onLogout={() => setAuth({ status: "loggedOut" })}
      />
    );
  }

  return (
    <main className="container">
      <header className="header">
        <div className="brand">
          <div className="logo" aria-hidden="true">
            CT
          </div>
          <div>
            <div className="title">CaloTrack</div>
            <div className="subtitle">
              API:{" "}
              {health === "unknown"
                ? "…"
                : health === "ok"
                  ? "connectée"
                  : "injoignable"}{" "}
              · {API_BASE_URL}
            </div>
          </div>
        </div>
      </header>

      <section className="card">
        <h1>Connexion</h1>

        <div className="segmented" role="tablist" aria-label="Action">
          <button
            className={mode === "login" ? "seg active" : "seg"}
            onClick={() => setMode("login")}
            type="button"
          >
            Connexion
          </button>
          <button
            className={mode === "create" ? "seg active" : "seg"}
            onClick={() => setMode("create")}
            type="button"
          >
            Créer un nouveau Foyer
          </button>
        </div>

        <div className="form">
          <label className="field">
            <span>Nom du Foyer</span>
            <input
              value={groupId}
              onChange={(e) => setGroupId(e.target.value)}
              placeholder="ex: Maison"
              autoCapitalize="off"
              autoCorrect="off"
            />
          </label>
          <label className="field">
            <span>Mot de passe</span>
            <input
              value={pw}
              onChange={(e) => setPw(e.target.value)}
              type="password"
            />
          </label>

          {allGroups.length > 0 ? (
            <p className="hint">Foyers sur cet appareil: {allGroups.join(", ")}</p>
          ) : (
            <p className="hint">
              Les foyers sont stockés côté serveur (PostgreSQL). Choisis un nom de foyer
              puis connecte-toi ou crée-le.
            </p>
          )}

          {error ? <p className="error">{error}</p> : null}

          <div className="actions">
            <button className="btn primary" type="button" onClick={onSubmit}>
              {mode === "login" ? "Se connecter" : "Créer le compte"}
            </button>
          </div>
        </div>
      </section>

      <footer className="footer">
        <span>Les données sont stockées en base PostgreSQL (Aiven) via l’API.</span>
      </footer>
    </main>
  );
}

function Shell(props: { groupId: string; password: string; onLogout: () => void }) {
  const [users, setUsers] = useState<string[]>([]);
  const [newUser, setNewUser] = useState("");
  const [err, setErr] = useState<string | null>(null);

  async function refreshUsers() {
    setErr(null);
    try {
      const data = await api<{ users: string[] }>(
        `/groups/${encodeURIComponent(props.groupId)}/users?password=${encodeURIComponent(
          props.password,
        )}`,
      );
      setUsers(data.users);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Erreur.");
    }
  }

  useEffect(() => {
    refreshUsers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <main className="container">
      <header className="header">
        <div className="brand">
          <div className="logo" aria-hidden="true">
            CT
          </div>
          <div>
            <div className="title">CaloTrack</div>
            <div className="subtitle">🏠 Foyer : {props.groupId}</div>
          </div>
        </div>

        <div className="actions">
          <button className="btn" type="button" onClick={props.onLogout}>
            Se déconnecter
          </button>
        </div>
      </header>

      <section className="card">
        <h1>Paramètres (demo API)</h1>
        <p>
          Cette section prouve la connexion Front → API → PostgreSQL. Prochaine étape: remettre
          tous les onglets (Repas/Bilan/Historique/Gestion) comme avant.
        </p>

        <div className="form">
          <div className="actions">
            <button className="btn" type="button" onClick={refreshUsers}>
              Rafraîchir
            </button>
          </div>

          {err ? <p className="error">{err}</p> : null}

          <div>
            <p className="hint">Membres: {users.length === 0 ? "—" : users.join(", ")}</p>
          </div>

          <label className="field">
            <span>Ajouter un membre</span>
            <input value={newUser} onChange={(e) => setNewUser(e.target.value)} />
          </label>
          <div className="actions">
            <button
              className="btn primary"
              type="button"
              onClick={async () => {
                setErr(null);
                const name = newUser.trim();
                if (!name) return;
                try {
                  await api<{ ok: boolean }>(
                    `/groups/${encodeURIComponent(props.groupId)}/users?password=${encodeURIComponent(
                      props.password,
                    )}`,
                    { method: "POST", body: JSON.stringify({ name }) },
                  );
                  setNewUser("");
                  await refreshUsers();
                } catch (e) {
                  setErr(e instanceof Error ? e.message : "Erreur.");
                }
              }}
            >
              Ajouter
            </button>
          </div>
        </div>
      </section>
    </main>
  );
}

