import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import hashlib
from datetime import date, timedelta
from sqlalchemy import text

# --- CONFIGURATION DB CLOUD (PostgreSQL) ---
# Se connecte aux secrets configurés dans l'onglet "Data" de Streamlit Cloud
conn = st.connection("postgresql", type="sql")

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def init_db():
    with conn.session as s:
        # Tables avec syntaxe PostgreSQL
        s.execute(text('CREATE TABLE IF NOT EXISTS accounts (group_id TEXT PRIMARY KEY, password TEXT)'))
        s.execute(text('CREATE TABLE IF NOT EXISTS users (name TEXT, group_id TEXT, PRIMARY KEY(name, group_id))'))
        s.execute(text('CREATE TABLE IF NOT EXISTS foods (name TEXT PRIMARY KEY, cal_100g REAL)'))
        s.execute(text('''CREATE TABLE IF NOT EXISTS meal_logs 
                 (id SERIAL PRIMARY KEY, date DATE, label TEXT, "user" TEXT, calories REAL, group_id TEXT)'''))
        s.execute(text('''CREATE TABLE IF NOT EXISTS daily_spend 
                 (date DATE, "user" TEXT, depense REAL, group_id TEXT, PRIMARY KEY (date, "user", group_id))'''))
        
        # Injection de la liste des 100 aliments si vide
        check_foods = s.execute(text("SELECT COUNT(*) FROM foods")).fetchone()
        if check_foods[0] == 0:
            aliments_100 = [
                ('Poulet (Blanc)', 165), ('Riz cuit', 130), ('Pâtes cuites', 150), ('Œuf (unité)', 155),
                ('Avocat', 160), ('Pomme', 52), ('Pain Baguette', 250), ('Beurre', 717), ('Huile d\'olive', 884),
                ('Brocoli', 34), ('Banane', 89), ('Yaourt nature', 63), ('Chocolat Noir 70%', 546),
                ('Saumon', 208), ('Amandes', 579), ('Flocons d\'avoine', 370), ('Lentilles cuites', 116)
                # Note: Tu peux copier la liste complète des 100 ici
            ]
            for name, cal in aliments_100:
                s.execute(text("INSERT INTO foods (name, cal_100g) VALUES (:n, :c) ON CONFLICT DO NOTHING"), {"n": name, "c": cal})
        s.commit()

def run_query(query_str, params=None, fetch=False):
    with conn.session as s:
        result = s.execute(text(query_str), params)
        if fetch:
            return result.fetchall()
        s.commit()

# --- INITIALISATION STREAMLIT ---
st.set_page_config(page_title="CaloTrack Pro Cloud", layout="wide")
init_db()

if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'group_id' not in st.session_state: st.session_state.group_id = None

# --- ECRAN DE CONNEXION ---
if not st.session_state.logged_in:
    st.title("🍎 CaloTrack Pro")
    mode = st.radio("Action", ["Connexion", "Créer un nouveau Foyer"], horizontal=True)
    g_id = st.text_input("Nom du Foyer")
    pw = st.text_input("Mot de passe", type="password")
    
    if mode == "Connexion":
        if st.button("Se connecter"):
            res = run_query("SELECT password FROM accounts WHERE group_id=:g", {"g": g_id}, fetch=True)
            if res and res[0][0] == hash_pw(pw):
                st.session_state.logged_in = True
                st.session_state.group_id = g_id
                st.rerun()
            else: st.error("Identifiants incorrects.")
    else:
        if st.button("Créer le compte"):
            if g_id and pw:
                try:
                    run_query("INSERT INTO accounts (group_id, password) VALUES (:g, :p)", {"g": g_id, "p": hash_pw(pw)})
                    st.success("Foyer créé ! Connectez-vous.")
                except: st.error("Ce nom de foyer est déjà utilisé.")
    st.stop()

# --- APPLICATION PRINCIPALE ---
gid = st.session_state.group_id
st.sidebar.subheader(f"🏠 Foyer : {gid}")
if st.sidebar.button("Se déconnecter"):
    st.session_state.logged_in = False
    st.rerun()

