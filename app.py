import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import requests # Pour télécharger le GeoJSON si besoin

# -----------------------------------------------------------------------------
# 1. CONFIGURATION DE LA PAGE
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Dashboard Pompiers - Data Storytelling",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Titre principal et contexte
st.title("🚒 Analyse des Interventions des Pompiers (2023)")
st.markdown("""
**Contexte du projet** : Ce dashboard explore les données d'interventions des SDIS en France.
L'objectif est de comprendre la répartition de l'activité opérationnelle : est-ce que les pompiers éteignent surtout des feux, ou font-ils du secours à la personne ?
""")

# -----------------------------------------------------------------------------
# 2. CHARGEMENT ET NETTOYAGE DES DONNÉES (Partie Critique)
# -----------------------------------------------------------------------------
@st.cache_data
def load_data():
    file_path = "interventions2023.csv"
    
    # Tentative de chargement robuste (gestion des erreurs d'encodage courantes)
    try:
        # Essai 1 : Encodage standard français (latin-1) et point-virgule
        df = pd.read_csv(file_path, sep=';', encoding='latin-1')
    except:
        try:
            # Essai 2 : Encodage UTF-8
            df = pd.read_csv(file_path, sep=';', encoding='utf-8')
        except:
            st.error(f"Erreur : Impossible de lire le fichier '{file_path}'. Vérifie qu'il est bien dans le dossier.")
            return None

    # Nettoyage des noms de colonnes (enlève les espaces avant/après)
    df.columns = df.columns.str.strip()
    
    # Renommage intelligent pour éviter les erreurs d'accents
    # On cherche des mots clés dans les colonnes pour les standardiser
    col_mapping = {}
    for col in df.columns:
        c_lower = col.lower()
        if "zone" in c_lower: col_mapping[col] = "Zone"
        elif "region" in c_lower or "région" in c_lower: col_mapping[col] = "Region"
        elif "departement" in c_lower or "département" in c_lower: col_mapping[col] = "Departement"
        elif "incendies" in c_lower: col_mapping[col] = "Incendies"
        elif "secours" in c_lower and "victime" in c_lower: col_mapping[col] = "SAP_Victime"
        elif "secours" in c_lower and "personne" in c_lower: col_mapping[col] = "SAP_Personne"
        elif "accident" in c_lower: col_mapping[col] = "Accidents"
        elif "total" in c_lower: col_mapping[col] = "Total"

    df = df.rename(columns=col_mapping)

    # Conversion en numérique (force les erreurs en NaN puis remplace par 0)
    numeric_cols = ["Incendies", "SAP_Victime", "SAP_Personne", "Accidents", "Total"]
    for col in numeric_cols:
        if col in df.columns:
            # Enlève les espaces insécables parfois présents dans les milliers (ex: "1 000")
            if df[col].dtype == object:
                df[col] = df[col].astype(str).str.replace(" ", "").str.replace(",", ".")
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # Création d'une colonne globale "Secours à personne" (somme des deux types si présents)
    if "SAP_Victime" in df.columns and "SAP_Personne" in df.columns:
        df["Secours_Personne_Total"] = df["SAP_Victime"] + df["SAP_Personne"]
    elif "SAP_Victime" in df.columns:
        df["Secours_Personne_Total"] = df["SAP_Victime"]
    else:
        df["Secours_Personne_Total"] = 0

    return df

# Chargement
df = load_data()

# Arrêt du script si pas de données
if df is None:
    st.stop()

# -----------------------------------------------------------------------------
# 3. SIDEBAR & FILTRES
# -----------------------------------------------------------------------------
st.sidebar.header("Filtres")

# Filtre Région
all_regions = sorted(df["Region"].unique().astype(str))
selected_region = st.sidebar.selectbox("Sélectionner une Région", ["Toutes"] + all_regions)

# Filtrage du DataFrame
if selected_region != "Toutes":
    df_filtered = df[df["Region"] == selected_region]
else:
    df_filtered = df

st.sidebar.markdown("---")
st.sidebar.info(f"Lignes affichées : {len(df_filtered)}")
st.sidebar.caption("Source : Data.gouv.fr")

# -----------------------------------------------------------------------------
# 4. DASHBOARD - SECTION KPIs
# -----------------------------------------------------------------------------
st.header("1. Indicateurs Clés (KPIs)")

# Calcul des totaux sur les données filtrées
total_interventions = df_filtered["Total"].sum()
total_incendies = df_filtered["Incendies"].sum()
total_sap = df_filtered["Secours_Personne_Total"].sum()
total_accidents = df_filtered["Accidents"].sum() if "Accidents" in df_filtered.columns else 0

# Calcul des pourcentages
if total_interventions > 0:
    pct_incendies = (total_incendies / total_interventions) * 100
    pct_sap = (total_sap / total_interventions) * 100
