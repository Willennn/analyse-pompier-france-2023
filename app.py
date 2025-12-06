import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import json
import requests
import os

# -------------------------------------------------------------------
# CONFIG
# -------------------------------------------------------------------
st.set_page_config(page_title="Pompiers France 2023", layout="wide")

# -------------------------------------------------------------------
# LOAD DATA
# -------------------------------------------------------------------
@st.cache_data
def load_data():
    df = pd.read_csv("interventions2023.csv", sep=";", encoding="latin-1")

    # Renommage des colonnes critiques pour simplifier le code
    df = df.rename(columns={
        "Année": "Annee",
        "Zone": "Zone",
        "Région": "Region",
        "Numéro": "Numero",
        "Département": "Departement",
        "Catégorie A": "Categorie",

        "Incendies": "Incendies",
        "Secours à victime": "Secours_victime",
        "Secours à personne": "Secours_personne",

        "Malaises à domicile : urgence vitale": "Malaises_Urgence",
        "Malaises à domicile : carence": "Malaises_Carence",

        "Accidents de circulation": "Accidents_circulation",
        "Opérations diverses": "Operations_diverses",
        "Total interventions": "Total_interventions"
    })

    # Convertir en numérique proprement
    cols_num = [
        "Incendies","Secours_victime","Secours_personne",
        "Malaises_Urgence","Malaises_Carence",
        "Accidents_circulation","Operations_diverses","Total_interventions"
    ]

    for c in cols_num:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    # Ajout variables propres
    df["Total_Malaises"] = df["Malaises_Urgence"] + df["Malaises_Carence"]

    # Type de zone (simple)
    def zone_type(row):
        if row["Numero"] == "BSPP": return "BSPP (Paris)"
        if row["Numero"] == "BMPM": return "BMPM (Marseille)"
        return "Métropole"

    df["Type_Zone"] = df.apply(zone_type, axis=1)

    return df

df_raw = load_data()

# -------------------------------------------------------------------
# SIDEBAR FILTERS
# -------------------------------------------------------------------
st.sidebar.title("Filtres")

regions = ["Toutes"] + sorted(df_raw["Region"].unique())
reg = st.sidebar.selectbox("Région", regions)

zones = ["Tous"] + sorted(df_raw["Type_Zone"].unique())
z_type = st.sidebar.selectbox("Type de zone", zones)

cats = ["Toutes"] + sorted(df_raw["Categorie"].unique())
cat = st.sidebar.selectbox("Catégorie", cats)

df = df_raw.copy()
if reg != "Toutes":
    df = df[df["Region"] == reg]
if z_type != "Tous":
    df = df[df["Type_Zone"] == z_type]
if cat != "Toutes":
    df = df[df["Categorie"] == cat]

# -------------------------------------------------------------------
# TOP NAV (MULTIPAGE SANS PAGES)
# -------------------------------------------------------------------
PAGES = ["Overview", "Interventions", "Carences", "Carte", "Conclusion"]
if "page" not in st.session_state:
    st.session_state.page = "Overview"

col1, col2, col3, col4, col5 = st.columns(5)
for c, p in zip([col1, col2, col3, col4, col5], PAGES):
    if c.button(p):
        st.session_state.page = p

st.write("---")

# -------------------------------------------------------------------
# KPIs COMMUNS
# -------------------------------------------------------------------
total_inter = df["Total_interventions"].sum()
incendies = df["Incendies"].sum()
sav = df["Secours_victime"].sum()
sap = df["Secours_personne"].sum()
mal = df["Total_Malaises"].sum()
car = df["Malaises_Carence"].sum()

pct_medical = min(100, (sav + sap) / max(total_inter, 1) * 100)
pct_incendies = min(100, incendies / max(total_inter, 1) * 100)
pct_car = min(100, car / max(mal, 1) * 100)

