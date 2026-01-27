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

# --- 2. FONCTIONS DE BASE ---
def hash_pw(pw): return hashlib.sha256(pw.encode()).hexdigest()

def run_query(query_str, params=None, fetch=False):
    with conn.session as s:
        result = s.execute(text(query_str), params)
        if fetch: return result.fetchall()
        s.commit()

def init_db():
    with conn.session as s:
        s.execute(text('CREATE TABLE IF NOT EXISTS accounts (group_id TEXT PRIMARY KEY, password TEXT)'))
        s.execute(text('CREATE TABLE IF NOT EXISTS users (name TEXT, group_id TEXT, PRIMARY KEY(name, group_id))'))
        s.execute(text('CREATE TABLE IF NOT EXISTS foods (name TEXT PRIMARY KEY, cal_100g REAL)'))
        s.execute(text('CREATE TABLE IF NOT EXISTS meal_logs (id SERIAL PRIMARY KEY, date DATE, label TEXT, "user" TEXT, calories REAL, group_id TEXT)'))
        s.execute(text('CREATE TABLE IF NOT EXISTS daily_spend (date DATE, "user" TEXT, depense REAL, group_id TEXT, PRIMARY KEY (date, "user", group_id))'))
        
        # Injection des ingrédients de base si vide
        check = s.execute(text("SELECT COUNT(*) FROM foods")).fetchone()
        if check[0] < 10:
            aliments = [('Poulet (Blanc)', 165), ('Riz cuit', 130), ('Pâtes cuites', 150), ('Œuf (unité)', 155), 
                        ('Avocat', 160), ('Pomme', 52), ('Pain Baguette', 250), ('Beurre', 717), ('Huile d\'olive', 884)]
            for n, c in aliments:
                s.execute(text("INSERT INTO foods VALUES (:n, :c) ON CONFLICT DO NOTHING"), {"n": n, "c": c})
        s.commit()

def analyze_meal_ia(image, info=""):
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"""Analyse ce repas. Info: {info}. 
        Réponds UNIQUEMENT en JSON strict avec cette structure:
        {{ "plat": "Nom du plat", "composition": [
            {{"ingredient": "Nom", "poids_g": 150, "kcal_100g": 165}}
        ] }}"""
        response = model.generate_content([prompt, image])
        match = re.search(r'\{.*\}', response.text, re.DOTALL)
        return json.loads(match.group()) if match else None
    except: return None

# --- 3. CONNEXION & COOKIES ---
init_db()
if 'logged_in' not in st.session_state: st.session_state.logged_in = False

cookie_foyer = controller.get('saved_group_id')
if cookie_foyer and not st.session_state.logged_in:
    st.session_state.logged_in, st.session_state.group_id = True, cookie_foyer

if not st.session_state.logged_in:
    st.title("🍎 CaloTrack Pro")
    choice = st.radio("Action", ["Connexion", "Nouveau Foyer"], horizontal=True)
    g_id = st.text_input("Foyer")
    pw = st.text_input("Mot de passe", type="password")
    rem = st.checkbox("Rester connecté")
    if st.button("Valider"):
        if choice == "Connexion":
            res = run_query("SELECT password FROM accounts WHERE group_id=:g", {"g": g_id}, fetch=True)
            if res and res[0][0] == hash_pw(pw):
                st.session_state.logged_in, st.session_state.group_id = True, g_id
                if rem: controller.set('saved_group_id', g_id)
                st.rerun()
            else: st.error("Erreur.")
        else:
            run_query("INSERT INTO accounts VALUES (:g, :p)", {"g": g_id, "p": hash_pw(pw)})
            st.success("Foyer créé !")
    st.stop()

# --- 4. APP PRINCIPALE ---
gid = st.session_state.group_id
users = [r[0] for r in run_query("SELECT name FROM users WHERE group_id=:g", {"g": gid}, fetch=True)]

st.sidebar.title(f"🏠 {gid}")
if st.sidebar.button("Déconnexion"):
    controller.remove('saved_group_id'); st.session_state.logged_in = False; st.rerun()

tabs = st.tabs(["🍽️ Nouveau Repas", "🏠 Bilan", "📈 Historique", "🗄️ Gestion", "⚙️ Paramètres"])

