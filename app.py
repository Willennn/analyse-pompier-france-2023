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
    """Return the first existing column name from variants list."""
    cols = df.columns.tolist()

    # direct match
    for v in name_variants:
        if v in cols:
            return v

    # case/accents-insensitive
    def normalize(x):
        return re.sub(r'\W+', '', x).lower()

    cols_norm = {normalize(c): c for c in cols}

    for v in name_variants:
        key = normalize(v)
        if key in cols_norm:
            return cols_norm[key]

    return None

# -----------------------
# Load data (robust)
# -----------------------
@st.cache_data
def load_data(path="interventions2023.csv"):
    # try common encodings
    df = None
    for enc in ("latin-1", "utf-8", "cp1252"):
        try:
            df = pd.read_csv(path, sep=";", encoding=enc)
            break
        except Exception:
            pass

    if df is None:
        raise RuntimeError(f"Impossible de lire {path} avec encodages courants.")

    df.columns = [c.strip() for c in df.columns]

    # mapping normalized names
    mapping = {
        "Annee": col_exists(df, ["Année", "Annee"]),
        "Zone": col_exists(df, ["Zone"]),
        "Region": col_exists(df, ["Région", "Region"]),
        "Numero": col_exists(df, ["Numéro", "Numero"]),
        "Departement": col_exists(df, ["Département", "Departement"]),
        "Categorie_A": col_exists(df, ["Catégorie A", "Catégorie", "Categorie", "Categorie_A", "Catégorie_A"]),
        "Feux_habitations": col_exists(df, ["Feux d'habitations-bureaux", "Feux d'habitations bureaux"]),
        "Incendies": col_exists(df, ["Incendies"]),
        "Secours_victime": col_exists(df, ["Secours à victime", "Secours_victime"]),
        "Secours_personne": col_exists(df, ["Secours à personne", "Secours_personne"]),
        "Malaises_Urgence": col_exists(df, ["Malaises à domicile : urgence vitale"]),
        "Malaises_Carence": col_exists(df, ["Malaises à domicile : carence"]),
        "Accidents_circulation": col_exists(df, ["Accidents de circulation"]),
        "Operations_diverses": col_exists(df, ["Opérations diverses"]),
        "Total_interventions": col_exists(df, ["Total interventions"])
    }

    # normalize columns
    for norm_key, found in mapping.items():
        if found is None:
            # Create placeholder
            df[norm_key] = 0 if "Total" in norm_key or "Malaises" in norm_key or "_" in norm_key else ""
            mapping[norm_key] = norm_key
        else:
            if found != norm_key:
                df = df.rename(columns={found: norm_key})
            mapping[norm_key] = norm_key

    # numeric columns
    numeric_cols = [
        "Feux_habitations", "Incendies", "Secours_victime", "Secours_personne",
        "Malaises_Urgence", "Malaises_Carence", "Accidents_circulation",
        "Operations_diverses", "Total_interventions"
    ]

    for c in numeric_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    # Derived
    df["Total_Malaises"] = df["Malaises_Urgence"] + df["Malaises_Carence"]

    # Ensure text columns exist and are strings
    for txt in ["Region", "Departement", "Categorie_A", "Zone", "Numero"]:
        if txt not in df.columns:
            df[txt] = ""
        df[txt] = df[txt].astype(str).str.strip().replace({"nan": "", "None": ""})

    # Departement code extraction
    df["Departement_str"] = df["Departement"].astype(str).str.extract(r"(\d+)").fillna("")

    return df

# -----------------------
# Load
# -----------------------
df_raw = load_data()

# -----------------------
# Sidebar filters (ROBUST FINAL VERSION)
# -----------------------
st.sidebar.title("Filtres")

def safe_unique(df, col):
    if col not in df.columns:
        return ["Toutes"]
    return ["Toutes"] + sorted(df[col].replace("", "Non renseignée").unique().tolist())

regions = safe_unique(df_raw, "Region")
zones = safe_unique(df_raw, "Zone")
cats = safe_unique(df_raw, "Categorie_A")

sel_region = st.sidebar.selectbox("Région", regions)
sel_zone = st.sidebar.selectbox("Zone", zones)
sel_cat = st.sidebar.selectbox("Catégorie", cats)

df = df_raw.copy()
if sel_region != "Toutes":
    df = df[df["Region"].fillna("Non renseignée") == sel_region]
if sel_zone != "Toutes":
    df = df[df["Zone"].fillna("Non renseignée") == sel_zone]
if sel_cat != "Toutes":
    df = df[df["Categorie_A"].fillna("Non renseignée") == sel_cat]

