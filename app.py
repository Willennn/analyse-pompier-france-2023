"""
app.py - Dashboard Interventions Pompiers France (2023)
Version robuste : accès aux colonnes EXACTES que tu as fournies.
Multipage-like (top nav) + filtres à gauche + carte choropleth.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import requests
import json
import os
import re

# -----------------------
# Config page
# -----------------------
st.set_page_config(page_title="Pompiers France 2023", layout="wide")

# -----------------------
# Util: safe column resolver
# -----------------------
def col_exists(df, name_variants):
    """Return the first existing column name found in df from name_variants list, else None."""
    cols = df.columns.tolist()
    for v in name_variants:
        if v in cols:
            return v
    # try case/accents-insensitive match
    cols_norm = {re.sub(r'\W+', '', c).lower(): c for c in cols}
    for v in name_variants:
        key = re.sub(r'\W+', '', v).lower()
        if key in cols_norm:
            return cols_norm[key]
    return None

# -----------------------
# Load data (robust)
# -----------------------
@st.cache_data
def load_data(path="interventions2023.csv"):
    # try common encodings
    for enc in ("latin-1", "utf-8", "cp1252"):
        try:
            df = pd.read_csv(path, sep=";", encoding=enc)
            break
        except Exception:
            df = None
    if df is None:
        raise RuntimeError(f"Impossible de lire {path} avec encodages courants.")

    # Strip column names whitespace
    df.columns = [c.strip() for c in df.columns]

    # --- Map the exact columns you provided to normalized keys ---
    mapping = {
        # basics (exact names as provided)
        "Annee": col_exists(df, ["Année", "Annee"]),
        "Zone": col_exists(df, ["Zone"]),
        "Region": col_exists(df, ["Région", "Region"]),
        "Numero": col_exists(df, ["Numéro", "Numero"]),
        "Departement": col_exists(df, ["Département", "Departement"]),
        "Categorie_A": col_exists(df, ["Catégorie A", "Catégorie", "Categorie", "Catégorie_A"]),
        # main numeric columns (use the long exact names you listed)
        "Feux_habitations": col_exists(df, ["Feux d'habitations-bureaux", "Feux d'habitations bureaux", "Feux_habitations"]),
        "Incendies": col_exists(df, ["Incendies"]),
        "Secours_victime": col_exists(df, ["Secours à victime", "Secours à victime", "Secours_victime"]),
        "Secours_personne": col_exists(df, ["Secours à personne", "Secours_personne"]),
        "Malaises_Urgence": col_exists(df, ["Malaises à domicile : urgence vitale", "Malaises à domicile : urgence vitale", "Malaises_Urgence"]),
        "Malaises_Carence": col_exists(df, ["Malaises à domicile : carence", "Malaises à domicile : carence", "Malaises_Carence"]),
        "Accidents_circulation": col_exists(df, ["Accidents de circulation", "Accidents de circulation", "Accidents_circulation"]),
        "Operations_diverses": col_exists(df, ["Opérations diverses", "Operations diverses", "Operations_diverses"]),
        "Total_interventions": col_exists(df, ["Total interventions", "Total_interventions"])
    }

    # For any mapped None -> create a column with zeros (to avoid KeyError later)
    for norm_key, found in mapping.items():
        if found is None:
            df[norm_key] = 0
            mapping[norm_key] = norm_key  # point to created column
        else:
            # rename the real column to the normalized key if names differ
            if found != norm_key:
                df = df.rename(columns={found: norm_key})
                mapping[norm_key] = norm_key

    # Ensure numeric columns are numeric
    numeric_cols = ["Feux_habitations", "Incendies", "Secours_victime", "Secours_personne",
                    "Malaises_Urgence", "Malaises_Carence", "Accidents_circulation",
                    "Operations_diverses", "Total_interventions"]
    for c in numeric_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
        else:
            df[c] = 0

    # Derived
    df["Total_Malaises"] = df["Malaises_Urgence"] + df["Malaises_Carence"]

    # Ensure text columns exist
    for txt in ["Region", "Departement", "Categorie_A", "Zone", "Numero"]:
        if txt not in df.columns:
            df[txt] = ""

    # Normalize departement codes as strings (for mapping)
    if "Departement" in df.columns:
        df["Departement_str"] = df["Departement"].astype(str).str.extract(r"(\d+)").fillna("")
    else:
        df["Departement_str"] = ""

    return df

# Load
df_raw = load_data()

# -----------------------
# Sidebar filters
# -----------------------
st.sidebar.title("Filtres")
regions = ["Toutes"] + sorted(df_raw["Region"].replace("", "Non renseignée").unique().tolist())
sel_region = st.sidebar.selectbox("Région", regions)

types_zone = ["Tous"] + sorted(df_raw["Zone"].replace("", "Non renseignée").unique().tolist())
sel_zone = st.sidebar.selectbox("Zone", types_zone)

cats = ["Toutes"] + sorted(df_raw["Categorie_A"].replace("", "Non renseignée").unique().tolist())
sel_cat = st.sidebar.selectbox("Catégorie", cats)

# Apply filters
df = df_raw.copy()
if sel_region != "Toutes":
    df = df[df["Region"].fillna("Non renseignée") == sel_region]
if sel_zone != "Tous":
    df = df[df["Zone"].fillna("Non renseignée") == sel_zone]
if sel_cat != "Toutes":
    df = df[df["Categorie_A"].fillna("Non renseignée") == sel_cat]

# -----------------------
# Top nav (multipage-like)
# -----------------------
PAGES = ["Overview", "Interventions", "Carences", "Carte", "Conclusion"]
if "page" not in st.session_state:
    st.session_state.page = "Overview"

cols = st.columns(len(PAGES))
for i, p in enumerate(PAGES):
    if cols[i].button(p):
        st.session_state.page = p

st.markdown("---")

# -----------------------
# Common metrics (bounded)
# -----------------------
total_inter = df["Total_interventions"].sum()
incendies = df["Incendies"].sum()
sav = df["Secours_victime"].sum()
sap = df["Secours_personne"].sum()
mal = df["Total_Malaises"].sum()
car = df["Malaises_Carence"].sum()

def pct(n, d):
    return float(min(100, (n / max(d, 1)) * 100))

pct_medical = pct(sav + sap, total_inter)
pct_incendies = pct(incendies, total_inter)
pct_car = pct(car, mal if mal>0 else 1)

# -----------------------
# Pages
# -----------------------
if st.session_state.page == "Overview":
    st.header("Vue d'ensemble")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total interventions", f"{int(total_inter):,}".replace(",", " "))
    c2.metric("Urgences médicales", f"{pct_medical:.0f}%")
    c3.metric("Incendies", f"{pct_incendies:.1f}%")
    c4.metric("Taux de carences", f"{pct_car:.0f}%")

    st.markdown("---")
    st.subheader("Répartition principale")
    vals = {
        "Secours à victime": sav,
        "Secours à personne": sap,
        "Incendies": incendies,
        "Accidents de circulation": df["Accidents_circulation"].sum(),
        "Opérations diverses": df["Operations_diverses"].sum()
    }
    fig = px.pie(values=list(vals.values()), names=list(vals.keys()), hole=0.45,
                 color_discrete_sequence=px.colors.sequential.Reds)
    fig.update_traces(textinfo="percent+label", textposition="outside")
    st.plotly_chart(fig, use_container_width=True)

elif st.session_state.page == "Interventions":
    st.header("Interventions — Top & tendances")
    st.subheader("Top départements")
    metric = st.selectbox("Choisir métrique", [
        ("Total interventions", "Total_interventions"),
        ("Incendies", "Incendies"),
        ("Secours victime", "Secours_victime"),
        ("Secours personne", "Secours_personne")
    ], format_func=lambda x: x[0])
    metric_key = metric[1]
    topn = st.slider("Top N", 5, 20, 10)
    top_df = df.groupby("Departement").agg({metric_key: "sum"}).reset_index().nlargest(topn, metric_key)
    fig = px.bar(top_df, x=metric_key, y="Departement", orientation="h", color=metric_key, color_continuous_scale="Reds")
    st.plotly_chart(fig, use_container_width=True)

elif st.session_state.page == "Carences":
    st.header("Carences ambulancières")
    st.subheader("Urgences vs Carences")
    fig = go.Figure()
    fig.add_trace(go.Bar(x=["Urgence vitale", "Carence"], y=[df["Malaises_Urgence"].sum(), df["Malaises_Carence"].sum()],
                         marker_color=["#3498db", "#e74c3c"]))
    fig.update_layout(yaxis_title="Nombre")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.subheader("Taux de carences par région")
    reg_df = df_raw.groupby("Region").agg({"Malaises_Carence":"sum","Total_Malaises":"sum"}).reset_index()
    reg_df["Taux"] = (reg_df["Malaises_Carence"] / reg_df["Total_Malaises"].replace(0, np.nan) * 100).fillna(0)
    reg_df = reg_df.sort_values("Taux", ascending=False)
    fig2 = px.bar(reg_df.head(20), x="Taux", y="Region", orientation="h", color="Taux", color_continuous_scale="Reds")
    st.plotly_chart(fig2, use_container_width=True)

elif st.session_state.page == "Carte":
    st.header("Carte choroplèthe — départements")
    # try local geojson first
    geojson = None
    if os.path.exists("departements.geojson"):
        with open("departements.geojson", "r", encoding="utf-8") as f:
            geojson = json.load(f)
    else:
        # try fetch simplified geojson
        try:
            url = "https://raw.githubusercontent.com/gregoiredavid/france-geojson/master/departements-version-simplifiee.geojson"
            r = requests.get(url, timeout=8)
            if r.status_code == 200:
                geojson = r.json()
        except Exception:
            geojson = None

    if geojson is None:
        st.info("GeoJSON non disponible. Ajoute 'departements.geojson' au dossier de l'app pour afficher la carte.")
    else:
        # prepare mapping by dept code
        df_map = df_raw.copy()
        df_map["dept"] = df_map["Departement"].astype(str).str.extract(r"(\d+)").fillna("")
        agg = df_map.groupby("dept").agg({"Malaises_Carence":"sum","Total_Malaises":"sum"}).reset_index()
        agg["taux"] = (agg["Malaises_Carence"] / agg["Total_Malaises"].replace(0, np.nan) * 100).fillna(0)
        # attempt common feature key names
        feature_keys = ["properties.code", "properties.code_insee", "properties.Code", "id"]
        plotted = False
        for fk in ["properties.code", "properties.code_insee", "id"]:
            try:
                fig = px.choropleth(agg, geojson=geojson, locations="dept", color="taux",
                                    featureidkey=fk, color_continuous_scale="Reds")
                fig.update_geos(fitbounds="locations", visible=False)
                fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=700)
                st.plotly_chart(fig, use_container_width=True)
                plotted = True
                break
            except Exception:
                continue
        if not plotted:
            st.error("Impossible d'aligner les codes département du GeoJSON et vos données. Vérifiez 'properties.code' ou 'properties.code_insee' du GeoJSON.")

elif st.session_state.page == "Conclusion":
    st.header("Conclusion")
    st.write("Dashboard prêt. Pour améliorer : ajouter geojson local, données ambulances, et horaires de garde.")

# Footer
st.markdown("---")
st.caption("Projet EFREI - Pompiers France 2023")
