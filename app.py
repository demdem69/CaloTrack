import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sqlite3
from datetime import date, timedelta

# --- CONFIGURATION DB ---
DB_NAME = "calories_v6.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (name TEXT PRIMARY KEY)')
    c.execute('CREATE TABLE IF NOT EXISTS foods (name TEXT PRIMARY KEY, cal_100g REAL)')
    c.execute('''CREATE TABLE IF NOT EXISTS meal_logs 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, label TEXT, user TEXT, calories REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS daily_spend 
                 (date TEXT, user TEXT, depense REAL, PRIMARY KEY (date, user))''')
    
    c.execute("SELECT COUNT(*) FROM foods")
    if c.fetchone()[0] == 0:
        base_foods = [
            # Protéines (Viandes, Poissons, Œufs)
    ('Poulet (Blanc)', 165), ('Poulet (Cuisse)', 210), ('Dinde (Filet)', 110),
    ('Bœuf (Steak 5%)', 125), ('Bœuf (Steak 15%)', 215), ('Porc (Filet)', 145),
    ('Jambon blanc', 110), ('Œuf (unité)', 155), ('Saumon', 208),
    ('Thon au naturel', 116), ('Cabillaud', 82), ('Crevettes', 99),
    ('Colin', 75), ('Sardines (huile)', 208), ('Tofu', 76),
    
    # Féculents et Céréales (Cuit)
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
    
    # Matières Grasses et Condiments
    ('Huile d\'olive', 884), ('Huile de tournesol', 884), ('Mayonnaise', 680),
    ('Ketchup', 110), ('Moutarde', 66), ('Noix', 654),
    ('Amandes', 579), ('Beurre de cacahuète', 588),
    
    # Plaisirs et Snack
    ('Chocolat Noir 70%', 546), ('Chocolat au lait', 535), ('Biscuit sablé', 450),
    ('Croissant', 400), ('Pain au chocolat', 400), ('Pizza Margherita', 260),
    ('Burger (classique)', 295), ('Frites', 312), ('Chips', 536),
    ('Glace vanille', 207), ('Miel', 304), ('Sucre', 387),
    
    # Boissons
    ('Café noir', 1), ('Thé', 1), ('Jus d\'orange', 45), ('Soda (Cola)', 42),
    ('Vin rouge', 85), ('Bière', 43), ('Eau', 0)
        ]
        c.executemany("INSERT INTO foods VALUES (?, ?)", base_foods)
    conn.commit()
    conn.close()

def run_query(query, params=(), fetch=False):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        if fetch: return cursor.fetchall()

# --- INTERFACE ---
st.set_page_config(page_title="CaloTrack Pro", layout="wide")
init_db()

st.title("🍎 CaloTrack Pro")
users = [r[0] for r in run_query("SELECT name FROM users", fetch=True)]

tabs = st.tabs(["🍽️ Nouveau Repas", "🏠 Bilan du Jour", "📈 Historique Mensuel", "🗄️ Gestion", "⚙️ Paramètres"])

