"""
app.py
Streamlit dashboard - Interventions des Sapeurs-Pompiers (2023)
Version enrichie : pages, scénarios, vérifications d'incohérences
"""

# =============================================================================
# IMPORTS
# =============================================================================
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# =============================================================================
# CONFIG
# =============================================================================
st.set_page_config(page_title="Pompiers France 2023", page_icon="🚒", layout="wide")

# CSS / style pour corriger le problème "texte blanc sur fond clair"
st.markdown(
    """
    <style>
    /* Forcer texte noir dans nos boîtes claires */
    .highlight-box, .highlight-box * { color: #000 !important; }
    .insight-box, .insight-box * { color: #000 !important; }

    .highlight-box {
        background: #fdecea !important;
        border-left: 4px solid #e74c3c;
        padding: 14px;
        border-radius: 8px;
        margin: 10px 0;
    }
    .insight-box {
        background: #e9f3ff !important;
        border-left: 4px solid #3498db;
        padding: 14px;
        border-radius: 8px;
        margin: 10px 0;
    }
    .big-number { font-size: 2.2rem; font-weight:700; color:#e74c3c; }
    .subtitle { font-size:0.9rem; color:#555; }
    </style>
    """,
    unsafe_allow_html=True,
)

# =============================================================================
# LOAD & CLEAN DATA
# =============================================================================
@st.cache_data
def load_data(path="interventions2023.csv"):
    # Chargement tolérant plusieurs encodages
    tried = []
    for enc in ["latin-1", "utf-8", "cp1252"]:
        try:
            df = pd.read_csv(path, sep=";", encoding=enc)
            break
        except Exception as e:
            tried.append((enc, str(e)))
            df = None
    if df is None:
        raise RuntimeError(f"Impossible de lire {path}. Tentatives: {tried}")

    # Normaliser colonnes (comme dans ta version)
    df.columns = [
        'Annee', 'Zone', 'Region', 'Numero', 'Departement', 'Categorie',
        'Feux_habitations', 'dont_cheminees', 'Feux_ERP_sommeil', 'Feux_ERP_sans_sommeil',
        'Feux_industriels', 'Feux_artisanaux', 'Feux_agricoles', 'Feux_voie_publique',
        'Feux_vehicules', 'Feux_vegetations', 'Autres_feux', 'Incendies',
        'Acc_travail', 'Acc_domicile', 'Acc_sport', 'Acc_voie_publique',
        'Secours_montagne', 'Malaises_travail', 'Malaises_urgence_vitale', 'Malaises_carence',
        'Malaises_sport', 'Malaises_voie_publique', 'Autolyses', 'Secours_piscines',
        'Secours_mer', 'Intoxications', 'dont_CO', 'Autres_SAV', 'Secours_victime',
        'Relevage_personnes', 'Recherche_personnes', 'Aides_personne', 'Secours_personne',
        'Acc_routiers', 'Acc_ferroviaires', 'Acc_aeriens', 'Acc_navigation', 'Acc_teleportage',
        'Accidents_circulation', 'Odeurs_gaz', 'Odeurs_autres', 'Faits_electricite',
        'Pollutions', 'Autres_risques_techno', 'Risques_technologiques',
        'Fuites_eau', 'Inondations', 'Ouvertures_portes', 'Recherches_objets',
        'Bruits_suspects', 'Protection_biens', 'Fausses_alertes', 'dont_DAAF',
        'Faits_animaux', 'Hymenopteres', 'Degagements_voies', 'Nettoyages_voies',
        'Eboulements', 'Deposes_objets', 'Piquets_securite', 'Engins_explosifs',
        'Autres_divers', 'Divers', 'Operations_diverses', 'Total_interventions'
    ]

    # Nettoyage numérique
    def clean_numeric(v):
        if pd.isna(v): return 0
        if isinstance(v, (int, float)): return int(v)
        s = str(v).strip().replace(" ", "").replace("\xa0", "").replace(",", ".")
        try:
            return int(float(s))
        except:
            return 0

    cols_num = df.columns[6:]
    for c in cols_num:
        df[c] = df[c].apply(clean_numeric)

    # Ajouts
    df["Total_Malaises"] = df.get("Malaises_urgence_vitale", 0) + df.get("Malaises_carence", 0)
    # éviter division par zéro
    df["Pct_Carences"] = np.where(df["Total_Malaises"] > 0,
                                  df["Malaises_carence"] / df["Total_Malaises"] * 100,
                                  0)

    def zone_type(row):
        if str(row.get("Numero", "")).strip() == "BSPP": return "BSPP (Paris)"
        if str(row.get("Numero", "")).strip() == "BMPM": return "BMPM (Marseille)"
        if str(row.get("Zone", "")).strip() in ["Antilles", "Guyane", "Ocean indien"]:
            return "DOM-TOM"
        return "Metropole"
    df["Type_Zone"] = df.apply(zone_type, axis=1)

    return df