# -------------------------------------------------------------------
# PAGE - OVERVIEW
# -------------------------------------------------------------------
if st.session_state.page == "Overview":
    st.header("Vue d'ensemble")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Interventions", f"{total_inter:,.0f}".replace(",", " "))
    c2.metric("Part médicale", f"{pct_medical:.0f}%")
    c3.metric("Part incendies", f"{pct_incendies:.1f}%")
    c4.metric("Taux carences", f"{pct_car:.0f}%")

    st.subheader("Répartition générale")
    values = {
        "Secours à victime": sav,
        "Secours à personne": sap,
        "Incendies": incendies,
        "Accidents circulation": df["Accidents_circulation"].sum(),
        "Opérations diverses": df["Operations_diverses"].sum()
    }

    fig = px.pie(
        names=list(values.keys()),
        values=list(values.values()),
        hole=0.4,
        color_discrete_sequence=px.colors.sequential.Reds
    )
    st.plotly_chart(fig, use_container_width=True)

# -------------------------------------------------------------------
# PAGE - INTERVENTIONS
# -------------------------------------------------------------------
elif st.session_state.page == "Interventions":
    st.header("Analyse des interventions")

    st.subheader("Top départements")
    metric = st.selectbox("Métrique", [
        ("Incendies", "Incendies"),
        ("Secours victime", "Secours_victime"),
        ("Secours personne", "Secours_personne"),
        ("Interventions totales", "Total_interventions"),
    ], format_func=lambda x: x[0])

    metric_key = metric[1]
    top = df.groupby("Departement")[metric_key].sum().reset_index().nlargest(10, metric_key)

    fig = px.bar(top, x=metric_key, y="Departement", orientation="h", color=metric_key,
                 color_continuous_scale="Reds")
    st.plotly_chart(fig, use_container_width=True)

# -------------------------------------------------------------------
# PAGE - CARENCES
# -------------------------------------------------------------------
elif st.session_state.page == "Carences":
    st.header("Carences ambulancières")

    c1, c2 = st.columns([2,1])

    with c1:
        fig = px.bar(
            x=["Urgence vitale", "Carence"],
            y=[df["Malaises_Urgence"].sum(), df["Malaises_Carence"].sum()],
            color=["Urgence vitale", "Carence"],
            color_discrete_sequence=["#3498db", "#e74c3c"]
        )
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.metric("Taux carences", f"{pct_car:.0f}%")
        st.metric("Carences totales", f"{int(car):,}".replace(",", " "))

# -------------------------------------------------------------------
# PAGE - CARTE
# -------------------------------------------------------------------
elif st.session_state.page == "Carte":
    st.header("Carte choroplèthe — Taux de carences")

    # charger geojson france
    url = "https://raw.githubusercontent.com/gregoiredavid/france-geojson/master/departements-version-simplifiee.geojson"
    r = requests.get(url)
    geojson = r.json()

    # extraction code département
    df_map = df_raw.copy()
    df_map["dept"] = df_map["Departement"].astype(str).str.extract(r"(\d+)")
    df_map = df_map.groupby("dept")[["Malaises_Carence","Total_Malaises"]].sum().reset_index()
    df_map["taux"] = (df_map["Malaises_Carence"] / df_map["Total_Malaises"].replace(0, np.nan) * 100).fillna(0)

    fig = px.choropleth(
        df_map,
        geojson=geojson,
        locations="dept",
        featureidkey="properties.code",
        color="taux",
        color_continuous_scale="Reds"
    )
    fig.update_geos(fitbounds="locations", visible=False)
    st.plotly_chart(fig, use_container_width=True)

# -------------------------------------------------------------------
# PAGE - CONCLUSION
# -------------------------------------------------------------------
elif st.session_state.page == "Conclusion":
    st.header("Conclusion")
    st.write(
        "Ce tableau de bord présente une vision claire et synthétique "
        "des interventions des sapeurs-pompiers en France en 2023."
    )
