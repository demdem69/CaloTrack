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


# --- 1. CONFIGURATION & SERVICES ---
controller = CookieController()
conn = st.connection("postgresql", type="sql")

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def run_query(query_str, params=None, fetch=False):
    with conn.session as s:
        result = s.execute(text(query_str), params)
        if fetch: return result.fetchall()
        s.commit()

def init_db():
    with conn.session as s:
        # 1. Création des tables si elles n'existent pas
        s.execute(text('CREATE TABLE IF NOT EXISTS accounts (group_id TEXT PRIMARY KEY, password TEXT)'))
        s.execute(text('CREATE TABLE IF NOT EXISTS users (name TEXT, group_id TEXT, PRIMARY KEY(name, group_id))'))
        s.execute(text('CREATE TABLE IF NOT EXISTS foods (name TEXT PRIMARY KEY, cal_100g REAL)'))
        s.execute(text('CREATE TABLE IF NOT EXISTS meal_logs (id SERIAL PRIMARY KEY, date DATE, label TEXT, "user" TEXT, calories REAL, group_id TEXT)'))
        s.execute(text('CREATE TABLE IF NOT EXISTS daily_spend (date DATE, "user" TEXT, depense REAL, group_id TEXT, PRIMARY KEY (date, "user", group_id))'))
        
        # 2. Vérification si la table foods est vide
        check = s.execute(text("SELECT COUNT(*) FROM foods")).fetchone()
        
        
            # Liste des 100 ingrédients à injecter
        aliments = [
                # Protéines
                ('Poulet (Blanc)', 165), ('Poulet (Cuisse)', 210), ('Dinde (Filet)', 110),
                ('Bœuf (Steak 5%)', 125), ('Bœuf (Steak 15%)', 215), ('Porc (Filet)', 145),
                ('Jambon blanc', 110), ('Œuf (unité)', 155), ('Saumon', 208),
                ('Thon au naturel', 116), ('Cabillaud', 82), ('Crevettes', 99),
                ('Colin', 75), ('Sardines (huile)', 208), ('Tofu', 76),
                # Féculents (Cuit)
                ('Riz blanc cuit', 130), ('Riz complet cuit', 110), ('Pâtes cuites', 150),
                ('Quinoa cuit', 120), ('Semoule cuite', 112), ('Boulghour cuit', 83),
                ('Pomme de terre vapeur', 77), ('Patate douce', 86), ('Pain Baguette', 250),
                ('Pain Complet', 247), ('Pain de mie', 280), ('Biscotte', 400),
                ('Flocons d\'avoine', 370), ('Maïs', 96), ('Lentilles cuites', 116),
                ('Pois chiches cuits', 164), ('Haricots rouges cuits', 127),
                # Légumes
                ('Haricots verts', 31), ('Brocoli', 34), ('Carotte', 41),
                ('Courgette', 17), ('Épinards', 23), ('Chou-fleur', 25),
                ('Aubergine', 25), ('Poivron', 30), ('Tomate', 18),
                ('Concombre', 15), ('Salade verte', 15), ('Champignons', 22),
                ('Oignon', 40), ('Petit pois', 81), ('Asperges', 20), ('Poireau', 61),
                # Fruits
                ('Pomme', 52), ('Banane', 89), ('Poire', 57), ('Orange', 47),
                ('Clémentine', 47), ('Fraise', 33), ('Framboise', 52),
                ('Myrtilles', 57), ('Raisin', 67), ('Kiwi', 61),
                ('Pêche', 39), ('Ananas', 50), ('Avocat', 160),
                ('Melon', 34), ('Pastèque', 30), ('Abricot', 48),
                # Produits Laitiers
                ('Lait demi-écrémé', 46), ('Lait entier', 60), ('Yaourt nature', 63),
                ('Fromage blanc 0%', 48), ('Fromage blanc 3%', 75), ('Emmental', 380),
                ('Camembert', 265), ('Mozzarella', 280), ('Feta', 264),
                ('Parmesan', 431), ('Beurre', 717), ('Crème fraîche 30%', 290),
                # Matières Grasses & Snacks
                ('Huile d\'olive', 884), ('Huile de tournesol', 884), ('Mayonnaise', 680),
                ('Ketchup', 110), ('Moutarde', 66), ('Noix', 654),
                ('Amandes', 579), ('Beurre de cacahuète', 588),
                ('Chocolat Noir 70%', 546), ('Chocolat au lait', 535), ('Biscuit sablé', 450),
                ('Croissant', 400), ('Pain au chocolat', 400), ('Pizza Margherita', 260),
                ('Burger (classique)', 295), ('Frites', 312), ('Chips', 536),
                ('Glace vanille', 207), ('Miel', 304), ('Sucre', 387),
                # Boissons
                ('Café noir', 1), ('Thé', 1), ('Jus d\'orange', 45), ('Soda (Cola)', 42),
                ('Vin rouge', 85), ('Bière', 43), ('Eau', 0)
            ]
            # Boucle 
    
        for n, c in aliments:
            s.execute(text("INSERT INTO foods (name, cal_100g) VALUES (:n, :c) ON CONFLICT (name) DO NOTHING"), {"n": n, "c": c})
        
        s.commit()