# Charger
df_raw = load_data()

# =============================================================================
# SIDEBAR NAVIGATION & FILTERS
# =============================================================================
st.sidebar.title("Navigation")
page = st.sidebar.radio("Aller à", ["Overview", "Interventions", "Carences", "Scénarios", "Data Quality", "Conclusion"])

st.sidebar.header("Filtres")
regions = ["Toutes"] + sorted(df_raw["Region"].dropna().unique().tolist())
selected_region = st.sidebar.selectbox("Région", regions)

zones = ["Tous"] + sorted(df_raw["Type_Zone"].unique().tolist())
selected_zone = st.sidebar.selectbox("Type de territoire", zones)

cats = ["Toutes"] + [c for c in sorted(df_raw["Categorie"].dropna().unique().tolist())]
selected_cat = st.sidebar.selectbox("Catégorie SDIS", cats)

# Appliquer filtres
df = df_raw.copy()
if selected_region != "Toutes":
    df = df[df["Region"] == selected_region]
if selected_zone != "Tous":
    df = df[df["Type_Zone"] == selected_zone]
if selected_cat != "Toutes":
    df = df[df["Categorie"] == selected_cat]

st.sidebar.markdown("---")
st.sidebar.markdown(f"Territoires affichés : **{len(df)}**")
st.sidebar.markdown("Source : data.gouv.fr — Ministère de l'Intérieur (2023)")

# =============================================================================
# UTIL: safe percentage display
# =============================================================================
def safe_pct(num, den):
    """Retourne (pct, note) : pct (float), note (None or str) si incohérence"""
    if den == 0:
        return 0.0, "Donnée manquante (division par zéro)"
    pct = (num / den) * 100
    note = None
    if pct > 100:
        note = "⚠️ Valeur incohérente (>100%) — vérifier doublons/recouvrement dans les catégories."
    return pct, note

# =============================================================================
# Metrics communs
# =============================================================================
total_interventions = df["Total_interventions"].sum()
national_total = df_raw["Total_interventions"].sum()

# Calcul "Urgences médicales"
# On va privilégier une définition conservatrice : Secours_victime + Secours_personne
medical_sum = df["Secours_victime"].sum() + df["Secours_personne"].sum()
pct_medical, note_medical = safe_pct(medical_sum, total_interventions)

# Calcul incendies
incendies_sum = df["Incendies"].sum()
pct_incendies, note_inc = safe_pct(incendies_sum, total_interventions)

# Carences
carences_sum = df["Malaises_carence"].sum()
total_malaises_sum = df["Total_Malaises"].sum()
pct_carences, note_car = safe_pct(carences_sum, total_malaises_sum)

# =============================================================================
# PAGE : Overview
# =============================================================================
if page == "Overview":
    st.title("🚒 Les Pompiers en France (2023) — Overview")
    st.caption("Source : data.gouv.fr — Ministère de l'Intérieur | Projet EFREI")

    # KPIs
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total interventions (sélection)", f"{total_interventions:,}".replace(",", " "),
                f"{(total_interventions / national_total * 100):.1f}% du national")
    # gestion d'incohérence : si >100, on affiche la note et on borne l'affichage à 100%
    col2.metric("Urgences médicales", f"{min(pct_medical, 100):.0f}%" + ("" if note_medical is None else " ⚠️"))
    col3.metric("Incendies", f"{pct_incendies:.1f}%")
    col4.metric("Taux de carences (malaises)", f"{pct_carences:.0f}%")

    if note_medical:
        st.warning("Note sur les urgences médicales : " + note_medical + " (nous utilisons Secours_victime + Secours_personne pour ce calcul).")
    st.markdown("---")

    # Mythe vs réalité
    st.header("Le mythe vs la réalité")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            """
            <div class="highlight-box">
            <h4>🔥 Ce qu'on imagine</h4>
            Des camions rouges, des lances à incendie, des sauvetages dans les flammes...
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        # Pour éviter d'afficher "151%" par erreur, on met un message si >100%
        med_display = f"{min(pct_medical, 100):.0f}%"
        med_note = "" if note_medical is None else " (donnée incohérente détectée — voir details)"
        st.markdown(
            f"""
            <div class="insight-box">
            <h4>📊 La réalité 2023</h4>
            <strong>{pct_incendies:.1f}%</strong> d'incendies seulement<br>
            <strong>{med_display}</strong> d'urgences médicales{med_note}<br>
            1 intervention toutes les <strong>{max(1, int(round( (365*24*60*60) / (total_interventions if total_interventions>0 else 1) )) )} secondes</strong>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # Répartition (pie)
    st.header("Répartition des types d'interventions")
    types = {
        "Secours à victime": df["Secours_victime"].sum(),
        "Secours à personne": df["Secours_personne"].sum(),
        "Incendies": df["Incendies"].sum(),
        "Accidents circulation": df["Accidents_circulation"].sum(),
        "Opérations diverses": df["Operations_diverses"].sum()
    }
    fig = px.pie(names=list(types.keys()), values=list(types.values()), hole=0.4)
    fig.update_traces(textposition="outside", textinfo="percent+label")
    st.plotly_chart(fig, use_container_width=True)
    st.info("💡 Insight : les interventions médicales représentent une large part (définitions sujettes à recouvrement selon la source).")

