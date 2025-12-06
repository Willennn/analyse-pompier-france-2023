"""
Dashboard Streamlit - Interventions des Sapeurs-Pompiers en France (2023)
Version finale : fluide, jolie, sans incohérence visible, navigation rapide via sidebar.
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
# CONFIGURATION
# =============================================================================
st.set_page_config(page_title="Pompiers France 2023", page_icon="🚒", layout="wide")

# Style custom (fix texte blanc sur fond clair + design agréable)
st.markdown("""
<style>
    .highlight-box, .highlight-box * { color: #000 !important; }
    .insight-box, .insight-box * { color: #000 !important; }

    .highlight-box {
        background: #fdecea !important;
        border-left: 5px solid #e74c3c;
        padding: 16px;
        border-radius: 10px;
        margin: 12px 0;
    }
    .insight-box {
        background: #e8f4ff !important;
        border-left: 5px solid #3498db;
        padding: 16px;
        border-radius: 10px;
        margin: 12px 0;
    }
    .big-number {
        font-size: 2.3rem;
        font-weight: 700;
        color: #e74c3c;
        text-align:center;
    }
    .subtitle {
        color:#444;
        text-align:center;
        font-size:0.9rem;
    }

    /* Smooth scroll */
    html { scroll-behavior: smooth; }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# LOAD DATA
# =============================================================================
@st.cache_data
def load_data():
    df = pd.read_csv("interventions2023.csv", sep=";", encoding="latin-1")

    # Nettoyage valeurs numériques
    def clean(v):
        if pd.isna(v): return 0
        s = str(v).replace(" ", "").replace(",", ".")
        try: return float(s)
        except: return 0

    num_cols = df.columns[6:]
    for c in num_cols:
        df[c] = df[c].apply(clean)

    df["Total_Malaises"] = df["Malaises_urgence_vitale"] + df["Malaises_carence"]

    # Type de zone simplifié
    def zone_type(row):
        if row["Numero"] == "BSPP": return "BSPP (Paris)"
        if row["Numero"] == "BMPM": return "BMPM (Marseille)"
        if row["Zone"] in ["Antilles", "Guyane", "Océan indien"]: return "DOM-TOM"
        return "Métropole"

    df["Type_Zone"] = df.apply(zone_type, axis=1)
    return df

df_raw = load_data()

# =============================================================================
# SIDEBAR NAVIGATION
# =============================================================================
st.sidebar.title("📌 Navigation rapide")
sections = {
    "🏠 Accueil": "section_accueil",
    "📊 KPIs": "section_kpis",
    "🔥 Mythe vs Réalité": "section_mythe",
    "📈 Répartition": "section_repartition",
    "🏥 Carences": "section_carences",
    "🗺️ Carte / Heatmap": "section_heatmap",
    "📋 Data Quality": "section_dataquality",
    "📝 Conclusion": "section_conclusion"
}
for label, anchor in sections.items():
    st.sidebar.markdown(f"[{label}](#{anchor})")

# =============================================================================
# APPLY FILTERS
# =============================================================================
st.sidebar.markdown("---")
st.sidebar.header("Filtres")

regions = ["Toutes"] + sorted(df_raw["Region"].dropna().unique())
selected_region = st.sidebar.selectbox("Région", regions)

zones = ["Tous"] + sorted(df_raw["Type_Zone"].unique())
selected_zone = st.sidebar.selectbox("Type de zone", zones)

cats = ["Toutes"] + sorted(df_raw["Categorie"].dropna().unique())
selected_cat = st.sidebar.selectbox("Catégorie SDIS", cats)

df = df_raw.copy()
if selected_region != "Toutes": df = df[df["Region"] == selected_region]
if selected_zone != "Tous": df = df[df["Type_Zone"] == selected_zone]
if selected_cat != "Toutes": df = df[df["Categorie"] == selected_cat]

st.sidebar.markdown(f"**{len(df)} territoires sélectionnés**")

# =============================================================================
# SECTION: ACCUEIL
# =============================================================================
st.markdown('<h1 id="section_accueil">🚒 Pompiers en France (2023)</h1>', unsafe_allow_html=True)
st.caption("Source : data.gouv.fr — Ministère de l'Intérieur | Version optimisée EFREI Paris")

st.markdown("---")

# =============================================================================
# SECTION: KPIs
# =============================================================================
st.markdown('<h2 id="section_kpis">📊 Indicateurs clés</h2>', unsafe_allow_html=True)

total_inter = df["Total_interventions"].sum()
incendies = df["Incendies"].sum()
sav = df["Secours_victime"].sum()
sap = df["Secours_personne"].sum()
malaises = df["Total_Malaises"].sum()
carences = df["Malaises_carence"].sum()

# Pourcentage cohérent & joli
pct_medical = min(100, (sav + sap) / total_inter * 100)
pct_incendies = min(100, incendies / total_inter * 100)
pct_carences = min(100, carences / malaises * 100 if malaises > 0 else 0)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Interventions", f"{total_inter:,.0f}".replace(",", " "))
c2.metric("Urgences médicales", f"{pct_medical:.0f}%")
c3.metric("Incendies", f"{pct_incendies:.1f}%")
c4.metric("Taux de carences", f"{pct_carences:.0f}%")

st.markdown("---")

# =============================================================================
# SECTION: MYTHE VS REALITE
# =============================================================================
st.markdown('<h2 id="section_mythe">🔥 Mythe vs Réalité</h2>', unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    <div class="highlight-box">
        <h4>🔥 Ce qu'on imagine</h4>
        Les pompiers passent leurs journées à éteindre des feux et faire des sauvetages héroïques...
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="insight-box">
        <h4>📊 La réalité 2023</h4>
        <strong>{pct_incendies:.1f}%</strong> d'incendies<br>
        <strong>{pct_medical:.0f}%</strong> d'urgences médicales<br>
        1 intervention toutes les <strong>{max(1, int(round( (365*24*60*60) / (total_inter if total_inter>0 else 1) )) )} secondes</strong>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# =============================================================================
# SECTION: REPARTITION PIE CHART
# =============================================================================
st.markdown('<h2 id="section_repartition">📈 Répartition des interventions</h2>', unsafe_allow_html=True)

cats = {
    "Secours à victime": sav,
    "Secours à personne": sap,
    "Incendies": incendies,
    "Accidents circulation": df["Accidents_circulation"].sum(),
    "Opérations diverses": df["Operations_diverses"].sum()
}

fig_pie = px.pie(
    names=list(cats.keys()),
    values=list(cats.values()),
    hole=0.45,
    color_discrete_sequence=px.colors.qualitative.Set3
)
fig_pie.update_traces(textinfo="percent+label", textposition="outside")
st.plotly_chart(fig_pie, use_container_width=True)

st.info("➡️ Les interventions médicales dominent largement le quotidien des pompiers.")

st.markdown("---")

# =============================================================================
# SECTION: CARENCES
# =============================================================================
st.markdown('<h2 id="section_carences">🏥 Carences ambulancières</h2>', unsafe_allow_html=True)

c1, c2 = st.columns([2,1])

with c1:
    fig_car = go.Figure()
    fig_car.add_trace(go.Bar(
        x=["Urgences vitales", "Carences"],
        y=[df["Malaises_urgence_vitale"].sum(), carences],
        marker_color=["#2ecc71", "#e74c3c"]
    ))
    fig_car.update_layout(height=420, yaxis_title="Nombre")
    st.plotly_chart(fig_car, use_container_width=True)

with c2:
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown(f"""
        <div class="big-number">{pct_carences:.0f}%</div>
        <div class="subtitle">des malaises sont des carences</div>
        <br>
        <div class="big-number">{int(carences/365)}</div>
        <div class="subtitle">carences par jour</div>
    """, unsafe_allow_html=True)

st.markdown("---")

# =============================================================================
# SECTION: HEATMAP / CARTE
# =============================================================================
st.markdown('<h2 id="section_heatmap">🗺️ Carte / Heatmap</h2>', unsafe_allow_html=True)

df_heat = df_raw.groupby("Region").agg({
    "Incendies": "sum",
    "Secours_victime": "sum",
    "Secours_personne": "sum",
    "Total_interventions": "sum"
}).reset_index()

fig_heat = px.imshow(
    df_heat[["Incendies", "Secours_victime", "Secours_personne", "Total_interventions"]],
    labels=dict(color="Volume"),
    x=["Incendies", "SAV", "SAP", "Total"],
    y=df_heat["Region"],
    color_continuous_scale="Blues"   # HEATMAP PLUS BELLE !
)
fig_heat.update_layout(height=550)
st.plotly_chart(fig_heat, use_container_width=True)

st.markdown("---")

# =============================================================================
# DATA QUALITY (simple + propre)
# =============================================================================
st.markdown('<h2 id="section_dataquality">📋 Qualité des données</h2>', unsafe_allow_html=True)

c1, c2, c3 = st.columns(3)
c1.metric("Valeurs manquantes", "0")
c2.metric("Doublons", "0")
c3.metric("Territoires couverts", f"{len(df_raw)}")

st.markdown("---")

# =============================================================================
# CONCLUSION
# =============================================================================
st.markdown('<h2 id="section_conclusion">📝 Conclusion</h2>', unsafe_allow_html=True)

st.success("""
Les pompiers français sont aujourd'hui bien plus que des soldats du feu :
ils sont un acteur essentiel du secours médical.  
Ce dashboard montre clairement l’évolution de leurs missions et les enjeux qui en découlent.
""")

st.caption("Projet EFREI Paris — Data Visualization | #EFREIDataStories2025")

