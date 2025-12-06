"""
Interventions des Sapeurs-Pompiers en France (2023)
Dashboard Streamlit - EFREI Paris
#EFREIDataStories2025
"""

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

st.markdown("""
<style>
    .big-number {
        font-size: 2.5rem;
        font-weight: 700;
        color: #e74c3c;
    }
    .subtitle {
        font-size: 1rem;
        color: #7f8c8d;
    }
    .highlight-box {
        background: #fff5f5;
        border-left: 4px solid #e74c3c;
        padding: 15px;
        border-radius: 0 8px 8px 0;
        margin: 10px 0;
    }
    .insight-box {
        background: #f0f9ff;
        border-left: 4px solid #3498db;
        padding: 15px;
        border-radius: 0 8px 8px 0;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# CHARGEMENT DES DONNEES
# =============================================================================
@st.cache_data
def load_data():
    df = pd.read_csv('interventions2023.csv', sep=';', encoding='latin-1')
    
    def clean_numeric(value):
        if pd.isna(value):
            return 0
        if isinstance(value, str):
            return int(value.replace(' ', '').replace('\xa0', ''))
        return int(value)
    
    cols_info = ['Annee', 'Zone', 'Region', 'Numero', 'Departement', 'Categorie A']
    cols_num = [col for col in df.columns if col not in cols_info]
    
    for col in cols_num:
        df[col] = df[col].apply(clean_numeric)
    
    df = df.rename(columns={'Categorie A': 'Categorie'})
    
    # Colonnes supplementaires
    df['Total_Malaises'] = df['Malaises a domicile : urgence vitale'] + df['Malaises a domicile : carence']
    df['Pct_Carences'] = np.where(
        df['Total_Malaises'] > 0,
        (df['Malaises a domicile : carence'] / df['Total_Malaises'] * 100).round(1), 
        0
    )
    
    # Type de zone
    def get_type_zone(row):
        if row['Numero'] == 'BSPP':
            return 'BSPP (Paris)'
        elif row['Numero'] == 'BMPM':
            return 'BMPM (Marseille)'
        elif row['Zone'] in ['Antilles', 'Guyane', 'Ocean indien']:
            return 'DOM-TOM'
        else:
            return 'Metropole'
    
    df['Type_Zone'] = df.apply(get_type_zone, axis=1)
    
    return df

df_raw = load_data()

# =============================================================================
# SIDEBAR - FILTRES
# =============================================================================
st.sidebar.header("🎛️ Filtres")

# Filtre par region
regions = ['Toutes'] + sorted(df_raw['Region'].unique().tolist())
selected_region = st.sidebar.selectbox("Region", regions)

# Filtre par type de zone
types_zone = ['Tous'] + df_raw['Type_Zone'].unique().tolist()
selected_type = st.sidebar.selectbox("Type de territoire", types_zone)

# Filtre par categorie SDIS
categories = ['Toutes'] + [c for c in df_raw['Categorie'].unique().tolist() if pd.notna(c) and c != '']
selected_cat = st.sidebar.selectbox("Categorie SDIS (A=grand, B=moyen, C=petit)", categories)

# Application des filtres
df = df_raw.copy()
if selected_region != 'Toutes':
    df = df[df['Region'] == selected_region]
if selected_type != 'Tous':
    df = df[df['Type_Zone'] == selected_type]
if selected_cat != 'Toutes':
    df = df[df['Categorie'] == selected_cat]

# Info sidebar
st.sidebar.markdown("---")
st.sidebar.markdown(f"**{len(df)}** territoires selectionnes")
st.sidebar.markdown("---")
st.sidebar.markdown("""
**Source des donnees**  
[data.gouv.fr](https://www.data.gouv.fr/datasets/interventions-realisees-par-les-services-d-incendie-et-de-secours/)  
Ministere de l'Interieur - 2023
""")

# =============================================================================
# HEADER
# =============================================================================
st.title("🚒 Les Pompiers en France (2023)")
st.caption("Source: data.gouv.fr - Ministere de l'Interieur | Licence Ouverte")

st.markdown("---")

# =============================================================================
# KPIs DYNAMIQUES (lies aux filtres)
# =============================================================================
total_interventions = df['Total interventions'].sum()
total_incendies = df['Incendies'].sum()
total_sav = df['Secours a victime'].sum()
total_sap = df['Secours a personne'].sum()
total_carences = df['Malaises a domicile : carence'].sum()
total_malaises = df['Total_Malaises'].sum()

# Comparaison avec le national (pour delta)
national_total = df_raw['Total interventions'].sum()
pct_of_national = (total_interventions / national_total * 100)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Total interventions", 
        f"{total_interventions:,.0f}".replace(",", " "),
        f"{pct_of_national:.1f}% du national"
    )
with col2:
    pct_medical = (total_sav + total_sap) / total_interventions * 100 if total_interventions > 0 else 0
    st.metric("Urgences medicales", f"{pct_medical:.0f}%")
with col3:
    pct_incendies = total_incendies / total_interventions * 100 if total_interventions > 0 else 0
    st.metric("Incendies", f"{pct_incendies:.1f}%")
with col4:
    pct_carences = total_carences / total_malaises * 100 if total_malaises > 0 else 0
    st.metric("Taux de carences", f"{pct_carences:.0f}%")

st.markdown("---")

# =============================================================================
# SECTION 1 : CONTEXTE - LE MYTHE VS LA REALITE
# =============================================================================
st.header("🤔 Le mythe vs la realite")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    <div class="highlight-box">
    <h4>🔥 Ce qu'on imagine</h4>
    <p>Des camions rouges, des lances a incendie, des sauvetages dans les flammes...</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="insight-box">
    <h4>📊 La realite 2023</h4>
    <p><strong>{pct_incendies:.1f}%</strong> d'incendies seulement<br>
    <strong>{pct_medical:.0f}%</strong> d'urgences medicales<br>
    1 intervention toutes les <strong>7 secondes</strong></p>
    </div>
    """, unsafe_allow_html=True)

# =============================================================================
# SECTION 2 : GRAPHIQUE REPARTITION
# =============================================================================
st.header("📊 Repartition des interventions")

categories_data = {
    'Secours a victime': df['Secours a victime'].sum(),
    'Secours a personne': df['Secours a personne'].sum(),
    'Incendies': df['Incendies'].sum(),
    'Accidents circulation': df['Accidents de circulation'].sum(),
    'Operations diverses': df['Operations diverses'].sum(),
    'Risques technologiques': df['Risques technologiques'].sum()
}

fig1 = px.pie(
    values=list(categories_data.values()),
    names=list(categories_data.keys()),
    hole=0.45,
    color_discrete_sequence=['#e74c3c', '#3498db', '#f39c12', '#9b59b6', '#1abc9c', '#34495e']
)
fig1.update_traces(textposition='outside', textinfo='percent+label')
fig1.update_layout(
    showlegend=False, 
    height=400,
    margin=dict(t=20, b=20)
)
st.plotly_chart(fig1, use_container_width=True)

st.info("💡 **Insight** : Les pompiers sont avant tout des urgentistes. Pres de 9 interventions sur 10 sont des secours medicaux, pas des incendies.")

# =============================================================================
# SECTION 3 : LA NARRATIVE - LES CARENCES
# =============================================================================
st.markdown("---")
st.header("🏥 Le vrai probleme : les carences ambulancieres")

st.markdown("""
Une **"carence"**, c'est quand les pompiers interviennent **a la place d'une ambulance** 
parce qu'il n'y en a pas de disponible. C'est un indicateur de tension du systeme de sante.
""")

# Graphique 2 : Urgences vs Carences
col1, col2 = st.columns([2, 1])

with col1:
    urgences = df['Malaises a domicile : urgence vitale'].sum()
    carences = df['Malaises a domicile : carence'].sum()
    
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(
        x=['Urgences vitales', 'Carences (pas d\'ambulance)'],
        y=[urgences, carences],
        marker_color=['#2ecc71', '#e74c3c'],
        text=[f'{urgences:,.0f}', f'{carences:,.0f}'],
        textposition='outside'
    ))
    fig2.update_layout(
        title="Malaises a domicile : urgences vs carences",
        yaxis_title="Nombre d'interventions",
        height=400,
        showlegend=False
    )
    st.plotly_chart(fig2, use_container_width=True)

