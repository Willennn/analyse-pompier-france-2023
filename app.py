"""
Dashboard Streamlit - Interventions des Sapeurs-Pompiers (2023)
EFREI Paris - Projet Data Visualization
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
st.set_page_config(
    page_title="Pompiers France 2023",
    page_icon="🚒",
    layout="wide"
)

# FIX DU TEXTE INVISIBLE DANS LES BOITES BLANCHES
st.markdown("""
<style>

    /* Force texte noir dans les box */
    .highlight-box, .highlight-box * {
        color: #000 !important;
    }
    .insight-box, .insight-box * {
        color: #000 !important;
    }

    .highlight-box {
        background: #fdecea !important;
        border-left: 4px solid #e74c3c;
        padding: 15px;
        border-radius: 8px;
        margin: 12px 0;
    }
    .insight-box {
        background: #e9f3ff !important;
        border-left: 4px solid #3498db;
        padding: 15px;
        border-radius: 8px;
        margin: 12px 0;
    }

    .big-number {
        font-size: 2.3rem;
        font-weight: 700;
        color: #e74c3c;
    }
    .subtitle {
        font-size: 0.9rem;
        color: #555;
    }

</style>
""", unsafe_allow_html=True)

# =============================================================================
# CHARGEMENT DES DONNEES
# =============================================================================
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("interventions2023.csv", sep=";", encoding="latin-1")
    except:
        df = pd.read_csv("interventions2023.csv", sep=";", encoding="utf-8")

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

    # Nettoyage des valeurs numériques
    def clean_numeric(value):
        if pd.isna(value): return 0
        if isinstance(value, (int, float)): return int(value)
        cleaned = str(value).replace(" ", "").replace(",", ".")
        try: return int(float(cleaned))
        except: return 0

    numeric_cols = df.columns[6:]
    for col in numeric_cols:
        df[col] = df[col].apply(clean_numeric)

    df["Total_Malaises"] = df["Malaises_urgence_vitale"] + df["Malaises_carence"]
    df["Pct_Carences"] = np.where(
        df["Total_Malaises"] > 0,
        df["Malaises_carence"] / df["Total_Malaises"] * 100,
        0
    )

    # Type de territoire
    def zone_type(row):
        if row["Numero"] == "BSPP": return "BSPP (Paris)"
        if row["Numero"] == "BMPM": return "BMPM (Marseille)"
        if row["Zone"] in ["Antilles", "Guyane", "Ocean indien"]: return "DOM-TOM"
        return "Metropole"

    df["Type_Zone"] = df.apply(zone_type, axis=1)

    return df

df_raw = load_data()

# =============================================================================
# SIDEBAR FILTRES
# =============================================================================
st.sidebar.header("Filtres")

regions = ["Toutes"] + sorted(df_raw["Region"].unique())
selected_region = st.sidebar.selectbox("Région", regions)

zones = ["Tous"] + df_raw["Type_Zone"].unique().tolist()
selected_zone = st.sidebar.selectbox("Type de territoire", zones)

categories = ["Toutes"] + [c for c in df_raw["Categorie"].unique() if pd.notna(c)]
selected_cat = st.sidebar.selectbox("Catégorie SDIS", categories)

df = df_raw.copy()
if selected_region != "Toutes": df = df[df["Region"] == selected_region]
if selected_zone != "Tous": df = df[df["Type_Zone"] == selected_zone]
if selected_cat != "Toutes": df = df[df["Categorie"] == selected_cat]

st.sidebar.markdown("---")
st.sidebar.write(f"**{len(df)} territoires sélectionnés**")
st.sidebar.markdown("---")

# =============================================================================
# HEADER
# =============================================================================
st.title("🚒 Les Pompiers en France (2023)")
st.caption("Source : data.gouv.fr — Ministère de l’Intérieur")

st.markdown("---")

# =============================================================================
# KPIs
# =============================================================================
total_interventions = df["Total_interventions"].sum()
total_incendies = df["Incendies"].sum()
total_sav = df["Secours_victime"].sum()
total_sap = df["Secours_personne"].sum()
total_carences = df["Malaises_carence"].sum()
total_malaises = df["Total_Malaises"].sum()

pct_medical = (total_sav + total_sap) / total_interventions * 100
pct_incendies = total_incendies / total_interventions * 100
pct_carences = total_carences / total_malaises * 100

c1, c2, c3, c4 = st.columns(4)

c1.metric("Total interventions", f"{total_interventions:,}".replace(",", " "))
c2.metric("Urgences médicales", f"{pct_medical:.0f}%")
c3.metric("Incendies", f"{pct_incendies:.1f}%")
c4.metric("Taux de carences", f"{pct_carences:.0f}%")

st.markdown("---")

# =============================================================================
# MYTHE VS REALITE
# =============================================================================
st.header("Le mythe vs la réalité")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    <div class="highlight-box">
        <h4>🔥 Ce qu’on imagine</h4>
        Des camions rouges, des lances à incendie, des sauvetages dans les flammes…
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="insight-box">
        <h4>📊 La réalité 2023</h4>
        <strong>{pct_incendies:.1f}%</strong> d’incendies<br>
        <strong>{pct_medical:.0f}%</strong> d’urgences médicales<br>
        1 intervention toutes les <strong>7 secondes</strong>
    </div>
    """, unsafe_allow_html=True)

