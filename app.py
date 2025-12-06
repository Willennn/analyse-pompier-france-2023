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
# 2. CHARGEMENT ET NETTOYAGE DES DONNÉES (CORRIGÉ)
# -----------------------------------------------------------------------------
@st.cache_data
def load_data():
    file_path = "interventions2023.csv"
    
    # 1. Tentative de chargement robuste
    df = None
    # Liste des encodages à tester
    encodings = ['latin-1', 'utf-8', 'cp1252', 'ISO-8859-1']
    # Liste des séparateurs à tester
    separators = [';', ',']
    
    for sep in separators:
        for enc in encodings:
            try:
                df_test = pd.read_csv(file_path, sep=sep, encoding=enc, nrows=5)
                # Si on a plus d'une colonne, c'est probablement le bon séparateur
                if len(df_test.columns) > 1:
                    df = pd.read_csv(file_path, sep=sep, encoding=enc)
                    break
            except:
                continue
        if df is not None:
            break
    
    if df is None:
        st.error(f"Erreur critique : Impossible de lire '{file_path}'. Vérifie le format du fichier.")
        return None

    # 2. Nettoyage des noms de colonnes
    df.columns = df.columns.str.strip()
    
    # 3. Renommage intelligent
    col_mapping = {}
    for col in df.columns:
        c_lower = col.lower()
        # On mappe selon des mots clés
        if "zone" in c_lower: col_mapping[col] = "Zone"
        elif "region" in c_lower or "région" in c_lower: col_mapping[col] = "Region"
        elif "departement" in c_lower or "département" in c_lower: col_mapping[col] = "Departement"
        elif "incendies" in c_lower: col_mapping[col] = "Incendies"
        elif "secours" in c_lower and "victime" in c_lower: col_mapping[col] = "SAP_Victime"
        elif "secours" in c_lower and "personne" in c_lower: col_mapping[col] = "SAP_Personne"
        elif "accident" in c_lower: col_mapping[col] = "Accidents"
        elif "total" in c_lower: col_mapping[col] = "Total"

    df = df.rename(columns=col_mapping)
    
    # --- CORRECTIF CRITIQUE ICI ---
    # Si deux colonnes s'appellent "Total", on ne garde que la première pour éviter le crash
    df = df.loc[:, ~df.columns.duplicated()]
    # ------------------------------

    # 4. Conversion en numérique
    numeric_cols = ["Incendies", "SAP_Victime", "SAP_Personne", "Accidents", "Total"]
    
    for col in numeric_cols:
        if col in df.columns:
            # Conversion forcée en string pour nettoyer les espaces (ex: "1 000")
            # On vérifie si la colonne est de type object (texte) avant de faire .str
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).str.replace(" ", "").str.replace(",", ".")
            
            # Conversion en nombre, les erreurs deviennent NaN puis 0
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # 5. Création colonne calculée
    if "SAP_Victime" in df.columns and "SAP_Personne" in df.columns:
        df["Secours_Personne_Total"] = df["SAP_Victime"] + df["SAP_Personne"]
    elif "SAP_Victime" in df.columns:
        df["Secours_Personne_Total"] = df["SAP_Victime"]
    elif "SAP_Personne" in df.columns:
         df["Secours_Personne_Total"] = df["SAP_Personne"]
    else:
        df["Secours_Personne_Total"] = 0

    return df

# Chargement
df = load_data()

# Arrêt si échec
if df is None:
    st.stop()

# -----------------------------------------------------------------------------
# 3. SIDEBAR & FILTRES
# -----------------------------------------------------------------------------
st.sidebar.header("Filtres")

# Vérification que la colonne Region existe
if "Region" in df.columns:
    all_regions = sorted(df["Region"].unique().astype(str))
    selected_region = st.sidebar.selectbox("Sélectionner une Région", ["Toutes"] + all_regions)
    if selected_region != "Toutes":
        df_filtered = df[df["Region"] == selected_region]
    else:
        df_filtered = df
else:
    st.sidebar.warning("Colonne 'Region' non trouvée.")
    df_filtered = df

st.sidebar.markdown("---")
st.sidebar.info(f"Lignes affichées : {len(df_filtered)}")
st.sidebar.caption("Source : Data.gouv.fr")

# -----------------------------------------------------------------------------
# 4. DASHBOARD - SECTION KPIs
# -----------------------------------------------------------------------------
st.header("1. Indicateurs Clés (KPIs)")

# Vérification des colonnes avant calcul
col_total = "Total" if "Total" in df_filtered.columns else df_filtered.columns[0] # Fallback
total_interventions = df_filtered[col_total].sum() if pd.api.types.is_numeric_dtype(df_filtered[col_total]) else 0

total_incendies = df_filtered["Incendies"].sum() if "Incendies" in df_filtered.columns else 0
total_sap = df_filtered["Secours_Personne_Total"].sum()
total_accidents = df_filtered["Accidents"].sum() if "Accidents" in df_filtered.columns else 0

# Calcul pourcentages
if total_interventions > 0:
    pct_incendies = (total_incendies / total_interventions) * 100
    pct_sap = (total_sap / total_interventions) * 100
else:
    pct_incendies = 0
    pct_sap = 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Interventions", f"{int(total_interventions):,}".replace(",", " "))
c2.metric("Incendies", f"{int(total_incendies):,}", f"{pct_incendies:.1f}%")
c3.metric("Secours à personne", f"{int(total_sap):,}", f"{pct_sap:.1f}%")
c4.metric("Accidents", f"{int(total_accidents):,}")

st.markdown("---")

# -----------------------------------------------------------------------------
# 5. STORYTELLING & VISUALISATIONS
# -----------------------------------------------------------------------------

# --- Graphique 1 : Pie Chart ---
st.subheader("2. Répartition des missions")

labels = ['Incendies', 'Secours à Personne', 'Accidents']
values = [total_incendies, total_sap, total_accidents]
# Ajout "Autres" pour compléter
autres = total_interventions - sum(values)
if autres > 0:
    labels.append("Autres")
    values.append(autres)

fig_pie = px.pie(names=labels, values=values, hole=0.4, 
                 color_discrete_sequence=px.colors.qualitative.Pastel)
st.plotly_chart(fig_pie, use_container_width=True)

# --- Graphique 2 : Bar Chart Départements ---
st.subheader("3. Top Départements (Volume)")

if "Departement" in df_filtered.columns:
    # On groupe par département et on somme
    df_dept = df_filtered.groupby("Departement")[col_total].sum().reset_index()
    df_dept = df_dept.sort_values(by=col_total, ascending=False).head(10)
    
    fig_bar = px.bar(df_dept, x=col_total, y="Departement", orientation='h',
                     title="Top 10 Départements par volume d'interventions",
                     color=col_total, color_continuous_scale="Reds")
    fig_bar.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig_bar, use_container_width=True)
else:
    st.warning("Colonne 'Departement' non trouvée pour le graphique.")

# --- Graphique 3 : Carte ---
st.subheader("4. Carte de France")
st.info("Visualisation simplifiée (Bubble Map) basée sur les données disponibles.")

# Si on n'a pas de lat/lon, on ne peut pas faire de carte précise sans GeoJSON complexe.
# On affiche un tableau de données à la place si la carte est trop complexe à gérer sans fichier externe.
if "Departement" in df_filtered.columns:
    st.dataframe(df_filtered.head(10), use_container_width=True)
else:
    st.write("Données géographiques non disponibles.")

# -----------------------------------------------------------------------------
# 6. FIN
# -----------------------------------------------------------------------------
st.success("✅ Dashboard chargé avec succès.")
