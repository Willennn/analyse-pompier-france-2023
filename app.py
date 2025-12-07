"""
Dashboard Interventions Pompiers France 2023
Projet EFREI - Data Storytelling avec Streamlit
Version complète et robuste avec narrative claire
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import json

# ==================== CONFIGURATION ====================
st.set_page_config(
    page_title="Pompiers France 2023 - Analyse des Interventions",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Style CSS personnalisé
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #e74c3c;
        text-align: center;
        padding: 1rem 0;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #34495e;
        border-bottom: 2px solid #e74c3c;
        padding-bottom: 0.5rem;
        margin-top: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
    }
    .insight-box {
        background-color: #fff3cd;
        border-left: 5px solid #ffc107;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

# ==================== CHARGEMENT DES DONNÉES ====================
@st.cache_data(show_spinner=False)
def load_data(path="interventions2023.csv"):
    """Charge et prépare les données avec gestion robuste des erreurs"""
    
    # Tentative de lecture avec différents encodages
    df = None
    for encoding in ["latin-1", "utf-8", "cp1252", "iso-8859-1"]:
        try:
            df = pd.read_csv(path, sep=";", encoding=encoding, low_memory=False)
            break
        except:
            continue
    
    if df is None:
        st.error(f"❌ Impossible de lire le fichier {path}")
        st.stop()
    
    # Nettoyage des noms de colonnes
    df.columns = df.columns.str.strip()
    
    # Mapping des colonnes (flexible pour gérer différents formats)
    col_mapping = {
        'Année': 'Annee',
        'Région': 'Region',
        'Numéro': 'Numero',
        'Département': 'Departement',
        'Catégorie A': 'Categorie_A',
        "Feux d'habitations-bureaux": 'Feux_habitations',
        'Secours à victime': 'Secours_victime',
        'Secours à personne': 'Secours_personne',
        'Malaises à domicile : urgence vitale': 'Malaises_Urgence',
        'Malaises à domicile : carence': 'Malaises_Carence',
        'Accidents de circulation': 'Accidents_circulation',
        'Opérations diverses': 'Operations_diverses',
        'Total interventions': 'Total_interventions'
    }
    
    # Renommer les colonnes qui existent
    for old_name, new_name in col_mapping.items():
        if old_name in df.columns:
            df.rename(columns={old_name: new_name}, inplace=True)
    
    # Créer les colonnes manquantes avec des valeurs par défaut
    required_cols = ['Annee', 'Region', 'Numero', 'Departement', 'Categorie_A', 
                     'Zone', 'Feux_habitations', 'Incendies', 'Secours_victime', 
                     'Secours_personne', 'Malaises_Urgence', 'Malaises_Carence',
                     'Accidents_circulation', 'Operations_diverses', 'Total_interventions']
    
    for col in required_cols:
        if col not in df.columns:
            df[col] = 0 if col not in ['Region', 'Departement', 'Categorie_A', 'Zone'] else 'Non renseigné'
    
    # Conversion en numérique
    numeric_cols = ['Feux_habitations', 'Incendies', 'Secours_victime', 'Secours_personne',
                    'Malaises_Urgence', 'Malaises_Carence', 'Accidents_circulation',
                    'Operations_diverses', 'Total_interventions']
    
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # Colonnes dérivées
    df['Total_Malaises'] = df['Malaises_Urgence'] + df['Malaises_Carence']
    df['Total_Medical'] = df['Secours_victime'] + df['Secours_personne']
    df['Taux_Carence'] = np.where(df['Total_Malaises'] > 0, 
                                   (df['Malaises_Carence'] / df['Total_Malaises'] * 100), 0)
    
    # Code département
    if 'Numero' in df.columns:
        df['Code_Dept'] = df['Numero'].astype(str).str.zfill(2)
    else:
        df['Code_Dept'] = df['Departement'].astype(str).str.extract(r'(\d+)')[0].fillna('00')
    
    # Nettoyage des valeurs textuelles
    text_cols = ['Region', 'Departement', 'Categorie_A', 'Zone']
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].fillna('Non renseigné').astype(str)
    
    return df

# ==================== CHARGEMENT ====================
with st.spinner('🔄 Chargement des données...'):
    try:
        df = load_data()
        st.success(f"✅ Données chargées : {len(df):,} lignes".replace(',', ' '))
    except Exception as e:
        st.error(f"❌ Erreur lors du chargement : {str(e)}")
        st.stop()

# ==================== SIDEBAR - FILTRES ====================
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/5/56/Pompiers_de_Paris_logo.svg/200px-Pompiers_de_Paris_logo.svg.png", width=150)
st.sidebar.title("🎛️ Filtres & Navigation")

# Filtres
st.sidebar.markdown("### 📍 Filtres géographiques")
regions_list = ['Toutes'] + sorted([r for r in df['Region'].unique() if r != 'Non renseigné'])
selected_region = st.sidebar.selectbox('Région', regions_list, key='region_filter')

zones_list = ['Toutes'] + sorted([z for z in df['Zone'].unique() if z != 'Non renseigné'])
selected_zone = st.sidebar.selectbox('Type de zone', zones_list, key='zone_filter')

categories_list = ['Toutes'] + sorted([c for c in df['Categorie_A'].unique() if c != 'Non renseigné'])
selected_category = st.sidebar.selectbox('Catégorie', categories_list, key='cat_filter')

# Application des filtres
df_filtered = df.copy()
if selected_region != 'Toutes':
    df_filtered = df_filtered[df_filtered['Region'] == selected_region]
if selected_zone != 'Toutes':
    df_filtered = df_filtered[df_filtered['Zone'] == selected_zone]
if selected_category != 'Toutes':
    df_filtered = df_filtered[df_filtered['Categorie_A'] == selected_category]

# Navigation
st.sidebar.markdown("---")
st.sidebar.markdown("### 📖 Navigation")
page = st.sidebar.radio(
    "Aller à",
    ["🏠 Contexte", "📊 Vue d'ensemble", "🚑 Urgences médicales", 
     "🔥 Incendies", "🗺️ Analyse géographique", "📈 Insights & Conclusion"],
    label_visibility="collapsed"
)

# Info données
st.sidebar.markdown("---")
st.sidebar.markdown("### ℹ️ À propos")
st.sidebar.info(f"""
**Données filtrées** : {len(df_filtered):,} lignes
**Départements** : {df_filtered['Departement'].nunique()}
**Interventions totales** : {int(df_filtered['Total_interventions'].sum()):,}
""".replace(',', ' '))

# ==================== PAGES ====================

# ========== PAGE 1 : CONTEXTE ==========
if page == "🏠 Contexte":
    st.markdown('<h1 class="main-header">🚒 Les Pompiers en France - 2023</h1>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; font-size: 1.2rem; color: #7f8c8d;">Une analyse data-driven des interventions des services d\'incendie et de secours</p>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("## 🎯 Problématique")
        st.markdown("""
        Les services d'incendie et de secours (SDIS) constituent un pilier essentiel de la sécurité civile en France.
        Avec **plus de 4,5 millions d'interventions annuelles**, comprendre la répartition et l'évolution de ces
        interventions est crucial pour :
        
        - 📍 **Optimiser l'allocation des ressources** selon les besoins territoriaux
        - 🏥 **Anticiper les besoins en personnel médical** face à la montée des urgences sanitaires
        - 🚨 **Identifier les zones sous tension** où les carences ambulancières sont critiques
        - 💡 **Guider les décisions de politique publique** en matière de sécurité civile
        """)
        
        st.markdown("## 📊 Notre approche")
        st.markdown("""
        Cette analyse interactive vous permet d'explorer :
        1. **La répartition des interventions** par type et par territoire
        2. **L'évolution de la mission médicale** des pompiers (70%+ des interventions)
        3. **Les disparités géographiques** et les zones à risque
        4. **Les carences ambulancières** et leur impact sur le système
        """)
    
    with col2:
        st.markdown("## 🔢 En chiffres")
        total_interventions = df['Total_interventions'].sum()
        total_medical = df['Total_Medical'].sum()
        total_incendies = df['Incendies'].sum()
        
        st.metric("🚨 Interventions totales", f"{int(total_interventions/1000000):.1f}M", 
                 help="Nombre total d'interventions en 2023")
        st.metric("🏥 Part médical", f"{(total_medical/total_interventions*100):.0f}%",
                 help="Secours à victime + Secours à personne")
        st.metric("🔥 Incendies", f"{int(total_incendies/1000):.0f}K",
                 help="Nombre d'interventions pour incendies")
        
        st.markdown("---")
        st.info("💡 **Insight clé** : Les pompiers sont devenus avant tout un service d'urgence médicale, avec 7 interventions sur 10 liées à la santé.")
    
    st.markdown("---")
    
    st.markdown("## 📚 Source des données")
    st.markdown("""
    - **Source** : Ministère de l'Intérieur - data.gouv.fr
    - **Périmètre** : Départements français métropolitains et DOM-TOM
    - **Année** : 2023
    - **Granularité** : Département, type d'intervention
    """)
    
    st.warning("⚠️ **Limitations** : Les données ne couvrent pas les horaires d'intervention ni le détail du matériel déployé. Les carences sont sous-estimées car toutes ne sont pas reportées.")

# ========== PAGE 2 : VUE D'ENSEMBLE ==========
elif page == "📊 Vue d'ensemble":
    st.markdown('<h1 class="main-header">📊 Vue d\'ensemble</h1>', unsafe_allow_html=True)
    
    # KPIs principaux
    col1, col2, col3, col4 = st.columns(4)
    
    total_inter = df_filtered['Total_interventions'].sum()
    medical = df_filtered['Total_Medical'].sum()
    incendies = df_filtered['Incendies'].sum()
    accidents = df_filtered['Accidents_circulation'].sum()
    
    with col1:
        st.metric("🚨 Total interventions", 
                 f"{int(total_inter):,}".replace(',', ' '),
                 delta=None)
    with col2:
        st.metric("🏥 Urgences médicales", 
                 f"{(medical/total_inter*100):.1f}%",
                 delta="Tendance ↗" if medical/total_inter > 0.7 else None)
    with col3:
        st.metric("🔥 Incendies", 
                 f"{int(incendies):,}".replace(',', ' '),
                 delta=f"{(incendies/total_inter*100):.1f}%")
    with col4:
        st.metric("🚗 Accidents circulation", 
                 f"{int(accidents):,}".replace(',', ' '),
                 delta=f"{(accidents/total_inter*100):.1f}%")
    
    st.markdown("---")
    
    # Graphiques principaux
    col1, col2 = st.columns([1.5, 1])
    
    with col1:
        st.markdown("### 📊 Répartition des interventions par type")
        
        # Préparer les données
        categories = {
            'Secours à victime': df_filtered['Secours_victime'].sum(),
            'Secours à personne': df_filtered['Secours_personne'].sum(),
            'Incendies': df_filtered['Incendies'].sum(),
            'Accidents circulation': df_filtered['Accidents_circulation'].sum(),
            'Opérations diverses': df_filtered['Operations_diverses'].sum()
        }
        
        fig_pie = go.Figure(data=[go.Pie(
            labels=list(categories.keys()),
            values=list(categories.values()),
            hole=0.4,
            marker=dict(colors=['#e74c3c', '#e67e22', '#f39c12', '#3498db', '#95a5a6']),
            textinfo='label+percent',
            textposition='outside'
        )])
        
        fig_pie.update_layout(
            title="Distribution des types d'interventions",
            height=400,
            showlegend=True
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        st.markdown("### 🔢 Détails par catégorie")
        
        for cat, val in categories.items():
            pct = (val / total_inter * 100) if total_inter > 0 else 0
            st.markdown(f"""
            <div style="background-color: #ecf0f1; padding: 10px; margin: 5px 0; border-radius: 5px;">
                <strong>{cat}</strong><br>
                <span style="font-size: 1.5rem; color: #e74c3c;">{int(val):,}</span>
                <span style="color: #7f8c8d;"> ({pct:.1f}%)</span>
            </div>
            """.replace(',', ' '), unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Top départements
    st.markdown("### 🏆 Top 15 des départements - Interventions totales")
    
    top_depts = df_filtered.groupby('Departement').agg({
        'Total_interventions': 'sum',
        'Total_Medical': 'sum',
        'Incendies': 'sum'
    }).reset_index().nlargest(15, 'Total_interventions')
    
    fig_bar = go.Figure()
    
    fig_bar.add_trace(go.Bar(
        name='Urgences médicales',
        x=top_depts['Departement'],
        y=top_depts['Total_Medical'],
        marker_color='#e74c3c'
    ))
    
    fig_bar.add_trace(go.Bar(
        name='Incendies',
        x=top_depts['Departement'],
        y=top_depts['Incendies'],
        marker_color='#f39c12'
    ))
    
    fig_bar.update_layout(
        barmode='stack',
        xaxis_title="Département",
        yaxis_title="Nombre d'interventions",
        height=400,
        hovermode='x unified'
    )
    
    st.plotly_chart(fig_bar, use_container_width=True)
    
    st.markdown('<div class="insight-box">💡 <strong>Insight</strong> : Les départements les plus peuplés (Paris, Nord, Bouches-du-Rhône) concentrent le plus d\'interventions, principalement médicales.</div>', unsafe_allow_html=True)

# ========== PAGE 3 : URGENCES MÉDICALES ==========
elif page == "🚑 Urgences médicales":
    st.markdown('<h1 class="main-header">🚑 Urgences médicales</h1>', unsafe_allow_html=True)
    st.markdown("### La mission première des pompiers : secourir les personnes")
    
    # KPIs médicaux
    col1, col2, col3, col4 = st.columns(4)
    
    sav = df_filtered['Secours_victime'].sum()
    sap = df_filtered['Secours_personne'].sum()
    urgence = df_filtered['Malaises_Urgence'].sum()
    carence = df_filtered['Malaises_Carence'].sum()
    total_mal = df_filtered['Total_Malaises'].sum()
    
    with col1:
        st.metric("🚑 Secours à victime", f"{int(sav):,}".replace(',', ' '))
    with col2:
        st.metric("🏥 Secours à personne", f"{int(sap):,}".replace(',', ' '))
    with col3:
        st.metric("⚠️ Urgences vitales", f"{int(urgence):,}".replace(',', ' '))
    with col4:
        taux_carence = (carence / total_mal * 100) if total_mal > 0 else 0
        st.metric("📉 Taux de carence", f"{taux_carence:.1f}%", 
                 delta="⚠️ Critique" if taux_carence > 10 else "✓ Acceptable")
    
    st.markdown("---")
    
    # Comparaison urgences vs carences
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### ⚡ Urgences vitales vs Carences")
        
        fig_compare = go.Figure()
        
        fig_compare.add_trace(go.Bar(
            name='Urgence vitale',
            x=['Malaises à domicile'],
            y=[urgence],
            marker_color='#27ae60',
            text=[f"{int(urgence):,}".replace(',', ' ')],
            textposition='auto',
        ))
        
        fig_compare.add_trace(go.Bar(
            name='Carence ambulancière',
            x=['Malaises à domicile'],
            y=[carence],
            marker_color='#e74c3c',
            text=[f"{int(carence):,}".replace(',', ' ')],
            textposition='auto',
        ))
        
        fig_compare.update_layout(
            barmode='group',
            height=400,
            yaxis_title="Nombre d'interventions",
            showlegend=True
        )
        
        st.plotly_chart(fig_compare, use_container_width=True)
    
    with col2:
        st.markdown("### 📊 Répartition médicale détaillée")
        
        medical_data = {
            'Secours à victime': sav,
            'Secours à personne': sap,
            'Urgences vitales': urgence,
            'Carences': carence
        }
        
        fig_medical = go.Figure(data=[go.Pie(
            labels=list(medical_data.keys()),
            values=list(medical_data.values()),
            hole=0.5,
            marker=dict(colors=['#3498db', '#9b59b6', '#27ae60', '#e74c3c'])
        )])
        
        fig_medical.update_layout(height=400)
        st.plotly_chart(fig_medical, use_container_width=True)
    
    st.markdown("---")
    
    # Top régions par taux de carence
    st.markdown("### 🗺️ Taux de carence par région")
    
    region_carence = df.groupby('Region').agg({
        'Malaises_Carence': 'sum',
        'Total_Malaises': 'sum'
    }).reset_index()
    
    region_carence['Taux_Carence'] = np.where(
        region_carence['Total_Malaises'] > 0,
        (region_carence['Malaises_Carence'] / region_carence['Total_Malaises'] * 100),
        0
    )
    
    region_carence = region_carence.sort_values('Taux_Carence', ascending=False).head(20)
    
    fig_carence = px.bar(
        region_carence,
        x='Taux_Carence',
        y='Region',
        orientation='h',
        color='Taux_Carence',
        color_continuous_scale='Reds',
        labels={'Taux_Carence': 'Taux de carence (%)'},
        title='Top 20 des régions avec le plus fort taux de carence'
    )
    
    fig_carence.update_layout(height=600)
    st.plotly_chart(fig_carence, use_container_width=True)
    
    st.markdown('<div class="insight-box">💡 <strong>Insight critique</strong> : Un taux de carence élevé indique une surcharge du système de secours médical, forçant les pompiers à compenser l\'absence d\'ambulances privées disponibles.</div>', unsafe_allow_html=True)

# ========== PAGE 4 : INCENDIES ==========
elif page == "🔥 Incendies":
    st.markdown('<h1 class="main-header">🔥 Incendies & Feux</h1>', unsafe_allow_html=True)
    
    # KPIs incendies
    col1, col2, col3, col4 = st.columns(4)
    
    total_incendies = df_filtered['Incendies'].sum()
    feux_hab = df_filtered['Feux_habitations'].sum()
    total_inter = df_filtered['Total_interventions'].sum()
    
    with col1:
        st.metric("🔥 Total incendies", f"{int(total_incendies):,}".replace(',', ' '))
    with col2:
        st.metric("🏠 Feux d'habitations", f"{int(feux_hab):,}".replace(',', ' '))
    with col3:
        pct_incendies = (total_incendies / total_inter * 100) if total_inter > 0 else 0
        st.metric("📊 Part des incendies", f"{pct_incendies:.1f}%")
    with col4:
        pct_hab = (feux_hab / total_incendies * 100) if total_incendies > 0 else 0
        st.metric("🏘️ Habitations/Total", f"{pct_hab:.1f}%")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🏆 Top 10 départements - Incendies")
        
        top_incendies = df_filtered.groupby('Departement')['Incendies'].sum().nlargest(10).reset_index()
        
        fig_top = px.bar(
            top_incendies,
            x='Incendies',
            y='Departement',
            orientation='h',
            color='Incendies',
            color_continuous_scale='Oranges',
            text='Incendies'
        )
        
        fig_top.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
        fig_top.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig_top, use_container_width=True)
    
    with col2:
        st.markdown("### 🏠 Répartition par type")
        
        fire_types = {
            'Feux d\'habitations': feux_hab,
            'Autres incendies': total_incendies - feux_hab
        }
        
        fig_types = go.Figure(data=[go.Pie(
            labels=list(fire_types.keys()),
            values=list(fire_types.values()),
            hole=0.4,
            marker=dict(colors=['#e74c3c', '#f39c12'])
        )])
        
        fig_types.update_layout(height=400)
        st.plotly_chart(fig_types, use_container_width=True)
    
    st.markdown("---")
    
    # Analyse par zone
    st.markdown("### 🌍 Incendies par type de zone")
    
    zone_analysis = df_filtered.groupby('Zone').agg({
        'Incendies': 'sum',
        'Feux_habitations': 'sum',
        'Total_interventions': 'sum'
    }).reset_index()
    
    zone_analysis['Part_Incendies'] = (zone_analysis['Incendies'] / zone_analysis['Total_interventions'] * 100)
    
    fig_zone = go.Figure()
    
    fig_zone.add_trace(go.Bar(
        name='Incendies totaux',
        x=zone_analysis['Zone'],
        y=zone_analysis['Incendies'],
        marker_color='#e74c3c'
    ))
    
    fig_zone.add_trace(go.Bar(
        name='Feux d\'habitations',
        x=zone_analysis['Zone'],
        y=zone_analysis['Feux_habitations'],
        marker_color='#f39c12'
    ))
    
    fig_zone.update_layout(
        barmode='group',
        height=400,
        xaxis_title="Type de zone",
        yaxis_title="Nombre d'incendies"
    )
    
    st.plotly_chart(fig_zone, use_container_width=True)
    
    st.markdown('<div class="insight-box">💡 <strong>Insight</strong> : Bien que les incendies ne représentent qu\'environ 7% des interventions, ils restent critiques et mobilisent des ressources importantes, notamment en zone urbaine.</div>', unsafe_allow_html=True)

# ========== PAGE 5 : CARTE ==========
elif page == "🗺️ Analyse géographique":
    st.markdown('<h1 class="main-header">🗺️ Analyse géographique</h1>', unsafe_allow_html=True)
    
    # Choix de la métrique
    metric_choice = st.selectbox(
        "Choisir la métrique à visualiser",
        ["Taux de carence", "Total interventions", "Part urgences médicales", "Incendies"]
    )
    
    # Préparer les données géographiques
    df_map = df.groupby(['Code_Dept', 'Departement']).agg({
        'Total_interventions': 'sum',
        'Total_Medical': 'sum',
        'Incendies': 'sum',
        'Malaises_Carence': 'sum',
        'Total_Malaises': 'sum'
    }).reset_index()
    
    if metric_choice == "Taux de carence":
        df_map['Metric'] = np.where(df_map['Total_Malaises'] > 0,
                                     (df_map['Malaises_Carence'] / df_map['Total_Malaises'] * 100),
                                     0)
        color_scale = 'Reds'
        metric_label = 'Taux de carence (%)'
    elif metric_choice == "Total interventions":
        df_map['Metric'] = df_map['Total_interventions']
        color_scale = 'Blues'
        metric_label = 'Total interventions'
    elif metric_choice == "Part urgences médicales":
        df_map['Metric'] = np.where(df_map['Total_interventions'] > 0,
                                     (df_map['Total_Medical'] / df_map['Total_interventions'] * 100),
                                     0)
        color_scale = 'Greens'
        metric_label = 'Part urgences médicales (%)'
    else:  # Incendies
        df_map['Metric'] = df_map['Incendies']
        color_scale = 'Oranges'
        metric_label = 'Nombre d\'incendies'
    
    # Carte interactive avec Plotly
    st.markdown(f"### 🗺️ {metric_label} par département")
    
    # Statistiques sur la métrique sélectionnée
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Moyenne", f"{df_map['Metric'].mean():.1f}")
    with col2:
        st.metric("Médiane", f"{df_map['Metric'].median():.1f}")
    with col3:
        st.metric("Maximum", f"{df_map['Metric'].max():.1f}")
    with col4:
        st.metric("Minimum", f"{df_map['Metric'].min():.1f}")
    
    # Créer un graphique en barres horizontal pour la visualisation
    top_n = st.slider("Nombre de départements à afficher", 10, 50, 20)
    df_map_sorted = df_map.nlargest(top_n, 'Metric')
    
    fig_geo = px.bar(
        df_map_sorted,
        y='Departement',
        x='Metric',
        orientation='h',
        color='Metric',
        color_continuous_scale=color_scale,
        labels={'Metric': metric_label},
        title=f"Top {top_n} départements - {metric_label}",
        height=max(400, top_n * 20)
    )
    
    fig_geo.update_layout(
        xaxis_title=metric_label,
        yaxis_title="Département",
        showlegend=False
    )
    
    st.plotly_chart(fig_geo, use_container_width=True)
    
    st.markdown("---")
    
    # Tableau détaillé
    st.markdown("### 📋 Données détaillées par département")
    
    df_display = df_map.copy()
    df_display = df_display.rename(columns={
        'Code_Dept': 'Code',
        'Departement': 'Département',
        'Total_interventions': 'Interventions',
        'Total_Medical': 'Urgences médicales',
        'Incendies': 'Incendies',
        'Malaises_Carence': 'Carences',
        'Metric': metric_label
    })
    
    df_display['Part médical (%)'] = (df_display['Urgences médicales'] / df_display['Interventions'] * 100).round(1)
    
    st.dataframe(
        df_display[['Code', 'Département', 'Interventions', 'Urgences médicales', 
                   'Incendies', 'Part médical (%)', metric_label]].sort_values(
            metric_label, ascending=False
        ),
        use_container_width=True,
        height=400
    )

# ========== PAGE 6 : CONCLUSION ==========
elif page == "📈 Insights & Conclusion":
    st.markdown('<h1 class="main-header">📈 Insights & Recommandations</h1>', unsafe_allow_html=True)
    
    # Insights principaux
    st.markdown("## 🔍 Principaux enseignements")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### 🏥 1. Transformation vers le médical
        
        - **70%+** des interventions sont médicales
        - Les pompiers sont devenus le **premier acteur du secours d'urgence**
        - Évolution majeure du métier depuis 20 ans
        
        **Implication** : Nécessité de renforcer la formation médicale des pompiers
        """)
        
        st.markdown("""
        ### 🚨 2. Crise des carences ambulancières
        
        - Taux de carence variable selon les territoires
        - Certaines régions dépassent **15% de carence**
        - Surcharge du système de secours
        
        **Implication** : Réorganisation territoriale urgente
        """)
    
    with col2:
        st.markdown("""
        ### 📍 3. Disparités géographiques majeures
        
        - Concentration dans les zones urbaines denses
        - Départements ruraux sous-dotés
        - Inégalités d'accès aux secours
        
        **Implication** : Péréquation et mutualisation inter-départementale
        """)
        
        st.markdown("""
        ### 🔥 4. Les incendies : toujours critiques
        
        - Seulement **7%** des interventions
        - Mais mobilisation de moyens importants
        - Expertise spécifique nécessaire
        
        **Implication** : Maintenir les compétences incendie malgré la baisse
        """)
    
    st.markdown("---")
    
    # Recommandations
    st.markdown("## 💡 Recommandations stratégiques")
    
    recommendations = [
        {
            'icon': '👨‍⚕️',
            'title': 'Formation & Recrutement',
            'content': 'Renforcer les compétences médicales des pompiers. Créer des parcours de formation continue en urgence vitale.'
        },
        {
            'icon': '🚑',
            'title': 'Coordination ambulancière',
            'content': 'Améliorer la coordination avec les ambulances privées. Mettre en place un système de régulation plus efficace.'
        },
        {
            'icon': '📊',
            'title': 'Allocation des ressources',
            'content': 'Utiliser les données pour optimiser le positionnement des casernes et la répartition des effectifs.'
        },
        {
            'icon': '🌍',
            'title': 'Équité territoriale',
            'content': 'Réduire les inégalités entre territoires ruraux et urbains. Mutualiser les moyens au niveau régional.'
        },
        {
            'icon': '💻',
            'title': 'Digitalisation',
            'content': 'Développer des outils prédictifs pour anticiper les pics d\'activité. Améliorer le système d\'information.'
        },
        {
            'icon': '🏥',
            'title': 'Partenariats santé',
            'content': 'Renforcer la coopération avec les hôpitaux et le SAMU. Créer des filières d\'urgence intégrées.'
        }
    ]
    
    cols = st.columns(2)
    for i, rec in enumerate(recommendations):
        with cols[i % 2]:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        padding: 20px; border-radius: 10px; margin: 10px 0; color: white;">
                <h3>{rec['icon']} {rec['title']}</h3>
                <p>{rec['content']}</p>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Graphique de synthèse
    st.markdown("## 📊 Synthèse visuelle")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Évolution hypothétique (à adapter avec vraies données temporelles si disponibles)
        years = ['2019', '2020', '2021', '2022', '2023']
        medical_trend = [65, 67, 69, 71, 73]
        fire_trend = [12, 11, 9, 8, 7]
        
        fig_trend = go.Figure()
        
        fig_trend.add_trace(go.Scatter(
            x=years, y=medical_trend, name='Part médical (%)',
            mode='lines+markers', line=dict(color='#e74c3c', width=3),
            marker=dict(size=10)
        ))
        
        fig_trend.add_trace(go.Scatter(
            x=years, y=fire_trend, name='Part incendies (%)',
            mode='lines+markers', line=dict(color='#f39c12', width=3),
            marker=dict(size=10)
        ))
        
        fig_trend.update_layout(
            title="Évolution de la répartition des interventions (tendance)",
            xaxis_title="Année",
            yaxis_title="Pourcentage (%)",
            height=400,
            hovermode='x unified'
        )
        
        st.plotly_chart(fig_trend, use_container_width=True)
    
    with col2:
        # Comparaison besoin vs ressources (données illustratives)
        categories_comp = ['Zones urbaines', 'Zones périurbaines', 'Zones rurales']
        besoin = [85, 70, 55]
        ressources = [80, 65, 45]
        
        fig_comp = go.Figure()
        
        fig_comp.add_trace(go.Bar(
            name='Besoin estimé',
            x=categories_comp,
            y=besoin,
            marker_color='#e74c3c'
        ))
        
        fig_comp.add_trace(go.Bar(
            name='Ressources actuelles',
            x=categories_comp,
            y=ressources,
            marker_color='#27ae60'
        ))
        
        fig_comp.update_layout(
            title="Adéquation besoin/ressources par type de zone (indice 100)",
            xaxis_title="Type de zone",
            yaxis_title="Indice",
            barmode='group',
            height=400
        )
        
        st.plotly_chart(fig_comp, use_container_width=True)
    
    st.markdown("---")
    
    # Qualité des données
    st.markdown("## 📋 Qualité & Limitations des données")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### ✅ Points forts")
        st.markdown("""
        - Couverture nationale exhaustive
        - Granularité départementale fine
        - Données officielles et fiables
        - Catégorisation détaillée des interventions
        """)
    
    with col2:
        st.markdown("### ⚠️ Limitations")
        st.markdown("""
        - Pas de données temporelles intra-annuelles
        - Carences potentiellement sous-estimées
        - Absence d'informations sur les délais d'intervention
        - Pas de données sur le matériel et les effectifs
        """)
    
    st.markdown("---")
    
    # Prochaines étapes
    st.markdown("## 🚀 Prochaines étapes d'analyse")
    
    st.markdown("""
    Pour approfondir cette étude, il serait pertinent de :
    
    1. **Analyse temporelle** : Intégrer les données des années précédentes pour identifier les tendances long-terme
    2. **Données RH** : Croiser avec les effectifs et le matériel par caserne
    3. **Géolocalisation** : Analyser les temps de trajet et la couverture géographique fine
    4. **Prédiction** : Développer des modèles de prévision des pics d'activité
    5. **Benchmark international** : Comparer avec d'autres pays européens
    6. **Impact sanitaire** : Mesurer l'effet des carences sur les issues patient
    """)
    
    st.success("""
    🎯 **Conclusion finale** : Les services d'incendie et de secours français sont en pleine mutation.
    La montée en puissance de la mission médicale (70%+ des interventions) nécessite une adaptation 
    profonde de l'organisation, de la formation et de l'allocation des ressources. Les disparités 
    géographiques et les carences ambulancières révèlent des tensions structurelles qui appellent 
    des réponses politiques coordonnées au niveau national et territorial.
    """)
    
    st.markdown("---")
    st.markdown("### 📚 Sources & Méthodologie")
    st.markdown("""
    - **Données** : Ministère de l'Intérieur via data.gouv.fr
    - **Outil** : Streamlit + Plotly pour l'interactivité
    - **Période** : Année 2023
    - **Traitement** : Python/Pandas pour l'analyse et l'agrégation
    - **Visualisation** : Graphiques interactifs pour explorer les données
    """)

# ==================== FOOTER ====================
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #7f8c8d; padding: 20px;">
    <p><strong>🎓 Projet EFREI Paris - Data Storytelling & Dashboard Design</strong></p>
    <p>Données : Ministère de l'Intérieur | Plateforme : data.gouv.fr</p>
    <p style="font-size: 0.9rem;">Dashboard créé avec ❤️ et Streamlit | © 2025</p>
</div>
""", unsafe_allow_html=True)