users = [r[0] for r in run_query("SELECT name FROM users WHERE group_id=:g", {"g": gid}, fetch=True)]
tabs = st.tabs(["🍽️ Nouveau Repas", "🏠 Bilan du Jour", "📈 Historique Mensuel", "🗄️ Gestion", "⚙️ Paramètres"])

# --- 1. NOUVEAU REPAS ---
with tabs[0]:
    food_dict = {r[0]: r[1] for r in run_query("SELECT name, cal_100g FROM foods", fetch=True)}
    if not users: st.warning("Allez dans 'Paramètres' pour ajouter des membres.")
    else:
        with st.container(border=True):
            meal_label = st.text_input("Nom du repas", "Déjeuner")
            n_ing = st.number_input("Nombre d'ingrédients", 1, 15, 2)
            total_cal_plat = 0
            cols = st.columns(2)
            for i in range(n_ing):
                with cols[0]:
                    choice = st.selectbox(f"Ingrédient {i+1}", sorted(list(food_dict.keys())), key=f"f_{i}")
                with cols[1]:
                    weight = st.number_input(f"Poids (g) - {choice}", 0, key=f"w_{i}")
                    total_cal_plat += (food_dict[choice] * weight) / 100
        
        st.subheader("Répartition familiale")
        shares = {}
        u_cols = st.columns(len(users))
        for i, u in enumerate(users):
            with u_cols[i]:
                s = st.slider(f"{u} (%)", 0, 100, 100//len(users), key=f"s_{u}")
                ex = st.number_input(f"Extras {u} (kcal)", 0, key=f"ex_{u}")
                shares[u] = (total_cal_plat * s / 100) + ex
            
        if st.button("🚀 Valider le repas"):
            for u, cal in shares.items():
                run_query('INSERT INTO meal_logs (date, label, "user", calories, group_id) VALUES (:d, :l, :u, :c, :g)', 
                          {"d": date.today(), "l": meal_label, "u": u, "c": cal, "g": gid})
            st.success("Repas enregistré !")

# --- 2. BILAN DU JOUR ---
with tabs[1]:
    st.header(f"Bilan du {date.today().strftime('%d/%m/%Y')}")
    tday = date.today()
    for u in users:
        with st.expander(f"👤 {u}", expanded=True):
            in_res = run_query('SELECT SUM(calories) FROM meal_logs WHERE "user"=:u AND date=:d AND group_id=:g', 
                               {"u": u, "d": tday, "g": gid}, fetch=True)
            in_cal = in_res[0][0] or 0
            
            res_d = run_query('SELECT depense FROM daily_spend WHERE date=:d AND "user"=:u AND group_id=:g', 
                              {"d": tday, "u": u, "g": gid}, fetch=True)
            cur_dep = res_d[0][0] if res_d else 2000.0
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Mangé", f"{in_cal:.0f} kcal")
            new_dep = c2.number_input(f"Dépensé ({u})", value=float(cur_dep), key=f"dep_{u}")
            if new_dep != cur_dep:
                run_query('INSERT INTO daily_spend (date, "user", depense, group_id) VALUES (:d, :u, :dep, :g) ON CONFLICT (date, "user", group_id) DO UPDATE SET depense = EXCLUDED.depense', 
                          {"d": tday, "u": u, "dep": new_dep, "g": gid})
                st.rerun()
            c3.metric("Bilan", f"{in_cal - new_dep:.0f} kcal", delta=-(in_cal - new_dep), delta_color="inverse")
            
            # Liste des repas du jour
            day_meals = run_query('SELECT id, label, calories FROM meal_logs WHERE "user"=:u AND date=:d AND group_id=:g', 
                                  {"u": u, "d": tday, "g": gid}, fetch=True)
            for mid, mlabel, mcal in day_meals:
                col_m, col_b = st.columns([4, 1])
                col_m.text(f"🍴 {mlabel} : {mcal:.0f} kcal")
                if col_b.button("Suppr.", key=f"del_{mid}"):
                    run_query("DELETE FROM meal_logs WHERE id=:id", {"id": mid})
                    st.rerun()

# --- 3. HISTORIQUE MENSUEL ---
with tabs[2]:
    if users:
        u_hist = st.selectbox("Historique de :", users)
        history = []
        total_in, total_out = 0, 0
        for i in range(30, -1, -1):
            d = (date.today() - timedelta(days=i))
            in_c = run_query('SELECT SUM(calories) FROM meal_logs WHERE "user"=:u AND date=:d AND group_id=:g', 
                             {"u": u_hist, "d": d, "g": gid}, fetch=True)[0][0] or 0
            out_c_res = run_query('SELECT depense FROM daily_spend WHERE "user"=:u AND date=:d AND group_id=:g', 
                                  {"u": u_hist, "d": d, "g": gid}, fetch=True)
            out_c = out_c_res[0][0] if out_c_res else 0
            history.append({"Date": d, "Bilan": in_c - out_c})
            total_in += in_c; total_out += out_c
        
        dfh = pd.DataFrame(history)
        m1, m2 = st.columns(2)
        m1.metric("Moyenne Consommée", f"{(total_in/31):.0f} kcal/j")
        m2.metric("Bilan Moyen", f"{((total_in - total_out)/31):.0f} kcal/j", delta_color="inverse")
        
        fig = go.Figure(go.Scatter(x=dfh['Date'], y=dfh['Bilan'], mode='lines+markers', fill='tozeroy'))
        fig.add_hline(y=0, line_dash="dash", line_color="green")
        st.plotly_chart(fig, use_container_width=True)

# --- 4. GESTION ---
with tabs[3]:
    st.header("🗄️ Gestion des données")
    table_choice = st.radio("Table :", ["Repas", "Dépenses"], horizontal=True)
    
    if table_choice == "Repas":
        data = run_query('SELECT id, date, "user", label, calories FROM meal_logs WHERE group_id=:g ORDER BY date DESC', {"g": gid}, fetch=True)
        df = pd.DataFrame(data, columns=["ID", "Date", "Utilisateur", "Label", "Kcal"])
    else:
        data = run_query('SELECT date, "user", depense FROM daily_spend WHERE group_id=:g ORDER BY date DESC', {"g": gid}, fetch=True)
        df = pd.DataFrame(data, columns=["Date", "Utilisateur", "Dépense"])
        
    edited = st.data_editor(df, num_rows="dynamic", use_container_width=True)
    if st.button("Sauvegarder les changements"):
        if table_choice == "Repas":
            run_query("DELETE FROM meal_logs WHERE group_id=:g", {"g": gid})
            for _, r in edited.iterrows():
                run_query('INSERT INTO meal_logs (id, date, "user", label, calories, group_id) VALUES (:id,:d,:u,:l,:c,:g)', 
                          {"id":r["ID"], "d":r["Date"], "u":r["Utilisateur"], "l":r["Label"], "c":r["Kcal"], "g":gid})
        else:
            run_query("DELETE FROM daily_spend WHERE group_id=:g", {"g": gid})
            for _, r in edited.iterrows():
                run_query('INSERT INTO daily_spend (date, "user", depense, group_id) VALUES (:d,:u,:dep,:g)', 
                          {"d":r["Date"], "u":r["Utilisateur"], "dep":r["Dépense"], "g":gid})
        st.success("Base mise à jour !")

# --- 5. PARAMÈTRES ---
with tabs[4]:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("👥 Membres du foyer")
        nu = st.text_input("Nouveau membre")
        if st.button("Ajouter"):
            run_query("INSERT INTO users (name, group_id) VALUES (:n, :g)", {"n": nu, "g": gid})
            st.rerun()
        u_to_del = st.selectbox("Supprimer membre", users)
        if st.button("🗑️ Supprimer membre"):
            run_query("DELETE FROM users WHERE name=:n AND group_id=:g", {"n": u_to_del, "g": gid})
            st.rerun()
    with c2:
        st.subheader("🥗 Bibliothèque")
        fn = st.text_input("Aliment")
        fc = st.number_input("Kcal/100g", 0)
        if st.button("Ajouter Aliment"):
            run_query("INSERT INTO foods (name, cal_100g) VALUES (:n, :c) ON CONFLICT (name) DO UPDATE SET cal_100g = EXCLUDED.cal_100g", {"n": fn, "c": fc})
            st.rerun()
        f_data = run_query("SELECT * FROM foods ORDER BY name", fetch=True)
        st.dataframe(pd.DataFrame(f_data, columns=["Nom", "Kcal"]), height=300)