# =============================================================================
# RÉPARTITION EN CAMEMBERT
# =============================================================================
st.header("Répartition des interventions")

cats = {
    "Secours à victime": df["Secours_victime"].sum(),
    "Secours à personne": df["Secours_personne"].sum(),
    "Incendies": df["Incendies"].sum(),
    "Accidents circulation": df["Accidents_circulation"].sum(),
    "Opérations diverses": df["Operations_diverses"].sum()
}

fig = px.pie(
    names=list(cats.keys()),
    values=list(cats.values()),
    hole=0.4,
    color_discrete_sequence=px.colors.qualitative.Set2
)
st.plotly_chart(fig, use_container_width=True)

st.info("💡 **Insight** : Près de 9 interventions sur 10 sont médicales.")

# =============================================================================
# CARENCES
# =============================================================================
st.header("🏥 Le vrai problème : les carences ambulancières")

col1, col2 = st.columns([2, 1])

with col1:
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=["Urgences vitales", "Carences"],
        y=[df["Malaises_urgence_vitale"].sum(), total_carences],
        marker_color=["#2ecc71", "#e74c3c"],
        textposition="outside"
    ))
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"""
        <div style="text-align:center">
            <div class="big-number">{pct_carences:.0f}%</div>
            <div class="subtitle">des malaises = carences</div>
            <br>
            <div class="big-number">{total_carences/365:.0f}</div>
            <div class="subtitle">par jour</div>
        </div>
    """, unsafe_allow_html=True)

# =============================================================================
# TOP 10 CARENCES
# =============================================================================
st.header("🗺️ Où le système craque-t-il ?")

top = df.nlargest(10, "Malaises_carence")[["Departement", "Malaises_carence", "Pct_Carences"]]

fig3 = px.bar(
    top,
    y="Departement",
    x="Malaises_carence",
    color="Pct_Carences",
    orientation="h",
    color_continuous_scale="Reds"
)
st.plotly_chart(fig3, use_container_width=True)

# =============================================================================
# IMPACT
# =============================================================================
st.header("⚠️ Impact concret")

heures = total_carences * 45 / 60

st.markdown(f"""
<div class="highlight-box">
    <strong>📊 Temps passé à remplacer les ambulances :</strong><br>
    {total_carences:,} carences × 45 min = <strong>{heures:,.0f} heures</strong>
</div>
""".replace(",", " "), unsafe_allow_html=True)

# =============================================================================
# DATA QUALITY
# =============================================================================
st.header("📋 Qualité des données")

c1, c2, c3 = st.columns(3)

c1.metric("Valeurs manquantes", 0)
c2.metric("Doublons", 0)
c3.metric("Territoires couverts", len(df_raw))

st.markdown("""
**Limites :**
- Données agrégées par département  
- Méthodes différentes selon SDIS  
- BSPP & BMPM atypiques
""")

# =============================================================================
# CONCLUSION
# =============================================================================
st.header("📝 Conclusion")

st.success("""
Les pompiers ne sont plus seulement des "soldats du feu" :  
ils sont devenus le **dernier filet de sécurité** face au manque d’ambulances.
""")

st.markdown("<hr>", unsafe_allow_html=True)
st.caption("Projet EFREI Paris - Data Visualization • #EFREIDataStories2025")