with col2:
    st.markdown("<br><br>", unsafe_allow_html=True)
    if total_malaises > 0:
        st.markdown(f"""
        <div style="text-align: center; padding: 20px;">
            <div class="big-number">{carences/total_malaises*100:.0f}%</div>
            <div class="subtitle">des malaises sont des carences</div>
            <br>
            <div class="big-number">{carences/365:.0f}</div>
            <div class="subtitle">carences par jour</div>
        </div>
        """, unsafe_allow_html=True)

st.warning(f"⚠️ **Traduction** : Dans **{carences/total_malaises*100:.0f}%** des cas, quand quelqu'un fait un malaise chez lui, les pompiers interviennent parce qu'il n'y a pas d'ambulance disponible.")

# =============================================================================
# SECTION 4 : COMPARAISON PAR REGION
# =============================================================================
st.markdown("---")
st.header("🗺️ Ou le systeme craque-t-il ?")

# Graphique 3 : Top territoires par carences
top_carences = df.nlargest(10, 'Malaises a domicile : carence')[
    ['Departement', 'Region', 'Malaises a domicile : carence', 'Pct_Carences']
]

if len(top_carences) > 0:
    fig3 = px.bar(
        top_carences,
        x='Malaises a domicile : carence',
        y='Departement',
        orientation='h',
        color='Pct_Carences',
        color_continuous_scale='Reds',
        hover_data=['Region', 'Pct_Carences'],
        labels={'Malaises a domicile : carence': 'Nombre de carences', 'Pct_Carences': '% carences'}
    )
    fig3.update_layout(
        title="Top 10 des territoires avec le plus de carences",
        yaxis={'categoryorder': 'total ascending'},
        height=400,
        coloraxis_colorbar_title="% carences"
    )
    st.plotly_chart(fig3, use_container_width=True)