# --- ONGLET REPAS (MANUEL + IA DÉCOMPOSÉE) ---
with tabs[0]:
    if not users: st.warning("Ajoutez des membres dans Paramètres.")
    else:
        method = st.radio("Méthode", ["⚖️ Manuel", "📸 Photo IA"], horizontal=True)
        final_label, final_cal = "Repas", 0.0

        if method == "⚖️ Manuel":
            f_dict = {r[0]: r[1] for r in run_query("SELECT * FROM foods", fetch=True)}
            final_label = st.text_input("Nom", "Déjeuner")
            n = st.number_input("Ingrédients", 1, 10, 1)
            for i in range(n):
                c1, c2 = st.columns(2)
                f = c1.selectbox(f"Aliment {i}", sorted(f_dict.keys()), key=f"f{i}")
                p = c2.number_input("Poids (g)", 0, key=f"p{i}")
                final_cal += (f_dict[f] * p) / 100
        else:
            img = st.file_uploader("Photo", type=['jpg','png'])
            if img and st.button("🔍 Analyser l'assiette"):
                res = analyze_meal_ia(Image.open(img))
                if res: st.session_state.ia_res = res
            
            if 'ia_res' in st.session_state:
                st.session_state.ia_res['plat'] = st.text_input("Plat", st.session_state.ia_res['plat'])
                df_ia = pd.DataFrame(st.session_state.ia_res['composition'])
                st.info("💡 Tu peux modifier les noms, les poids ou les kcal/100g directement dans le tableau ci-dessous avant de valider.")
                edited_ia = st.data_editor(df_ia, num_rows="dynamic", use_container_width=True)
                # Calcul dynamique
                final_label = st.session_state.ia_res['plat']
                final_cal = sum((r['poids_g'] * r['kcal_100g'] / 100) for _, r in edited_ia.iterrows())
                st.metric("Total estimé", f"{final_cal:.0f} kcal")

        st.divider()
        shares = {}
        cols = st.columns(len(users))
        for i, u in enumerate(users):
            with cols[i]:
                pct = st.slider(f"{u} (%)", 0, 100, 100//len(users), key=f"s{u}")
                shares[u] = (final_cal * pct / 100)
    
        if st.button("🚀 Enregistrer"):
            if final_cal > 0:
                for u, c in shares.items():
                    run_query('INSERT INTO meal_logs (date, label, "user", calories, group_id) VALUES (:d,:l,:u,:c,:g)', 
                              {"d": date.today(), "l": final_label, "u": u, "c": c, "g": gid})
                
                st.success("Validé !")
                
                # Suppression sécurisée des données temporaires de l'IA
                if 'ia_res' in st.session_state:
                    del st.session_state['ia_res']
                
                st.rerun()
            else:
                st.error("Le total des calories doit être supérieur à 0.")
                
# --- ONGLET GESTION & PARAMÈTRES (MODIF/SUPPR) ---
with tabs[3]: # Gestion des logs
    st.subheader("Logs des repas")
    data = run_query('SELECT id, date, "user", label, calories FROM meal_logs WHERE group_id=:g ORDER BY date DESC', {"g": gid}, fetch=True)
    df_logs = pd.DataFrame(data, columns=["ID", "Date", "User", "Label", "Kcal"])
    ed_logs = st.data_editor(df_logs, num_rows="dynamic", use_container_width=True, hide_index=True)
    if st.button("💾 Sauver Logs"):
        run_query("DELETE FROM meal_logs WHERE group_id=:g", {"g": gid})
        for _, r in ed_logs.iterrows():
            run_query('INSERT INTO meal_logs (date,label,"user",calories,group_id) VALUES (:d,:l,:u,:c,:g)', 
                      {"d":r["Date"],"l":r["Label"],"u":r["User"],"c":r["Kcal"],"g":gid})
        st.rerun()

with tabs[4]: # Paramètres & Bibliothèque
    st.subheader("👥 Membres")
    nu = st.text_input("Nouveau membre")
    if st.button("Ajouter"):
        run_query("INSERT INTO users VALUES (:n, :g)", {"n": nu, "g": gid}); st.rerun()
    
    st.divider()
    st.subheader("🥗 Bibliothèque (Modifier/Supprimer)")
    f_data = run_query("SELECT name, cal_100g FROM foods ORDER BY name", fetch=True)
    df_f = pd.DataFrame(f_data, columns=["Nom", "Kcal_100g"])
    ed_f = st.data_editor(df_f, num_rows="dynamic", use_container_width=True, hide_index=True)
    if st.button("💾 Sauver Bibliothèque"):
        run_query("DELETE FROM foods")
        for _, r in ed_f.iterrows():
            run_query("INSERT INTO foods VALUES (:n, :c) ON CONFLICT DO NOTHING", {"n":r["Nom"], "c":r["Kcal_100g"]})
        st.success("Base mise à jour !"); st.rerun()

# --- BILAN & HISTORIQUE (Ancienne version) ---
with tabs[1]:
    for u in users:
        c = run_query('SELECT SUM(calories) FROM meal_logs WHERE "user"=:u AND date=:d AND group_id=:g', {"u":u,"d":date.today(),"g":gid}, fetch=True)[0][0] or 0
        st.metric(f"Total {u}", f"{c:.0f} kcal")