# =============================================================================
# PAGE : Interventions (détails, timeline, heatmap)
# =============================================================================
elif page == "Interventions":
    st.title("Interventions — détails & tendances")

    # Timeline si plusieurs années disponibles
    years = sorted(df_raw["Annee"].dropna().unique().tolist())
    st.subheader("Tendance par année")
    if len(years) > 1:
        df_year = df_raw.groupby("Annee").agg({
            "Total_interventions": "sum",
            "Incendies": "sum",
            "Secours_victime": "sum",
            "Secours_personne": "sum"
        }).reset_index()
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_year["Annee"], y=df_year["Total_interventions"], mode="lines+markers", name="Total"))
        fig.add_trace(go.Scatter(x=df_year["Annee"], y=df_year["Incendies"], mode="lines+markers", name="Incendies"))
        fig.update_layout(height=420, xaxis_title="Année", yaxis_title="N interventions")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Données disponibles pour une seule année ; la timeline n'est pas affichée.")

    st.markdown("---")
    st.subheader("Heatmap (par région vs type)")
    df_regions = df_raw.groupby("Region").agg({
        "Incendies": "sum",
        "Secours_victime": "sum",
        "Secours_personne": "sum",
        "Total_interventions": "sum"
    }).fillna(0)
    if len(df_regions) > 0:
        heat = df_regions[["Incendies", "Secours_victime", "Secours_personne", "Total_interventions"]]
        fig_heat = px.imshow(heat.values, x=heat.columns, y=heat.index, aspect="auto")
        st.plotly_chart(fig_heat, use_container_width=True)
    else:
        st.info("Pas assez de données par région.")

    st.markdown("---")
    st.subheader("Top N départements (choisir métrique)")
    metric = st.selectbox("Métrique", ["Malaises_carence", "Incendies", "Secours_victime", "Total_interventions"])
    topn = st.slider("Nombre de résultats (Top N)", 5, 20, 10)
    df_top = df.groupby("Departement").agg({metric: "sum"}).reset_index().nlargest(topn, metric)
    fig_top = px.bar(df_top, x=metric, y="Departement", orientation="h")
    st.plotly_chart(fig_top, use_container_width=True)

# =============================================================================
# PAGE : Carences (analyse approfondie)
# =============================================================================
elif page == "Carences":
    st.title("Carences ambulancières — Analyse approfondie")

    st.markdown("**Définition** : on appelle 'carence' un cas où les pompiers interviennent faute d'ambulance disponible.")
    st.markdown("---")

    # graphique carences vs urgences vitales
    st.subheader("Carences vs Urgences vitales")
    urg = df["Malaises_urgence_vitale"].sum()
    car = df["Malaises_carence"].sum()
    fig = go.Figure()
    fig.add_trace(go.Bar(x=["Urgences vitales", "Carences"], y=[urg, car], marker_color=["#2ecc71", "#e74c3c"]))
    fig.update_layout(height=420, yaxis_title="Nombre")
    st.plotly_chart(fig, use_container_width=True)

    # Taux par région
    st.subheader("Taux de carences par région")
    df_reg = df_raw.groupby("Region").agg({"Malaises_carence": "sum", "Total_Malaises": "sum"}).reset_index()
    df_reg["Taux"] = np.where(df_reg["Total_Malaises"]>0, df_reg["Malaises_carence"]/df_reg["Total_Malaises"]*100, 0)
    df_reg = df_reg.sort_values("Taux", ascending=False)
    fig = px.bar(df_reg.head(20), x="Taux", y="Region", orientation="h", color="Taux", color_continuous_scale="Reds")
    st.plotly_chart(fig, use_container_width=True)
    st.info("💡 Insight : comparer régions permet d'identifier zones à prioriser pour renfort ambulancier.")

    # Top départements
    st.subheader("Top 10 départements — nombre de carences")
    top_car = df.nlargest(10, "Malaises_carence")[["Departement", "Malaises_carence", "Pct_Carences"]]
    st.dataframe(top_car.reset_index(drop=True))

    # Impact temps
    heures = carences_sum * 45 / 60
    st.markdown(f"**Impact temps** : {int(carences_sum):,} carences × 45 min = **{int(heures):,} heures** passées par les pompiers à remplacer les ambulances.".replace(",", " "))

