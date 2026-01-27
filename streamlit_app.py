import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import hashlib
from datetime import date, timedelta
from sqlalchemy import text
import google.generativeai as genai
from PIL import Image
import json
import re
from streamlit_cookies_controller import CookieController

# --- 1. CONFIGURATION & DESIGN ---
st.set_page_config(page_title="CaloTrack Pro", page_icon="🍏", layout="wide")
controller = CookieController()
conn = st.connection("postgresql", type="sql")

st.markdown("""
    <style>
    .stButton>button { background-color: #2ecc71; color: white; border-radius: 8px; border: none; font-weight: bold; height: 3em; width: 100%; }
    .stButton>button:hover { background-color: #27ae60; color: white; border: none; }
    .stTabs [aria-selected="true"] { background-color: #2ecc71 !important; color: white !important; border-radius: 5px; }
    [data-testid="stMetricValue"] { color: #2ecc71; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FONCTIONS TECHNIQUES ---
def hash_pw(pw): return hashlib.sha256(pw.encode()).hexdigest()

def run_query(query_str, params=None, fetch=False):
    with conn.session as s:
        result = s.execute(text(query_str), params)
        if fetch: return result.fetchall()
        s.commit()
        return None

def init_db():
    with conn.session as s:
        s.execute(text('CREATE TABLE IF NOT EXISTS accounts (group_id TEXT PRIMARY KEY, password TEXT)'))
        s.execute(text('CREATE TABLE IF NOT EXISTS users (name TEXT, group_id TEXT, PRIMARY KEY(name, group_id))'))
        s.execute(text('CREATE TABLE IF NOT EXISTS foods (name TEXT PRIMARY KEY, cal_100g REAL)'))
        s.execute(text('CREATE TABLE IF NOT EXISTS meal_logs (id SERIAL PRIMARY KEY, date DATE, label TEXT, "user" TEXT, calories REAL, group_id TEXT)'))
        s.commit()
        # Injection initiale sécurisée
        aliments = [('Poulet (Blanc)', 165), ('Riz cuit', 130), ('Pâtes cuites', 150), ('Œuf (unité)', 155), ('Avocat', 160)]
        for n, c in aliments:
            s.execute(text("INSERT INTO foods (name, cal_100g) VALUES (:n, :c) ON CONFLICT (name) DO NOTHING"), {"n": n, "c": c})
        s.commit()

def analyze_meal_ia(image, info=""):
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"Analyse ce repas. Info: {info}. Réponds UNIQUEMENT en JSON: {{'plat': 'Nom', 'composition': [{{'ingredient': 'Nom', 'poids_g': 100, 'kcal_100g': 150}}]}}"
        response = model.generate_content([prompt, image])
        match = re.search(r'\{.*\}', response.text, re.DOTALL)
        return json.loads(match.group().replace("'", '"')) if match else None
    except: return None

# --- 3. AUTHENTIFICATION ---
init_db()
if 'logged_in' not in st.session_state: st.session_state.logged_in = False

cookie_foyer = controller.get('saved_group_id')
if cookie_foyer and not st.session_state.logged_in:
    st.session_state.logged_in, st.session_state.group_id = True, cookie_foyer

if not st.session_state.logged_in:
    st.title("🍎 CaloTrack Pro")
    choice = st.radio("Action", ["Connexion", "Nouveau Foyer"], horizontal=True, key="auth_choice")
    g_id = st.text_input("Foyer", key="g_input")
    pw = st.text_input("Mot de passe", type="password", key="p_input")
    if st.button("Valider", key="auth_btn"):
        if choice == "Connexion":
            res = run_query("SELECT password FROM accounts WHERE group_id=:g", {"g": g_id}, fetch=True)
            if res and res[0][0] == hash_pw(pw):
                st.session_state.logged_in, st.session_state.group_id = True, g_id
                controller.set('saved_group_id', g_id)
                st.rerun()
        else:
            run_query("INSERT INTO accounts VALUES (:g, :p) ON CONFLICT DO NOTHING", {"g": g_id, "p": hash_pw(pw)})
            st.success("Foyer créé !")
    st.stop()

# --- 4. APP PRINCIPALE ---
gid = st.session_state.group_id
user_rows = run_query("SELECT name FROM users WHERE group_id=:g", {"g": gid}, fetch=True)
users = [r[0] for r in user_rows]

st.sidebar.title(f"🏠 {gid}")
if st.sidebar.button("Déconnexion", key="logout_btn"):
    controller.remove('saved_group_id'); st.session_state.logged_in = False; st.rerun()

tabs = st.tabs(["🍽️ Nouveau Repas", "🏠 Bilan", "📈 Historique", "🗄️ Logs", "⚙️ Paramètres"])

with tabs[0]: # REPAS
    if not users: st.warning("Ajoutez des membres dans Paramètres.")
    else:
        method = st.radio("Méthode", ["⚖️ Manuel", "📸 Photo IA"], horizontal=True, key="m_choice")
        final_label, final_cal = "Repas", 0.0
        if method == "⚖️ Manuel":
            f_dict = {r[0]: r[1] for r in run_query("SELECT * FROM foods", fetch=True)}
            final_label = st.text_input("Nom", "Déjeuner", key="lab_man")
            n_ing = st.number_input("Ingrédients", 1, 15, 1, key="n_man")
            for i in range(int(n_ing)):
                c1, c2 = st.columns(2)
                f = c1.selectbox(f"Aliment {i+1}", sorted(f_dict.keys()), key=f"f_{i}")
                p = c2.number_input("Poids (g)", 0, key=f"p_{i}")
                final_cal += (f_dict[f] * p) / 100
        else:
            img = st.file_uploader("Photo", type=['jpg','png'], key="ia_img")
            if img and st.button("🔍 Analyser", key="ia_btn"):
                res = analyze_meal_ia(Image.open(img))
                if res: st.session_state.ia_res = res
            if 'ia_res' in st.session_state:
                final_label = st.text_input("Plat", st.session_state.ia_res['plat'], key="ia_lab")
                df_ia = pd.DataFrame(st.session_state.ia_res['composition'])
                ed_ia = st.data_editor(df_ia, num_rows="dynamic", use_container_width=True, key="ia_ed")
                final_cal = sum((r['poids_g'] * r['kcal_100g'] / 100) for _, r in ed_ia.iterrows())
                st.metric("Total IA", f"{final_cal:.0f} kcal")

        st.divider()
        shares = {}
        cols = st.columns(len(users))
        for i, u in enumerate(users):
            with cols[i]:
                pct = st.slider(f"{u} (%)", 0, 100, 100//len(users), key=f"sl_{u}")
                shares[u] = (final_cal * pct / 100)
        if st.button("🚀 Enregistrer", key="save_repas"):
            for u, c in shares.items():
                run_query('INSERT INTO meal_logs (date, label, "user", calories, group_id) VALUES (:d,:l,:u,:c,:g)', 
                          {"d": date.today(), "l": final_label, "u": u, "c": c, "g": gid})
            if 'ia_res' in st.session_state: del st.session_state['ia_res']
            st.rerun()

with tabs[1]: # BILAN JOUR
    st.header(f"Bilan {date.today()}")
    for u in users:
        val = run_query('SELECT SUM(calories) FROM meal_logs WHERE "user"=:u AND date=:d AND group_id=:g', 
                        {"u":u,"d":date.today(),"g":gid}, fetch=True)[0][0] or 0
        st.metric(f"Total {u}", f"{val:.0f} kcal")

with tabs[2]: # HISTORIQUE 30J
    if users:
        u_h = st.selectbox("Utilisateur", users, key="h_sel")
        h_rows = []
        for i in range(30, -1, -1):
            d = date.today() - timedelta(days=i)
            v = run_query('SELECT SUM(calories) FROM meal_logs WHERE "user"=:u AND date=:d AND group_id=:g', 
                          {"u":u_h,"d":d,"g":gid}, fetch=True)[0][0] or 0
            h_rows.append({"Date": d, "Kcal": v})
        fig = go.Figure(go.Scatter(x=[x['Date'] for x in h_rows], y=[x['Kcal'] for x in h_rows], fill='tozeroy', line=dict(color='#2ecc71')))
        st.plotly_chart(fig, use_container_width=True)

with tabs[3]: # GESTION LOGS
    l_data = run_query('SELECT id, date, "user", label, calories FROM meal_logs WHERE group_id=:g ORDER BY date DESC', {"g": gid}, fetch=True)
    df_l = pd.DataFrame(l_data, columns=["ID", "Date", "User", "Label", "Kcal"])
    ed_l = st.data_editor(df_l, num_rows="dynamic", use_container_width=True, key="l_ed")
    if st.button("💾 Sauver Logs", key="s_l"):
        run_query("DELETE FROM meal_logs WHERE group_id=:g", {"g": gid})
        for _, r in ed_l.iterrows():
            run_query('INSERT INTO meal_logs (date, label, "user", calories, group_id) VALUES (:d,:l,:u,:c,:g)', 
                      {"d":r["Date"],"l":r["Label"],"u":r["User"],"c":r["Kcal"],"g":gid})
        st.rerun()

with tabs[4]: # PARAMÈTRES
    c1, c2 = st.columns([1, 2])
    with c1:
        nu = st.text_input("Nouveau membre", key="nu_in")
        if st.button("Ajouter", key="nu_bt"):
            run_query("INSERT INTO users VALUES (:n, :g) ON CONFLICT DO NOTHING", {"n": nu, "g": gid})
            st.rerun()
    with c2:
        f_rows = run_query("SELECT name, cal_100g FROM foods ORDER BY name", fetch=True)
        df_f = pd.DataFrame(f_rows, columns=["Nom", "Kcal_100g"])
        ed_f = st.data_editor(df_f, num_rows="dynamic", use_container_width=True, key="f_ed")
        if st.button("💾 Sauver Bibliothèque", key="s_f"):
            run_query("DELETE FROM foods")
            for _, r in ed_f.iterrows():
                run_query("INSERT INTO foods VALUES (:n, :c) ON CONFLICT DO NOTHING", {"n":r["Nom"], "c":r["Kcal_100g"]})
            st.rerun()    with conn.session as s:
        s.execute(text('CREATE TABLE IF NOT EXISTS accounts (group_id TEXT PRIMARY KEY, password TEXT)'))
        s.execute(text('CREATE TABLE IF NOT EXISTS users (name TEXT, group_id TEXT, PRIMARY KEY(name, group_id))'))
        s.execute(text('CREATE TABLE IF NOT EXISTS foods (name TEXT PRIMARY KEY, cal_100g REAL)'))
        s.execute(text('CREATE TABLE IF NOT EXISTS meal_logs (id SERIAL PRIMARY KEY, date DATE, label TEXT, "user" TEXT, calories REAL, group_id TEXT)'))
        s.execute(text('CREATE TABLE IF NOT EXISTS daily_spend (date DATE, "user" TEXT, depense REAL, group_id TEXT, PRIMARY KEY (date, "user", group_id))'))
        
        aliments = [('Poulet (Blanc)', 165), ('Riz cuit', 130), ('Pâtes cuites', 150), ('Œuf (unité)', 155), 
                    ('Avocat', 160), ('Pomme', 52), ('Pain Baguette', 250), ('Beurre', 717), ('Huile d\'olive', 884)]
        for n, c in aliments:
            s.execute(text("INSERT INTO foods (name, cal_100g) VALUES (:name, :cal) ON CONFLICT (name) DO NOTHING"), {"name": n, "cal": c})
        s.commit()

def analyze_meal_ia(image, info=""):
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"""Analyse ce repas. Info supplémentaire: {info}. 
        Réponds UNIQUEMENT en JSON strict avec cette structure:
        {{ "plat": "Nom du plat", "composition": [
            {{"ingredient": "Nom de l'aliment", "poids_g": 150, "kcal_100g": 165}}
        ] }}"""
        response = model.generate_content([prompt, image])
        match = re.search(r'\{.*\}', response.text, re.DOTALL)
        return json.loads(match.group()) if match else None
    except: return None

# --- 3. GESTION SESSION & COOKIES ---
init_db()
if 'logged_in' not in st.session_state: st.session_state.logged_in = False

cookie_foyer = controller.get('saved_group_id')
if cookie_foyer and not st.session_state.logged_in:
    st.session_state.logged_in, st.session_state.group_id = True, cookie_foyer

if not st.session_state.logged_in:
    st.title("🍎 CaloTrack Pro")
    choice = st.radio("Action", ["Connexion", "Nouveau Foyer"], horizontal=True)
    g_id = st.text_input("Nom du Foyer", key="auth_group_id")
    pw = st.text_input("Mot de passe", type="password", key="auth_password")
    rem = st.checkbox("Rester connecté (30 jours)", key="auth_remember")
    if st.button("Valider", key="auth_submit"):
        if choice == "Connexion":
            res = run_query("SELECT password FROM accounts WHERE group_id=:g", {"g": g_id}, fetch=True)
            if res and res[0][0] == hash_pw(pw):
                st.session_state.logged_in, st.session_state.group_id = True, g_id
                if rem: controller.set('saved_group_id', g_id)
                st.rerun()
            else: st.error("Identifiants incorrects.")
        else:
            try:
                run_query("INSERT INTO accounts VALUES (:g, :p)", {"g": g_id, "p": hash_pw(pw)})
                st.success("Foyer créé ! Connectez-vous.")
            except: st.error("Ce nom de foyer existe déjà.")
    st.stop()

# --- 4. INTERFACE PRINCIPALE ---
gid = st.session_state.group_id
users = [r[0] for r in run_query("SELECT name FROM users WHERE group_id=:g", {"g": gid}, fetch=True)]

st.sidebar.title(f"🏠 {gid}")
if st.sidebar.button("Se déconnecter", key="sidebar_logout"):
    controller.remove('saved_group_id'); st.session_state.logged_in = False; st.rerun()

tabs = st.tabs(["🍽️ Nouveau Repas", "🏠 Bilan Journée", "📈 Historique", "🗄️ Gestion Logs", "⚙️ Paramètres"])

# --- ONGLET 0 : NOUVEAU REPAS ---
with tabs[0]:
    if not users: st.warning("Veuillez ajouter des membres dans l'onglet Paramètres.")
    else:
        method = st.radio("Méthode de saisie", ["⚖️ Manuel", "📸 Photo IA"], horizontal=True, key="meal_method_choice")
        final_label, final_cal = "Repas", 0.0

        if method == "⚖️ Manuel":
            f_dict = {r[0]: r[1] for r in run_query("SELECT * FROM foods", fetch=True)}
            final_label = st.text_input("Nom du repas", "Déjeuner", key="manual_meal_label")
            n_ing = st.number_input("Nombre d'ingrédients", 1, 15, 1, key="manual_ing_count")
            for i in range(n_ing):
                c1, c2 = st.columns(2)
                f = c1.selectbox(f"Aliment {i+1}", sorted(f_dict.keys()), key=f"man_f_{i}")
                p = c2.number_input("Poids (g)", 0, key=f"man_p_{i}")
                final_cal += (f_dict[f] * p) / 100
        else:
            img = st.file_uploader("Photo de l'assiette", type=['jpg', 'jpeg', 'png'], key="ia_image_uploader")
            txt_ia = st.text_input("Précisions pour l'IA", key="ia_text_input")
            if img and st.button("🔍 Analyser avec l'IA", key="ia_analyze_button"):
                with st.spinner("L'IA décompose le repas..."):
                    res_ia = analyze_meal_ia(Image.open(img), txt_ia)
                    if res_ia: st.session_state.ia_res = res_ia
            
            if 'ia_res' in st.session_state:
                st.info("💡 Modifiez les ingrédients, poids ou kcal ci-dessous si besoin.")
                final_label = st.text_input("Nom du plat détecté", st.session_state.ia_res['plat'], key="ia_meal_label_edit")
                df_ia = pd.DataFrame(st.session_state.ia_res['composition'])
                edited_ia = st.data_editor(df_ia, num_rows="dynamic", use_container_width=True, hide_index=True, key="ia_editor")
                final_cal = sum((row['poids_g'] * row['kcal_100g'] / 100) for _, row in edited_ia.iterrows())
                st.metric("Total estimé", f"{final_cal:.0f} kcal")

        st.divider()
        st.subheader("Qui a mangé ?")
        shares = {}
        cols = st.columns(len(users))
        for i, u in enumerate(users):
            with cols[i]:
                pct = st.slider(f"{u} (%)", 0, 100, 100//len(users), key=f"slider_user_{u}")
                shares[u] = (final_cal * pct / 100)
        
        if st.button("🚀 Enregistrer le repas", key="save_meal_final"):
            if final_cal > 0:
                for u, c in shares.items():
                    run_query('INSERT INTO meal_logs (date, label, "user", calories, group_id) VALUES (:d,:l,:u,:c,:g)', 
                              {"d": date.today(), "l": final_label, "u": u, "c": c, "g": gid})
                st.success("Repas enregistré !")
                if 'ia_res' in st.session_state: del st.session_state['ia_res']
                st.rerun()
            else: st.error("Ajoutez des calories avant de valider.")

# --- ONGLET 3 : GESTION DES LOGS ---
with tabs[3]:
    st.subheader("Historique des entrées")
    data_logs = run_query('SELECT id, date, "user", label, calories FROM meal_logs WHERE group_id=:g ORDER BY date DESC', {"g": gid}, fetch=True)
    df_logs = pd.DataFrame(data_logs, columns=["ID", "Date", "Utilisateur", "Plat", "Kcal"])
    ed_logs = st.data_editor(df_logs, num_rows="dynamic", use_container_width=True, hide_index=True, key="logs_table_editor")
    if st.button("💾 Appliquer les modifications aux logs", key="save_logs_button"):
        run_query("DELETE FROM meal_logs WHERE group_id=:g", {"g": gid})
        for _, r in ed_logs.iterrows():
            run_query('INSERT INTO meal_logs (date, label, "user", calories, group_id) VALUES (:d,:l,:u,:c,:g)', 
                      {"d":r["Date"],"l":r["Plat"],"u":r["Utilisateur"],"c":r["Kcal"],"g":gid})
        st.success("Logs mis à jour !"); st.rerun()

# --- ONGLET 4 : PARAMÈTRES & BIBLIOTHÈQUE ---
with tabs[4]:
    c1, c2 = st.columns([1, 2])
    with c1:
        st.subheader("👥 Foyer")
        nu = st.text_input("Nom du membre", key="new_user_name")
        if st.button("Ajouter au foyer", key="add_user_button"):
            if nu:
                run_query("INSERT INTO users (name, group_id) VALUES (:n, :g) ON CONFLICT DO NOTHING", {"n": nu, "g": gid})
                st.rerun()
    
    with c2:
        st.subheader("🥗 Bibliothèque d'Aliments")
        f_data = run_query("SELECT name, cal_100g FROM foods ORDER BY name", fetch=True)
        df_f = pd.DataFrame(f_data, columns=["Nom", "Kcal_100g"])
        ed_f = st.data_editor(df_f, num_rows="dynamic", use_container_width=True, hide_index=True, key="foods_table_editor")
        if st.button("💾 Sauvegarder la Bibliothèque", key="save_foods_button"):
            run_query("DELETE FROM foods")
            for _, r in ed_f.iterrows():
                run_query("INSERT INTO foods (name, cal_100g) VALUES (:name, :cal) ON CONFLICT DO NOTHING", {"name":r["Nom"], "cal":r["Kcal_100g"]})
            st.success("Aliments mis à jour !"); st.rerun()

# --- BILAN (ONGLET 1) ---
with tabs[1]:
    st.header(f"Bilan du {date.today().strftime('%d/%m')}")
    for u in users:
        c = run_query('SELECT SUM(calories) FROM meal_logs WHERE "user"=:u AND date=:d AND group_id=:g', {"u":u,"d":date.today(),"g":gid}, fetch=True)[0][0] or 0
        st.metric(f"Consommation {u}", f"{c:.0f} kcal")