# -----------------------
# Top nav
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
# Metrics
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
pct_inc = pct(incendies, total_inter)
pct_car = pct(car, mal if mal > 0 else 1)

# -----------------------
# Pages
# -----------------------
if st.session_state.page == "Overview":
    st.header("Vue d'ensemble")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total interventions", f"{int(total_inter):,}".replace(",", " "))
    c2.metric("Urgences médicales", f"{pct_medical:.0f}%")
    c3.metric("Incendies", f"{pct_inc:.1f}%")
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

    fig = px.pie(
        values=list(vals.values()),
        names=list(vals.keys()),
        hole=0.45,
        color_discrete_sequence=px.colors.sequential.Reds
    )
    fig.update_traces(textinfo="percent+label", textposition="outside")
    st.plotly_chart(fig, use_container_width=True)

elif st.session_state.page == "Interventions":
    st.header("Interventions — Top départements")

    metric = st.selectbox(
        "Choisir métrique",
        [
            ("Total interventions", "Total_interventions"),
            ("Incendies", "Incendies"),
            ("Secours victime", "Secours_victime"),
            ("Secours personne", "Secours_personne")
        ],
        format_func=lambda x: x[0]
    )
    metric_key = metric[1]
    topn = st.slider("Top N", 5, 20, 10)

    top_df = df.groupby("Departement").agg({metric_key: "sum"}).reset_index()
    top_df = top_df.nlargest(topn, metric_key)

    fig = px.bar(
        top_df,
        x=metric_key,
        y="Departement",
        orientation="h",
        color=metric_key,
        color_continuous_scale="Reds"
    )
    st.plotly_chart(fig, use_container_width=True)

elif st.session_state.page == "Carences":
    st.header("Carences ambulancières")

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=["Urgence vitale", "Carence"],
        y=[df["Malaises_Urgence"].sum(), df["Malaises_Carence"].sum()]
    ))
    fig.update_layout(yaxis_title="Nombre")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.subheader("Taux de carences par région")

    reg_df = df_raw.groupby("Region").agg({
        "Malaises_Carence": "sum",
        "Total_Malaises": "sum"
    }).reset_index()

    reg_df["Taux"] = (reg_df["Malaises_Carence"] /
                      reg_df["Total_Malaises"].replace(0, np.nan) * 100).fillna(0)

    reg_df = reg_df.sort_values("Taux", ascending=False)

    fig2 = px.bar(
        reg_df.head(20),
        x="Taux",
        y="Region",
        orientation="h",
        color="Taux",
        color_continuous_scale="Reds"
    )
    st.plotly_chart(fig2, use_container_width=True)

elif st.session_state.page == "Carte":
    st.header("Carte choroplèthe — départements")

    geojson = None
    if os.path.exists("departements.geojson"):
        with open("departements.geojson", "r", encoding="utf-8") as f:
            geojson = json.load(f)
    else:
        try:
            url = "https://raw.githubusercontent.com/gregoiredavid/france-geojson/master/departements-version-simplifiee.geojson"
            r = requests.get(url, timeout=8)
            if r.status_code == 200:
                geojson = r.json()
        except Exception:
            pass

    if geojson is None:
        st.info("GeoJSON non disponible. Ajoute 'departements.geojson' au dossier.")
    else:
        df_map = df_raw.copy()
        df_map["dept"] = df_map["Departement"].astype(str).str.extract(r"(\d+)").fillna("")

        agg = df_map.groupby("dept").agg({
            "Malaises_Carence": "sum",
            "Total_Malaises": "sum"
        }).reset_index()

        agg["taux"] = (agg["Malaises_Carence"] /
                       agg["Total_Malaises"].replace(0, np.nan) * 100).fillna(0)

        plotted = False
        for fk in ["properties.code", "properties.code_insee", "id"]:
            try:
                fig = px.choropleth(
                    agg,
                    geojson=geojson,
                    locations="dept",
                    color="taux",
                    featureidkey=fk,
                    color_continuous_scale="Reds"
                )
                fig.update_geos(fitbounds="locations", visible=False)
                fig.update_layout(margin=0, height=650)
                st.plotly_chart(fig, use_container_width=True)
                plotted = True
                break
            except Exception:
                continue

        if not plotted:
            st.error("Impossible d'aligner les codes département du GeoJSON et vos données.")

elif st.session_state.page == "Conclusion":
    st.header("Conclusion")
    st.write("Dashboard terminé. Améliorations possibles : données ambulancières, GeoJSON local, horaires de garde.")

# Footer
st.markdown("---")
st.caption("Projet EFREI - Pompiers France 2023")