# --- 1. NOUVEAU REPAS ---
with tabs[0]:
    food_dict = {r[0]: r[1] for r in run_query("SELECT * FROM foods", fetch=True)}
    if not users: st.warning("Ajoutez un utilisateur dans 'Paramètres'.")
    else:
        st.header("Composition du repas")
        with st.container(border=True):
            meal_label = st.text_input("Nom du repas", "Déjeuner")
            n_ing = st.number_input("Nombre d'ingrédients", 1, 15, 2)
            total_cal_plat = 0
            cols_ing = st.columns(2)
            for i in range(n_ing):
                with cols_ing[0]:
                    choice = st.selectbox(f"Ingrédient {i+1}", sorted(list(food_dict.keys())), key=f"f_{i}")
                with cols_ing[1]:
                    weight = st.number_input(f"Poids (g) - {choice}", 0, key=f"w_{i}")
                    total_cal_plat += (food_dict[choice] * weight) / 100
        
        st.subheader("Répartition familiale")
        shares = {}
        u_cols = st.columns(len(users))
        for i, u in enumerate(users):
            with u_cols[i]:
                st.markdown(f"**{u}**")
                s = st.slider(f"Part (%)", 0, 100, 100//len(users), key=f"s_{u}")
                ex = st.number_input(f"Extras (kcal)", 0, key=f"ex_{u}")
                shares[u] = (total_cal_plat * s / 100) + ex
            
        if st.button("🚀 Valider le repas"):
            for u, cal in shares.items():
                run_query("INSERT INTO meal_logs (date, label, user, calories) VALUES (?, ?, ?, ?)", 
                          (date.today().isoformat(), meal_label, u, cal))
            st.success("Repas enregistré !")

# --- 2. BILAN DU JOUR ---
with tabs[1]:
    st.header(f"📅 Bilan du {date.today().strftime('%d/%m/%Y')}")
    tday = date.today().isoformat()
    
    for u in users:
        with st.expander(f"👤 Profil : {u}", expanded=True):
            in_cal = run_query("SELECT SUM(calories) FROM meal_logs WHERE user=? AND date=?", (u, tday), fetch=True)[0][0] or 0
            res_d = run_query("SELECT depense FROM daily_spend WHERE date=? AND user=?", (tday, u), fetch=True)
            cur_dep = res_d[0][0] if res_d else 2000.0
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Mangé", f"{in_cal:.0f} kcal")
            new_dep = c2.number_input(f"Dépensé ({u})", value=float(cur_dep), key=f"dep_{u}")
            if new_dep != cur_dep:
                run_query("INSERT OR REPLACE INTO daily_spend VALUES (?, ?, ?)", (tday, u, new_dep))
                st.rerun()
            c3.metric("Bilan", f"{in_cal - new_dep:.0f} kcal", delta=-(in_cal - new_dep), delta_color="inverse")
            
            # Liste des repas avec bouton supprimer
            day_meals = run_query("SELECT id, label, calories FROM meal_logs WHERE user=? AND date=?", (u, tday), fetch=True)
            if day_meals:
                for mid, mlabel, mcal in day_meals:
                    col_m, col_b = st.columns([4, 1])
                    col_m.text(f"🍴 {mlabel} : {mcal:.0f} kcal")
                    if col_b.button("Supprimer", key=f"del_{mid}"):
                        run_query("DELETE FROM meal_logs WHERE id=?", (mid,))
                        st.rerun()

# --- 3. HISTORIQUE MENSUEL ---
with tabs[2]:
    if users:
        u_hist = st.selectbox("Choisir un utilisateur", users, key="h_u_sel")
        
        # Définition de la période (30 derniers jours)
        today_date = date.today()
        thirty_days_ago = today_date - timedelta(days=30)
        
        # --- RÉCUPÉRATION ET CALCUL DES DONNÉES ---
        history = []
        total_in = 0
        total_out = 0
        days_count = 0
        
        # On boucle sur les 30 derniers jours
        for i in range(30, -1, -1):  # Du plus ancien au plus récent
            d = (today_date - timedelta(days=i)).isoformat()
            
            # Somme des repas du jour
            in_c = run_query("SELECT SUM(calories) FROM meal_logs WHERE user=? AND date=?", (u_hist, d), fetch=True)[0][0] or 0
            
            # Dépense du jour
            out_c_res = run_query("SELECT depense FROM daily_spend WHERE user=? AND date=?", (u_hist, d), fetch=True)
            out_c = out_c_res[0][0] if out_c_res else 0
            
            history.append({
                "Date": d, 
                "Entrant (Kcal)": in_c, 
                "Sortant (Kcal)": out_c, 
                "Bilan": in_c - out_c
            })
            
            total_in += in_c
            total_out += out_c
            if in_c > 0 or out_c > 0:
                days_count += 1

        dfh = pd.DataFrame(history)

        # --- AFFICHAGE DES MÉTRIQUES MOYENNES ---
        st.subheader(f"📊 Statistiques des 30 derniers jours ({u_hist})")
        
        avg_in = total_in / 30
        avg_out = total_out / 30
        avg_bilan = (total_in - total_out) / 30

        m1, m2, m3 = st.columns(3)
        m1.metric("Moyenne Entrante", f"{avg_in:.0f} kcal/j")
        m2.metric("Moyenne Sortante", f"{avg_out:.0f} kcal/j")
        m3.metric("Bilan Moyen", f"{avg_bilan:.0f} kcal/j", 
                  delta=f"{avg_bilan:.0f}", delta_color="inverse")

        st.divider()

        # --- GRAPHIQUE DU BILAN ---
        st.subheader("📈 Courbe du bilan journalier")
        fig = go.Figure()
        
        # Courbe du bilan
        fig.add_trace(go.Scatter(
            x=dfh['Date'], 
            y=dfh['Bilan'], 
            mode='lines+markers',
            name="Bilan (Entrant - Sortant)",
            line=dict(color='#ef5350', width=3),
            fill='tozeroy' # Remplit la zone sous la courbe
        ))
        
        # Ligne d'équilibre
        fig.add_hline(y=0, line_dash="dash", line_color="green", annotation_text="Équilibre")
        
        fig.update_layout(
            yaxis_title="Calories (kcal)",
            xaxis_title="Date",
            hovermode="x unified",
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)

        # --- TABLEAU DÉTAILLÉ ---
        with st.expander("📄 Voir le détail journalier (Tableau)"):
            st.dataframe(
                dfh.sort_values(by="Date", ascending=False), 
                hide_index=True, 
                use_container_width=True
            )

# --- 4. GESTION ---
with tabs[3]:
    st.header("🗄️ Gestion des données")
    table_choice = st.radio("Table :", ["Repas", "Dépenses"], horizontal=True)
    
    if table_choice == "Repas":
        data = run_query("SELECT * FROM meal_logs ORDER BY date DESC", fetch=True)
        df = pd.DataFrame(data, columns=["ID", "Date", "Label", "User", "Calories"])
    else:
        data = run_query("SELECT * FROM daily_spend ORDER BY date DESC", fetch=True)
        df = pd.DataFrame(data, columns=["Date", "User", "Dépense"])
        
    st.write("💡 Pour supprimer : sélectionnez une ligne et appuyez sur 'Suppr' (Delete) sur votre clavier.")
    edited = st.data_editor(df, num_rows="dynamic", use_container_width=True)
    
    if st.button("Sauvegarder les changements"):
        if table_choice == "Repas":
            run_query("DELETE FROM meal_logs")
            for _, row in edited.iterrows():
                run_query("INSERT INTO meal_logs VALUES (?,?,?,?,?)", tuple(row))
        else:
            run_query("DELETE FROM daily_spend")
            for _, row in edited.iterrows():
                run_query("INSERT INTO daily_spend VALUES (?,?,?)", tuple(row))
        st.success("Base mise à jour !")

# --- 5. PARAMÈTRES ---
with tabs[4]:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("👥 Utilisateurs")
        nu = st.text_input("Nouveau nom")
        if st.button("Ajouter"):
            run_query("INSERT INTO users VALUES (?)", (nu,))
            st.rerun()
        u_to_del = st.selectbox("Choisir un utilisateur à supprimer", users)
        if st.button("🗑️ Supprimer l'utilisateur"):
            run_query("DELETE FROM users WHERE name=?", (u_to_del,))
            st.rerun()

    with c2:
        st.subheader("🥗 Aliments")
        fn = st.text_input("Aliment")
        fc = st.number_input("Kcal/100g", 0)
        if st.button("Ajouter Aliment"):
            run_query("INSERT OR REPLACE INTO foods VALUES (?, ?)", (fn, fc))
            st.rerun()
        
        foods_df = pd.DataFrame(run_query("SELECT * FROM foods ORDER BY name", fetch=True), columns=["Nom", "Kcal"])
        f_to_del = st.selectbox("Aliment à supprimer", foods_df["Nom"])
        if st.button("🗑️ Supprimer l'aliment"):
            run_query("DELETE FROM foods WHERE name=?", (f_to_del,))
            st.rerun()
        st.dataframe(foods_df, height=300)