def analyze_meal_ia(image, info=""):
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"Analyse cette image. Info: {info}. Réponds UNIQUEMENT en JSON: {{\"label\": \"Nom\", \"calories\": 450}}"
        response = model.generate_content([prompt, image])
        match = re.search(r'\{.*\}', response.text, re.DOTALL)
        return json.loads(match.group()) if match else None
    except: return None

# --- 2. LOGIQUE DE CONNEXION (AVEC COOKIES) ---
st.set_page_config(page_title="CaloTrack Pro Cloud", layout="wide")
init_db()

if 'logged_in' not in st.session_state: st.session_state.logged_in = False

# Vérification du cookie au chargement
cookie_foyer = controller.get('saved_group_id')
if cookie_foyer and not st.session_state.logged_in:
    st.session_state.logged_in = True
    st.session_state.group_id = cookie_foyer

if not st.session_state.logged_in:
    st.title("🍎 CaloTrack Pro")
    tab_log, tab_reg = st.tabs(["🔑 Connexion", "📝 Créer un Foyer"])
    
    with tab_log:
        g_id = st.text_input("Nom du Foyer")
        pw = st.text_input("Mot de passe", type="password")
        remember = st.checkbox("Rester connecté (30 jours)")
        if st.button("Se connecter"):
            res = run_query("SELECT password FROM accounts WHERE group_id=:g", {"g": g_id}, fetch=True)
            if res and res[0][0] == hash_pw(pw):
                st.session_state.logged_in, st.session_state.group_id = True, g_id
                if remember: controller.set('saved_group_id', g_id)
                st.rerun()
            else: st.error("Identifiants incorrects.")
    
    with tab_reg:
        new_g = st.text_input("Nom du nouveau Foyer")
        new_pw = st.text_input("Nouveau Mot de passe", type="password")
        if st.button("Créer le compte"):
            try:
                run_query("INSERT INTO accounts VALUES (:g, :p)", {"g": new_g, "p": hash_pw(new_pw)})
                st.success("Foyer créé ! Connectez-vous.")
            except: st.error("Ce nom est déjà pris.")
    st.stop()

# --- 3. APPLICATION PRINCIPALE ---
gid = st.session_state.group_id
users = [r[0] for r in run_query("SELECT name FROM users WHERE group_id=:g", {"g": gid}, fetch=True)]

st.sidebar.subheader(f"🏠 Foyer : {gid}")
if st.sidebar.button("Se déconnecter"):
    controller.remove('saved_group_id')
    st.session_state.logged_in = False
    st.rerun()

tabs = st.tabs(["🍽️ Nouveau Repas", "🏠 Bilan du Jour", "📈 Historique Mensuel", "🗄️ Gestion", "⚙️ Paramètres"])