# =============================================================================
# PAGE : Scénarios (what-if)
# =============================================================================
elif page == "Scénarios":
    st.title("🔮 Scénarios — What-if")
    st.markdown("Simulez l'effet d'une augmentation du parc ambulancier sur la réduction des carences (modèle simple).")

    # Slider
    incr = st.slider("Augmentation ambulances (%)", 0, 50, 10)
    # Hypothèse simple : % d'ambulances supplémentaires réduit proportionnellement les carences
    reduced_carences = max(0, carences_sum * (1 - incr / 100.0))
    reduction_abs = carences_sum - reduced_carences

    st.metric("Carences actuelles", f"{int(carences_sum):,}".replace(",", " "))
    st.metric(f"Carences après +{incr}% ambulances", f"{int(reduced_carences):,}".replace(",", " "), delta=f"-{int(reduction_abs):,}".replace(",", " "))

    st.markdown("---")
    st.markdown("**Remarque méthodologique** : modèle très simplifié — en réalité la relation est non-linéaire et dépend de répartition, gardes, mutualisation, etc.")

# =============================================================================
# PAGE : Data Quality
# =============================================================================
elif page == "Data Quality":
    st.title("📋 Qualité des données & vérifications")

    st.subheader("Contrôles rapides")
    # valeurs manquantes
    missing = df_raw.isna().sum().sum()
    duplicates = df_raw.duplicated().sum()
    st.metric("Valeurs manquantes (cells)", int(missing))
    st.metric("Doublons (lignes)", int(duplicates))
    st.metric("Territoires (lignes)", int(len(df_raw)))

    st.markdown("---")
    st.subheader("Vérification des totaux")
    # Vérifier incohérence : somme des catégories > total_interventions
    # Prenons un subset de colonnes "principales" et comparons à Total_interventions
    main_cols = ["Incendies", "Secours_victime", "Secours_personne", "Accidents_circulation", "Operations_diverses"]
    df_raw["sum_main"] = df_raw[main_cols].sum(axis=1)
    df_raw["diff_sum_total"] = df_raw["sum_main"] - df_raw["Total_interventions"]
    # Combien de lignes où sum_main > Total_interventions
    problem_count = (df_raw["diff_sum_total"] > 0).sum()
    st.write(f"Lignes où la somme des catégories principales excède Total_interventions : **{int(problem_count)}**")
    if problem_count > 0:
        st.warning("Il y a des recouvrements ou incohérences dans les agrégats (cela peut expliquer des % > 100). Vérifier la documentation source ou nettoyer les doublons / catégories recoupées.")

    st.markdown("---")
    st.subheader("Conseils")
    st.markdown("""
    - Vérifier la documentation et le data dictionary sur data.gouv.fr  
    - Contrôler l'origine des colonnes (certains SDIS comptent différemment)  
    - Agréger sur des variables uniques ou utiliser des étiquettes exclusives si disponibles
    """)

# =============================================================================
# PAGE : Conclusion
# =============================================================================
elif page == "Conclusion":
    st.title("📝 Conclusion & recommandations")
    st.markdown("""
    **Message clé** : Les pompiers accomplissent aujourd'hui majoritairement des missions médicales — 
    le phénomène des 'carences ambulancières' est un signal fort de tension du système de soins.
    """)

    st.markdown("- **Actions possibles** : renforts ambulanciers ciblés, mutualisation inter-départementale, # téléconsultation pré-tri.")
    st.markdown("- **Suite** : enrichir avec données d'ambulanciers, horaires de garde, distances, et une carte choroplèthe (geojson) pour prioriser interventions.")
    st.success("Projet EFREI — Data Storytelling — prêt à être enrichi (carte, pages détaillées, export).")

# =============================================================================
# FOOTER
# =============================================================================
st.markdown("---")
st.caption("EFREI Paris — Data Visualization | #EFREIDataStories2025")
