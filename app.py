# =============================================================================
# IMPORTS
# =============================================================================
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import json
import os
import requests
from typing import Optional

# =============================================================================
# CONFIG
# =============================================================================
st.set_page_config(page_title="Pompiers France 2023", layout="wide", initial_sidebar_state="expanded")

# Style global (sobriété, pas d'émojis, top nav)
st.markdown(
    """
    <style>
    /* Top nav style */
    .topnav {
        display:flex;
        gap:12px;
        align-items:center;
        padding:12px 0;
        border-bottom:1px solid #eee;
        margin-bottom:18px;
    }
    .nav-btn {
        padding:8px 14px;
        border-radius:8px;
        cursor:pointer;
        font-weight:600;
    }
    .nav-btn.active {
        background: linear-gradient(90deg,#e74c3c,#c0392b);
        color: #fff;
        box-shadow: 0 6px 18px rgba(199,32,47,0.12);
    }
    .nav-btn.inactive {
        background: transparent;
        color: #111;
        border: 1px solid transparent;
    }

    /* KPI cards */
    .kpi {
        background:#ffffff;
        border-radius:10px;
        padding:14px;
        box-shadow: 0 6px 18px rgba(15,15,15,0.03);
    }
    .kpi-title { font-size:0.9rem; color:#555; }
    .kpi-value { font-size:1.6rem; font-weight:700; color:#111; }

    /* minor text */
    .muted { color:#666; font-size:0.9rem; }

    /* ensure charts full width responsiveness */
    .element-container { padding-top:6px; padding-bottom:6px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# =============================================================================
# UTIL: Column name resolver (tolérant)
# =============================================================================
def find_col(df: pd.DataFrame, candidates: list[str]) -> Optional[str]:
    """Return first matching column in df from candidates (case-insensitive, accent tolerant)."""
    cols = {c.lower().replace("é", "e").replace("è", "e").replace("à", "a").replace("ô", "o"): c for c in df.columns}
    for cand in candidates:
        key = cand.lower().replace("é", "e").replace("è", "e").replace("à", "a").replace("ô", "o")
        if key in cols:
            return cols[key]
    return None

# =============================================================================
# LOAD DATA (robuste)
# =============================================================================
@st.cache_data
def load_data(path="interventions2023.csv"):
    # Try multiple encodings
    tried = []
    df = None
    for enc in ("latin-1", "utf-8", "cp1252"):
        try:
            df = pd.read_csv(path, sep=";", encoding=enc)
            break
        except Exception as e:
            tried.append((enc, str(e)))
    if df is None:
        raise RuntimeError(f"Impossible de lire {path}. Tentatives: {tried}")

    # Normalize column names (strip)
    df.columns = [c.strip() for c in df.columns]

    # Map important columns with fallbacks
    col_map = {}
    col_map["Annee"] = find_col(df, ["Annee", "Année", "annee"])
    col_map["Region"] = find_col(df, ["Region", "Région", "region"])
    col_map["Numero"] = find_col(df, ["Numero", "N°", "Numero SDIS", "numero"])
    col_map["Departement"] = find_col(df, ["Departement", "Département", "departement"])
    col_map["Categorie"] = find_col(df, ["Categorie", "Catégorie", "categorie"])
    # numeric fields (many possibilities)
    col_map["Secours_victime"] = find_col(df, ["Secours_victime", "Secours victime", "secours_victime", "secours_victime"])
    col_map["Secours_personne"] = find_col(df, ["Secours_personne", "Secours personne", "secours_personne"])
    col_map["Incendies"] = find_col(df, ["Incendies", "incendies", "Incendie", "incendie"])
    col_map["Malaises_urgence_vitale"] = find_col(df, ["Malaises_urgence_vitale", "Malaises urgence vitale", "Malaises_urgence"])
    col_map["Malaises_carence"] = find_col(df, ["Malaises_carence", "Malaises carence", "carences", "Malaises_carence"])
    col_map["Total_interventions"] = find_col(df, ["Total_interventions", "Total interventions", "Total_interventions"])
    col_map["Type_Zone"] = find_col(df, ["Zone", "Type_Zone", "Type zone", "zone"])

    # Ensure columns exist in df; if a numeric column is missing, create it with zeros
    numeric_defaults = ["Secours_victime", "Secours_personne", "Incendies", "Malaises_urgence_vitale", "Malaises_carence", "Total_interventions"]
    for key in numeric_defaults:
        col = col_map.get(key)
        if col is None:
            df[key] = 0
            col_map[key] = key  # refers to column just created
        else:
            # rename df internal to normalized key for simplicity
            df.rename(columns={col: key}, inplace=True)
            col_map[key] = key

    # Normalize / clean numeric columns
    def clean_num(s):
        if pd.isna(s): return 0.0
        if isinstance(s, (int, float)): return float(s)
        st_ = str(s).strip().replace(" ", "").replace("\xa0", "").replace(",", ".")
        try:
            return float(st_)
        except:
            return 0.0

    for k in numeric_defaults:
        df[k] = df[k].apply(clean_num)

    # Ensure textual columns exist
    for txt in ["Region", "Departement", "Categorie", "Numero", "Zone"]:
        if txt not in df.columns:
            df[txt] = df.get(txt, "")

    # Derived columns
    df["Total_Malaises"] = df["Malaises_urgence_vitale"] + df["Malaises_carence"]
    # Add Type_Zone if not present
    if "Type_Zone" not in df.columns:
        def detect_zone(row):
            num = str(row.get("Numero", "")).upper()
            zone = str(row.get("Zone", ""))
            if num == "BSPP": return "BSPP (Paris)"
            if num == "BMPM": return "BMPM (Marseille)"
            if zone.lower() in ["antilles", "guyane", "ocean indien", "océan indien"]:
                return "DOM-TOM"
            return "Metropole"
        df["Type_Zone"] = df.apply(detect_zone, axis=1)

    return df

# Load dataset
df_raw = load_data()

# =============================================================================
# SIDEBAR FILTERS (persist across pages)
# =============================================================================
st.sidebar.title("Filtres")
regions = ["Toutes"] + sorted(df_raw["Region"].dropna().unique().tolist())
sel_region = st.sidebar.selectbox("Région", regions)

types_zone = ["Tous"] + sorted(df_raw["Type_Zone"].dropna().unique().tolist())
sel_zone = st.sidebar.selectbox("Type de territoire", types_zone)

cats = ["Toutes"] + sorted(df_raw["Categorie"].dropna().unique().tolist())
sel_cat = st.sidebar.selectbox("Catégorie SDIS", cats)

# apply filters
df = df_raw.copy()
if sel_region != "Toutes":
    df = df[df["Region"] == sel_region]
if sel_zone != "Tous":
    df = df[df["Type_Zone"] == sel_zone]
if sel_cat != "Toutes":
    df = df[df["Categorie"] == sel_cat]

# =============================================================================
# TOP NAV (simulate multipage with clear top bar)
# =============================================================================
PAGES = ["Overview", "Interventions", "Carences", "Carte", "Data Quality", "Conclusion"]
# maintain state
if "page" not in st.session_state:
    st.session_state.page = "Overview"

# Render top nav
cols = st.columns([1,1,1,1,1,1])
for i, p in enumerate(PAGES):
    active = "active" if st.session_state.page == p else "inactive"
    if cols[i].button(p, key=f"nav_{p}"):
        st.session_state.page = p

st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

# =============================================================================
# COMMON METRICS (bounded to 0-100 for percents)
# =============================================================================
total_inter = df["Total_interventions"].sum()
incendies = df["Incendies"].sum()
sav = df["Secours_victime"].sum()
sap = df["Secours_personne"].sum()
malaises = df["Total_Malaises"].sum()
carences = df["Malaises_carence"].sum()

def pct_safe(n, d):
    if d <= 0: return 0.0
    return float(min(100.0, max(0.0, (n / d) * 100.0)))

pct_medical = pct_safe(sav + sap, max(total_inter, 1))
pct_incendies = pct_safe(incendies, max(total_inter, 1))
pct_carences = pct_safe(carences, max(malaises, 1))

# =============================================================================
# PAGE: OVERVIEW
# =============================================================================
if st.session_state.page == "Overview":
    st.header("Résumé — Indicateurs clés")
    k1, k2, k3, k4 = st.columns(4)
    k1.markdown("<div class='kpi'><div class='kpi-title'>Total interventions (sélection)</div>"
                f"<div class='kpi-value'>{int(total_inter):,}</div></div>".replace(",", " "), unsafe_allow_html=True)
    k2.markdown("<div class='kpi'><div class='kpi-title'>Part urgences médicales</div>"
                f"<div class='kpi-value'>{pct_medical:.0f}%</div></div>", unsafe_allow_html=True)
    k3.markdown("<div class='kpi'><div class='kpi-title'>Part incendies</div>"
                f"<div class='kpi-value'>{pct_incendies:.1f}%</div></div>", unsafe_allow_html=True)
    k4.markdown("<div class='kpi'><div class='kpi-title'>Taux carences (malaises)</div>"
                f"<div class='kpi-value'>{pct_carences:.0f}%</div></div>", unsafe_allow_html=True)

    st.markdown("### Synthèse")
    st.write(
        "Ce dashboard présente une synthèse des interventions réalisées en 2023. "
        "Utilisez la barre de filtres à gauche pour explorer par région, type de territoire ou catégorie SDIS."
    )

    st.markdown("---")
    st.subheader("Répartition générale")
    small = {
        "Secours à victime": sav,
        "Secours à personne": sap,
        "Incendies": incendies,
        "Accidents circulation": df["Accidents_circulation"].sum(),
        "Opérations diverses": df["Operations_diverses"].sum()
    }
    fig = px.pie(names=list(small.keys()), values=list(small.values()), hole=0.4,
                 color_discrete_sequence=px.colors.sequential.RdBu)
    fig.update_traces(textinfo="percent+label", textposition="outside")
    st.plotly_chart(fig, use_container_width=True)

# =============================================================================
# PAGE: INTERVENTIONS
# =============================================================================
elif st.session_state.page == "Interventions":
    st.header("Interventions — Tendances & Top")
    # Timeline by departement or by year if present
    years = sorted(df_raw["Annee"].dropna().unique().tolist())
    if len(years) > 1:
        st.subheader("Tendance par année")
        df_year = df_raw.groupby("Annee").agg({"Total_interventions": "sum", "Incendies": "sum"}).reset_index()
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_year["Annee"], y=df_year["Total_interventions"], mode="lines+markers", name="Total"))
        fig.add_trace(go.Scatter(x=df_year["Annee"], y=df_year["Incendies"], mode="lines+markers", name="Incendies"))
        fig.update_layout(height=420, xaxis_title="Année", yaxis_title="Nombre")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Données disponibles pour une seule année — la timeline n'est pas affichée.")

    st.markdown("---")
    st.subheader("Top départements (choisir métrique)")
    metric = st.selectbox("Métrique", options=[
        ("Carences", "Malaises_carence"),
        ("Incendies", "Incendies"),
        ("Secours victime", "Secours_victime"),
        ("Total interventions", "Total_interventions")
    ], format_func=lambda x: x[0])
    metric_key = metric[1]
    topn = st.slider("Top N", 5, 25, 10)
    df_top = df.groupby("Departement").agg({metric_key: "sum"}).reset_index().nlargest(topn, metric_key)
    fig_top = px.bar(df_top, x=metric_key, y="Departement", orientation="h", color=metric_key, color_continuous_scale="Reds")
    st.plotly_chart(fig_top, use_container_width=True)

# =============================================================================
# PAGE: CARENCES
# =============================================================================
elif st.session_state.page == "Carences":
    st.header("Carences ambulancières — Analyse")
    st.markdown("Affichage synthétique des carences et de leur impact.")
    c1, c2 = st.columns([2,1])
    with c1:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=["Urgences vitales", "Carences"],
            y=[df["Malaises_urgence_vitale"].sum(), df["Malaises_carence"].sum()],
            marker_color=["#2ecc71", "#e74c3c"]
        ))
        fig.update_layout(height=420, yaxis_title="Nombre")
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.markdown("<div class='kpi'><div class='kpi-title'>Carences (total)</div>"
                    f"<div class='kpi-value'>{int(df['Malaises_carence'].sum()):,}</div></div>".replace(",", " "), unsafe_allow_html=True)
        st.markdown("<div class='muted'>Carences par jour</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='font-size:1.3rem; font-weight:600'>{int(df['Malaises_carence'].sum()/365):,}</div>".replace(",", " "), unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("Taux de carences par région")
    df_reg = df_raw.groupby("Region").agg({"Malaises_carence":"sum","Total_Malaises":"sum"}).reset_index()
    df_reg["Taux"] = (df_reg["Malaises_carence"] / df_reg["Total_Malaises"].replace(0, np.nan) * 100).fillna(0)
    df_reg = df_reg.sort_values("Taux", ascending=False)
    fig = px.bar(df_reg.head(20), x="Taux", y="Region", orientation="h", color="Taux", color_continuous_scale="Reds")
    st.plotly_chart(fig, use_container_width=True)

# =============================================================================
# PAGE: CARTE (CHOROPLETH)
# =============================================================================
elif st.session_state.page == "Carte":
    st.header("Carte choroplèthe — Taux de carences par département")

    # Try to load local geojson first
    geojson_path = "departements.geojson"
    geojson = None
    if os.path.exists(geojson_path):
        with open(geojson_path, "r", encoding="utf-8") as f:
            geojson = json.load(f)
    else:
        # Try to fetch a common simplified departments geojson from GitHub (if internet available)
        try:
            url = "https://raw.githubusercontent.com/gregoiredavid/france-geojson/master/departements-version-simplifiee.geojson"
            r = requests.get(url, timeout=8)
            if r.status_code == 200:
                geojson = r.json()
        except Exception:
            geojson = None

    if geojson is None:
        st.warning("GeoJSON des départements introuvable localement. Si vous voulez la carte, placez 'departements.geojson' dans le dossier de l'app ou activez Internet.")
        st.info("Astuce : un fichier couramment utilisé est 'departements-version-simplifiee.geojson'.")
    else:
        # prepare data: need department codes (numero)
        # Attempt to find department column in data
        dep_col = find_col(df_raw, ["Departement", "Département", "departement", "code_departement", "dept"])
        if dep_col is None:
            st.error("Impossible d'identifier la colonne département dans les données.")
        else:
            # create aggregation by department (ensure string codes)
            # sometimes dept values include name; we'll try to extract numeric code if possible
            df_map = df_raw[[dep_col, "Malaises_carence", "Total_Malaises"]].copy()
            df_map[dep_col] = df_map[dep_col].astype(str).str.strip()
            # try to keep only first two characters if numeric
            def extract_code(s):
                s0 = s.split()[0]
                s0 = s0.replace("0", "0")  # placeholder
                digits = "".join([c for c in s0 if c.isdigit()])
                return digits if digits != "" else s
            df_map["dept_code"] = df_map[dep_col].apply(extract_code)
            agg = df_map.groupby("dept_code").agg({
                "Malaises_carence":"sum",
                "Total_Malaises":"sum"
            }).reset_index()
            agg["taux"] = (agg["Malaises_carence"] / agg["Total_Malaises"].replace(0, np.nan) * 100).fillna(0)

            # Plot choropleth
            try:
                fig = px.choropleth(agg,
                                    geojson=geojson,
                                    locations="dept_code",
                                    color="taux",
                                    color_continuous_scale="Reds",
                                    featureidkey="properties.code")  # many french geojson use properties.code or code
                fig.update_geos(fitbounds="locations", visible=False)
                fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=700)
                st.plotly_chart(fig, use_container_width=True)
            except Exception:
                # fallback: try different feature key
                try:
                    fig = px.choropleth(agg,
                                        geojson=geojson,
                                        locations="dept_code",
                                        color="taux",
                                        color_continuous_scale="Reds",
                                        featureidkey="properties.code_insee")
                    fig.update_geos(fitbounds="locations", visible=False)
                    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=700)
                    st.plotly_chart(fig, use_container_width=True)
                except Exception:
                    st.error("Erreur lors du rendu de la carte. Le GeoJSON et les codes département doivent correspondre (vérifier 'properties.code' ou 'properties.code_insee').")

# =============================================================================
# PAGE: DATA QUALITY (soft)
# =============================================================================
elif st.session_state.page == "Data Quality":
    st.header("Qualité des données (vue synthétique)")
    st.markdown("Vue simplifiée — affichage professionnel (aucune mention publique d'incohérences).")
    missing_cells = int(df_raw.isna().sum().sum())
    dups = int(df_raw.duplicated().sum())
    st.metric("Valeurs manquantes (cells)", missing_cells)
    st.metric("Doublons (lignes)", dups)
    st.metric("Lignes (territoires)", len(df_raw))

    st.markdown("---")
    st.subheader("Quelques conseils (internes)")
    st.markdown("- Si vous ajoutez la carte, assurez-vous que les codes départements du GeoJSON correspondent aux valeurs dans la colonne 'Département' ou 'code'.\n- Conserver une version 'raw' des données pour toute reproduction.")

# =============================================================================
# PAGE: CONCLUSION
# =============================================================================
elif st.session_state.page == "Conclusion":
    st.header("Conclusion & recommandations")
    st.markdown(
        "Ce tableau de bord est prévu pour présenter des insights clairs et professionnels. "
        "Pour aller plus loin : intégrer horaires de garde, positionnement des ambulances, "
        "et enrichir la carte avec couches de distance / temps de trajet."
    )
    st.markdown("---")
    st.markdown("Crédits : Source data.gouv.fr — Ministère de l'Intérieur (2023). Projet étudiant - EFREI.")

# =============================================================================
# FOOTER
# =============================================================================
st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
st.markdown("<div class='muted'>Design sobre — couleurs : rouge / bleu. Pour assistance, fournis le GeoJSON ou demande l'ajout.</div>", unsafe_allow_html=True)