else:
    pct_incendies = 0
    pct_sap = 0

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Interventions", f"{total_interventions:,.0f}".replace(",", " "))
col2.metric("Incendies", f"{total_incendies:,.0f}", f"{pct_incendies:.1f}% du total")
col3.metric("Secours à personne", f"{total_sap:,.0f}", f"{pct_sap:.1f}% du total")
col4.metric("Accidents Route", f"{total_accidents:,.0f}")

st.markdown("---")

# -----------------------------------------------------------------------------
# 5. STORYTELLING & VISUALISATIONS
# -----------------------------------------------------------------------------

# --- Graphique 1 : La part réelle des incendies (Pie Chart) ---
st.subheader("2. Quelle est la mission principale des pompiers ?")
st.write("Beaucoup de gens pensent que les pompiers éteignent surtout des feux. Les données montrent une réalité différente.")

data_pie = pd.DataFrame({
    'Type': ['Incendies', 'Secours à Personne', 'Accidents', 'Autres'],
    'Valeur': [
        total_incendies, 
        total_sap, 
        total_accidents, 
        total_interventions - (total_incendies + total_sap + total_accidents)
    ]
})

fig_pie = px.pie(data_pie, values='Valeur', names='Type', hole=0.4, 
                 color_discrete_sequence=px.colors.qualitative.Pastel)
fig_pie.update_traces(textposition='inside', textinfo='percent+label')
st.plotly_chart(fig_pie, use_container_width=True)

st.info("💡 **Insight** : Le secours à la personne représente la grande majorité de l'activité, transformant le métier de pompier vers un rôle d'urgence sociale et sanitaire.")

# --- Graphique 2 : Comparaison par Département (Bar Chart) ---
st.subheader(f"3. Comparaison des Départements ({selected_region})")

# On trie pour avoir un graphique propre
df_bar = df_filtered.sort_values(by="Total", ascending=False).head(15) # Top 15 pour lisibilité

fig_bar = px.bar(
    df_bar, 
    x="Departement", 
    y=["Secours_Personne_Total", "Incendies"], 
    title="Répartition Incendies vs Secours par Département",
    barmode='group',
    labels={"value": "Nombre d'interventions", "variable": "Type"},
    color_discrete_map={"Secours_Personne_Total": "#1f77b4", "Incendies": "#d62728"}
)
st.plotly_chart(fig_bar, use_container_width=True)

# --- Graphique 3 : Carte (Map) ---
st.subheader("4. Carte de l'intensité des interventions")

# Pour la carte, on a besoin d'un GeoJSON. 
# Si tu ne l'as pas, on utilise un scatter plot simple ou on essaie de charger une url publique.
try:
    # URL publique stable pour les départements français
    geojson_url = "https://france-geojson.gregoiredavid.fr/repo/departements.geojson"
    
    # On extrait le code département (ex: "01", "75") pour faire la jointure
    # Cette partie dépend de comment est écrit ton département dans le CSV. 
    # Ici on suppose qu'il y a le numéro au début ou que c'est le nom.
    # Pour simplifier, on va créer une map simple ScatterGeo ou utiliser une librairie simple.
    
    # Option simple pour étudiant : Bubble map sur les coordonnées (si disponibles)
    # OU Choropleth map si on arrive à matcher les noms.
    
    # Tentative Choropleth simple
    fig_map = px.choropleth(
        df_filtered,
        geojson=geojson_url,
        locations="Departement", # Doit matcher le GeoJSON (nom ou code)
        featureidkey="properties.nom", # On essaie de matcher par nom
        color="Total",
        scope="europe",
        color_continuous_scale="Reds",
        title="Carte de chaleur des interventions (Match par nom de département)"
    )
    fig_map.update_geos(fitbounds="locations", visible=False)
    st.plotly_chart(fig_map, use_container_width=True)

except Exception as e:
    st.warning("La carte n'a pas pu être chargée (problème de connexion au GeoJSON ou de format). Voici les données brutes à la place.")
    st.dataframe(df_filtered[["Departement", "Total", "Incendies"]].head())

# -----------------------------------------------------------------------------
# 6. QUALITÉ DES DONNÉES & CONCLUSION
# -----------------------------------------------------------------------------
st.markdown("---")
with st.expander("🔍 Qualité des données et Limites"):
    st.write("**Sources** : Ministère de l'Intérieur.")
    st.write(f"**Données manquantes** : {df_filtered.isna().sum().sum()} cellules vides détectées.")
    st.write("**Limites** : Certaines interventions 'Autres' regroupent des opérations diverses (animaux, fuites d'eau) qui ne sont pas détaillées ici.")

st.success("✅ **Conclusion** : Ce dashboard permet aux décideurs de voir que les ressources doivent être priorisées sur la formation au secours à personne, qui constitue le cœur de métier actuel.")