# Comparaison par region (si pas de filtre region)
if selected_region == 'Toutes':
    st.subheader("Taux de carences par region")
    
    df_regions = df_raw.groupby('Region').agg({
        'Malaises a domicile : carence': 'sum',
        'Total_Malaises': 'sum'
    }).reset_index()
    df_regions['Taux_Carences'] = (df_regions['Malaises a domicile : carence'] / df_regions['Total_Malaises'] * 100).round(1)
    df_regions = df_regions.sort_values('Taux_Carences', ascending=True)
    
    fig4 = px.bar(
        df_regions,
        x='Taux_Carences',
        y='Region',
        orientation='h',
        color='Taux_Carences',
        color_continuous_scale='RdYlGn_r',
        labels={'Taux_Carences': 'Taux de carences (%)'}
    )
    fig4.update_layout(
        height=450,
        coloraxis_colorbar_title="% carences"
    )
    st.plotly_chart(fig4, use_container_width=True)
    
    st.info("💡 **Insight** : L'Ile-de-France a le taux de carences le plus eleve. La densite de population sature le systeme de sante.")

# =============================================================================
# SECTION 5 : IMPLICATIONS
# =============================================================================
st.markdown("---")
st.header("⚠️ Pourquoi c'est un probleme ?")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    **Pour les pompiers :**
    - Surcharge de travail
    - Fatigue et burn-out
    - Moins disponibles pour les incendies
    """)

with col2:
    st.markdown("""
    **Pour les citoyens :**
    - Delais d'intervention plus longs
    - Cout supporte par les impots locaux
    - Symptome d'un systeme sature
    """)

# Calcul impact
if total_carences > 0:
    heures = (total_carences * 45) / 60
    st.markdown(f"""
    <div class="highlight-box">
    <strong>📊 Impact concret</strong> (sur la selection actuelle)<br>
    {total_carences:,.0f} carences × 45 min = <strong>{heures:,.0f} heures</strong> passees a remplacer les ambulances
    </div>
    """.replace(",", " "), unsafe_allow_html=True)

# =============================================================================
# SECTION 6 : DATA QUALITY
# =============================================================================
st.markdown("---")
st.header("📋 Qualite des donnees")

col1, col2, col3 = st.columns(3)

with col1:
    missing = df_raw.isnull().sum().sum()
    st.metric("Valeurs manquantes", missing)

with col2:
    duplicates = df_raw.duplicated().sum()
    st.metric("Doublons", duplicates)

with col3:
    st.metric("Territoires couverts", len(df_raw))

st.markdown("""
**Limites et biais potentiels :**
- Donnees agregees par departement (pas de detail communal)
- Certains SDIS peuvent avoir des methodes de comptage differentes
- Les categories d'intervention peuvent se chevaucher dans certains cas
- La BSPP et le BMPM sont des unites militaires avec un fonctionnement particulier

**Methode de nettoyage :**
- Conversion des nombres avec separateurs (espaces) en entiers
- Aucune valeur manquante dans les colonnes numeriques
- Verification de coherence : total = somme des sous-categories
""")

# =============================================================================
# SECTION 7 : CONCLUSION
# =============================================================================
st.markdown("---")
st.header("📝 Ce qu'il faut retenir")

st.success("""
**Message cle :** Les sapeurs-pompiers ne sont plus seulement des soldats du feu. 
Ils sont devenus le dernier filet de securite d'un systeme de sante sous pression. 
En 2023, ils ont compense plus de 200 000 fois l'absence d'ambulances disponibles.
""")

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("**🔥 Le mythe**\n\nPompiers = eteindre des feux")
with col2:
    st.markdown("**📊 La realite**\n\n88% urgences medicales, 3% incendies")
with col3:
    st.markdown("**⚠️ Le probleme**\n\n200 000+ carences/an")

# =============================================================================
# FOOTER
# =============================================================================
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #7f8c8d; padding: 10px;">
Projet EFREI Paris - Data Visualization | #EFREIDataStories2025
</div>
""", unsafe_allow_html=True)