# --- ONGLET 1 : NOUVEAU REPAS ---
with tabs[0]:
    if not users: st.warning("Allez dans 'Paramètres' pour ajouter des membres.")
    else:
        method = st.radio("Méthode d'ajout :", ["⚖️ Pesée manuelle", "📸 Photo IA"], horizontal=True)
        final_label, final_cal = "Repas", 0.0

        if method == "⚖️ Pesée manuelle":
            f_dict = {r[0]: r[1] for r in run_query("SELECT * FROM foods", fetch=True)}
            final_label = st.text_input("Nom du repas", "Déjeuner")
            n_ing = st.number_input("Ingrédients", 1, 15, 1)
            for i in range(n_ing):
                c1, c2 = st.columns(2)
                f = c1.selectbox(f"Aliment {i}", sorted(f_dict.keys()), key=f"f_{i}")
                p = c2.number_input("Poids (g)", 0, key=f"p_{i}")
                final_cal += (f_dict[f] * p) / 100
        else:
            img = st.file_uploader("Prendre une photo", type=['jpg', 'jpeg', 'png'])
            txt = st.text_input("Précisions pour l'IA")
            if img and st.button("Analyser"):
                with st.spinner("L'IA calcule..."):
                    res = analyze_meal_ia(Image.open(img), txt)
                    if res: st.session_state.ia_res = res
            if 'ia_res' in st.session_state:
                final_label = st.text_input("Plat détecté", st.session_state.ia_res['label'])
                final_cal = st.number_input("Kcal estimées", value=float(st.session_state.ia_res['calories']))

        st.divider()
        shares = {}
        u_cols = st.columns(len(users))
        for i, u in enumerate(users):
            with u_cols[i]:
                s = st.slider(f"{u} (%)", 0, 100, 100//len(users), key=f"s_{u}")
                ex = st.number_input(f"Extras {u}", 0, key=f"ex_{u}")
                shares[u] = (final_cal * s / 100) + ex
        
        if st.button("🚀 Valider et Enregistrer"):
            for u, cal in shares.items():
                run_query('INSERT INTO meal_logs (date, label, "user", calories, group_id) VALUES (:d,:l,:u,:c,:g)', 
                          {"d": date.today(), "l": final_label, "u": u, "c": cal, "g": gid})
            st.success("Repas enregistré !")
            if 'ia_res' in st.session_state: del st.session_state.ia_res

# --- ONGLET 2 : BILAN DU JOUR ---
with tabs[1]:
    tday = date.today()
    for u in users:
        with st.expander(f"👤 {u}", expanded=True):
            in_cal = run_query('SELECT SUM(calories) FROM meal_logs WHERE "user"=:u AND date=:d AND group_id=:g', {"u": u, "d": tday, "g": gid}, fetch=True)[0][0] or 0
            res_d = run_query('SELECT depense FROM daily_spend WHERE date=:d AND "user"=:u AND group_id=:g', {"d": tday, "u": u, "g": gid}, fetch=True)
            cur_dep = res_d[0][0] if res_d else 2000.0
            c1, c2, c3 = st.columns(3)
            c1.metric("Mangé", f"{in_cal:.0f} kcal")
            new_dep = c2.number_input(f"Dépense cible ({u})", value=float(cur_dep), key=f"dep_{u}")
            if new_dep != cur_dep:
                run_query('INSERT INTO daily_spend (date, "user", depense, group_id) VALUES (:d,:u,:dep,:g) ON CONFLICT (date,"user",group_id) DO UPDATE SET depense=EXCLUDED.depense', {"d":tday,"u":u,"dep":new_dep,"g":gid})
                st.rerun()
            c3.metric("Bilan", f"{in_cal - new_dep:.0f} kcal", delta=-(in_cal-new_dep), delta_color="inverse")

# --- ONGLET 3 : HISTORIQUE ---
with tabs[2]:
    if users:
        u_h = st.selectbox("Historique de :", users)
        hist = []
        for i in range(30, -1, -1):
            d = date.today() - timedelta(days=i)
            inc = run_query('SELECT SUM(calories) FROM meal_logs WHERE "user"=:u AND date=:d AND group_id=:g', {"u":u_h,"d":d,"g":gid}, fetch=True)[0][0] or 0
            outc = run_query('SELECT depense FROM daily_spend WHERE "user"=:u AND date=:d AND group_id=:g', {"u":u_h,"d":d,"g":gid}, fetch=True)
            outc = outc[0][0] if outc else 2000
            hist.append({"Date": d, "Bilan": inc - outc})
        dfh = pd.DataFrame(hist)
        st.plotly_chart(go.Figure(go.Scatter(x=dfh['Date'], y=dfh['Bilan'], fill='tozeroy')), use_container_width=True)

# --- ONGLET 4 : GESTION ---
with tabs[3]:
    st.header("🗄️ Gestion")
    table_choice = st.radio("Table :", ["Repas", "Dépenses"], horizontal=True)
    if table_choice == "Repas":
        data = run_query('SELECT id, date, "user", label, calories FROM meal_logs WHERE group_id=:g ORDER BY date DESC', {"g": gid}, fetch=True)
        df = pd.DataFrame(data, columns=["ID", "Date", "Utilisateur", "Label", "Kcal"])
        edited = st.data_editor(df, num_rows="dynamic", use_container_width=True, hide_index=True)
        if st.button("💾 Sauvegarder Repas"):
            run_query("DELETE FROM meal_logs WHERE group_id=:g", {"g": gid})
            for _, r in edited.iterrows():
                run_query('INSERT INTO meal_logs (date,label,"user",calories,group_id) VALUES (:d,:l,:u,:c,:g)', {"d":r["Date"],"l":r["Label"],"u":r["Utilisateur"],"c":r["Kcal"],"g":gid})
            st.rerun()
    else:
        data = run_query('SELECT date, "user", depense FROM daily_spend WHERE group_id=:g ORDER BY date DESC', {"g": gid}, fetch=True)
        df = pd.DataFrame(data, columns=["Date", "Utilisateur", "Dépense"])
        edited = st.data_editor(df, num_rows="dynamic", use_container_width=True, hide_index=True)
        if st.button("💾 Sauvegarder Dépenses"):
            run_query("DELETE FROM daily_spend WHERE group_id=:g", {"g": gid})
            for _, r in edited.iterrows():
                run_query('INSERT INTO daily_spend (date,"user",depense,group_id) VALUES (:d,:u,:dep,:g)', {"d":r["Date"],"u":r["Utilisateur"],"dep":r["Dépense"],"g":gid})
            st.rerun()

# --- ONGLET 5 : PARAMÈTRES ---
with tabs[4]:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("👥 Membres")
        nu = st.text_input("Nouveau membre")
        if st.button("Ajouter Membre"):
            run_query("INSERT INTO users VALUES (:n, :g)", {"n": nu, "g": gid}); st.rerun()
        u_del = st.selectbox("Supprimer", users)
        if st.button("🗑️ Supprimer"):
            run_query("DELETE FROM users WHERE name=:n AND group_id=:g", {"n": u_del, "g": gid}); st.rerun()
    with c2:
        st.subheader("🥗 Bibliothèque")
        fn = st.text_input("Nouvel aliment")
        fc = st.number_input("Kcal/100g", 0)
        if st.button("Ajouter à la base"):
            run_query("INSERT INTO foods VALUES (:n,:c) ON CONFLICT (name) DO UPDATE SET cal_100g=EXCLUDED.cal_100g", {"n":fn,"c":fc})
            st.rerun()
        f_data = run_query("SELECT * FROM foods ORDER BY name", fetch=True)
        st.dataframe(pd.DataFrame(f_data, columns=["Nom", "Kcal"]), height=300)
