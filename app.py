import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ==================== CONFIGURATION ====================
st.set_page_config(
    page_title="Pompiers France 2023",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Style CSS amélioré - TEXTE VISIBLE
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #e74c3c;
        text-align: center;
        padding: 1rem 0;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #2c3e50;
        border-bottom: 2px solid #e74c3c;
        padding-bottom: 0.5rem;
        margin-top: 2rem;
    }
    .insight-box {
        background-color: #fff3cd;
        border-left: 5px solid #ffc107;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 5px;
        color: #000000 !important;
    }
    .insight-box p, .insight-box strong {
        color: #000000 !important;
    }
    /* Fix pour le texte sur fond blanc */
    .stMarkdown, .stMarkdown p, .stMarkdown div {
        color: #2c3e50 !important;
    }
    /* Metrics custom */
    [data-testid="stMetricValue"] {
        font-size: 2rem !important;
        color: #2c3e50 !important;
    }
    /* Sidebar */
    .css-1d391kg, .css-1cypcdb {
        background-color: #2c3e50;
    }
    /* Navigation buttons */
    .nav-button {
        background-color: #e74c3c;
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 5px;
        text-align: center;
        margin: 0.2rem;
        cursor: pointer;
    }
</style>
""", unsafe_allow_html=True)

# ==================== CHARGEMENT ROBUSTE ====================
@st.cache_data(show_spinner=False)
def load_data(path="interventions2023.csv"):
    """Charge et nettoie les données de manière ultra-robuste"""
    
    df = None
    # Essayer différents encodages ET séparateurs
    for encoding in ["latin-1", "utf-8", "cp1252", "iso-8859-1"]:
        for sep in [";", ",", "\t"]:
            try:
                df = pd.read_csv(path, sep=sep, encoding=encoding, low_memory=False)
                if len(df.columns) > 5:  # Vérifier que le séparateur est bon
                    break
            except:
                continue
        if df is not None and len(df.columns) > 5:
            break
    
    if df is None or len(df.columns) <= 5:
        st.error(f"❌ Impossible de lire le fichier {path}")
        st.info("Vérifiez que le fichier existe et que le séparateur est correct (;)")
        st.stop()
    
    # Nettoyer les noms de colonnes
    df.columns = df.columns.str.strip().str.replace('\xa0', ' ')
    
    # Afficher les colonnes disponibles pour debug
    st.sidebar.info(f"✅ {len(df)} lignes chargées | {len(df.columns)} colonnes")
    
    # Mapping flexible des colonnes (gère accents et variations)
    def find_column(df, possible_names):
        """Trouve une colonne parmi plusieurs noms possibles"""
        cols_lower = {col.lower().replace('é', 'e').replace('è', 'e').replace('à', 'a'): col 
                      for col in df.columns}
        
        for name in possible_names:
            name_normalized = name.lower().replace('é', 'e').replace('è', 'e').replace('à', 'a')
            if name_normalized in cols_lower:
                return cols_lower[name_normalized]
            # Recherche partielle
            for col_norm, col_orig in cols_lower.items():
                if name_normalized in col_norm or col_norm in name_normalized:
                    return col_orig
        return None
    
    # Mapper toutes les colonnes nécessaires
    col_map = {
        'Annee': find_column(df, ['Année', 'Annee', 'annee', 'ANNEE']),
        'Region': find_column(df, ['Région', 'Region', 'region', 'REGION']),
        'Numero': find_column(df, ['Numéro', 'Numero', 'numero', 'NUM', 'Code']),
        'Departement': find_column(df, ['Département', 'Departement', 'departement', 'DEPARTEMENT']),
        'Zone': find_column(df, ['Zone', 'zone', 'ZONE', 'Type de zone']),
        'Categorie_A': find_column(df, ['Catégorie A', 'Categorie A', 'Catégorie', 'Categorie', 'CAT']),
        'Feux_habitations': find_column(df, ["Feux d'habitations-bureaux", "Feux d'habitations", 'Feux habitations', 'FEUX HAB']),
        'Incendies': find_column(df, ['Incendies', 'incendies', 'INCENDIES']),
        'Secours_victime': find_column(df, ['Secours à victime', 'Secours a victime', 'SAV', 'SECOURS VICTIME']),
        'Secours_personne': find_column(df, ['Secours à personne', 'Secours a personne', 'SAP', 'SECOURS PERSONNE']),
        'Malaises_Urgence': find_column(df, ['Malaises à domicile : urgence vitale', 'Malaises urgence', 'Urgence vitale', 'MALAISES URG']),
        'Malaises_Carence': find_column(df, ['Malaises à domicile : carence', 'Malaises carence', 'Carence', 'MALAISES CAR']),
        'Accidents_circulation': find_column(df, ['Accidents de circulation', 'Accidents circulation', 'ACC CIRCULATION']),
        'Operations_diverses': find_column(df, ['Opérations diverses', 'Operations diverses', 'OP DIVERSES']),
        'Total_interventions': find_column(df, ['Total interventions', 'Total', 'TOTAL INTERVENTIONS'])
    }
    
    # Renommer les colonnes trouvées
    rename_dict = {}
    for new_name, old_name in col_map.items():
        if old_name is not None:
            rename_dict[old_name] = new_name
    
    df = df.rename(columns=rename_dict)
    
    # Créer les colonnes manquantes avec valeurs par défaut
    for col in col_map.keys():
        if col not in df.columns:
            if col in ['Region', 'Departement', 'Categorie_A', 'Zone']:
                df[col] = 'Non renseigné'
            else:
                df[col] = 0
    
    # CONVERSION NUMÉRIQUE ROBUSTE
    numeric_cols = ['Feux_habitations', 'Incendies', 'Secours_victime', 'Secours_personne',
                    'Malaises_Urgence', 'Malaises_Carence', 'Accidents_circulation',
                    'Operations_diverses', 'Total_interventions']
    
    for col in numeric_cols:
        if col in df.columns:
            # Remplacer virgules par points, supprimer espaces
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).str.replace(',', '.').str.replace(' ', '').str.replace('\xa0', '')
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(float)
    
    # Colonnes dérivées
    df['Total_Malaises'] = df['Malaises_Urgence'] + df['Malaises_Carence']
    df['Total_Medical'] = df['Secours_victime'] + df['Secours_personne']
    
    # Taux de carence (éviter division par zéro)
    df['Taux_Carence'] = 0.0
    mask = df['Total_Malaises'] > 0
    df.loc[mask, 'Taux_Carence'] = (df.loc[mask, 'Malaises_Carence'] / df.loc[mask, 'Total_Malaises'] * 100)
    
    # Code département
    if 'Numero' in df.columns:
        df['Code_Dept'] = df['Numero'].astype(str).str.zfill(2)
    else:
        df['Code_Dept'] = '00'
    
    # Nettoyer valeurs textuelles
    text_cols = ['Region', 'Departement', 'Categorie_A', 'Zone']
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].fillna('Non renseigné').astype(str).str.strip()
            df[col] = df[col].replace(['', 'nan', 'None'], 'Non renseigné')
    
    return df

# ==================== CHARGEMENT ====================
with st.spinner('🔄 Chargement des données...'):
    try:
        df = load_data()
    except Exception as e:
        st.error(f"❌ Erreur : {str(e)}")
        st.stop()

# ==================== NAVIGATION D'ABORD ====================
st.sidebar.title("📖 Navigation")

# Initialiser la page
if "page" not in st.session_state:
    st.session_state.page = "🏠 Contexte"

# Radio pour navigation
page = st.sidebar.radio(
    "Choisir une page",
    ["🏠 Contexte", "📊 Vue d'ensemble", "🚑 Urgences médicales", 
     "🔥 Incendies", "🗺️ Analyse géographique", "📈 Insights & Conclusion"],
    key='page_selector'
)

st.sidebar.markdown("---")

# ==================== PUIS FILTRES ====================
st.sidebar.title("🎛️ Filtres géographiques")

# Filtres
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

# Info données
st.sidebar.markdown("---")
st.sidebar.markdown("### ℹ️ Données")
total_rows = len(df_filtered)
total_inter_sidebar = df_filtered['Total_interventions'].sum()
st.sidebar.metric("Lignes", f"{total_rows:,}".replace(',', ' '))
st.sidebar.metric("Interventions", f"{int(total_inter_sidebar):,}".replace(',', ' '))

# ==================== PAGES ====================

# ========== PAGE 1 : CONTEXTE ==========
if page == "🏠 Contexte":
    st.markdown('<h1 class="main-header">🚒 Les Pompiers en France - 2023</h1>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; font-size: 1.2rem; color: #2c3e50;">Une analyse data-driven des interventions des services d\'incendie et de secours</p>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("## 🎯 Problématique")
        st.markdown("""
        <div style="color: #2c3e50;">
        Les services d'incendie et de secours (SDIS) constituent un pilier essentiel de la sécurité civile en France.
        Avec <strong>plus de 4,5 millions d'interventions annuelles</strong>, comprendre la répartition et l'évolution de ces
        interventions est crucial pour :
        
        <ul>
        <li>📍 <strong>Optimiser l'allocation des ressources</strong> selon les besoins territoriaux</li>
        <li>🏥 <strong>Anticiper les besoins en personnel médical</strong> face à la montée des urgences sanitaires</li>
        <li>🚨 <strong>Identifier les zones sous tension</strong> où les carences ambulancières sont critiques</li>
        <li>💡 <strong>Guider les décisions de politique publique</strong> en matière de sécurité civile</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("## 📊 Notre approche")
        st.markdown("""
        <div style="color: #2c3e50;">
        Cette analyse interactive vous permet d'explorer :<br>
        1. <strong>La répartition des interventions</strong> par type et par territoire<br>
        2. <strong>L'évolution de la mission médicale</strong> des pompiers (70%+ des interventions)<br>
        3. <strong>Les disparités géographiques</strong> et les zones à risque<br>
        4. <strong>Les carences ambulancières</strong> et leur impact sur le système
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("## 🔢 En chiffres")
        total_interventions = df['Total_interventions'].sum()
        total_medical = df['Total_Medical'].sum()
        total_incendies = df['Incendies'].sum()
        
        if total_interventions > 0:
            st.metric("🚨 Interventions totales", 
                     f"{total_interventions/1_000_000:.2f}M",
                     help="Nombre total d'interventions en 2023")
            st.metric("🏥 Part médical", 
                     f"{(total_medical/total_interventions*100):.1f}%",
                     help="Secours à victime + Secours à personne")
            st.metric("🔥 Incendies", 
                     f"{int(total_incendies/1000):.0f}K",
                     help="Nombre d'interventions pour incendies")
        
        st.markdown("---")
        st.info("💡 **Insight clé** : Les pompiers sont devenus avant tout un service d'urgence médicale, avec 7 interventions sur 10 liées à la santé.")
    
    st.markdown("---")
    
    st.markdown("## 📚 Source des données")
    st.markdown("""
    <div style="color: #2c3e50;">
    <ul>
    <li><strong>Source</strong> : Ministère de l'Intérieur - data.gouv.fr</li>
    <li><strong>Périmètre</strong> : Départements français métropolitains et DOM-TOM</li>
    <li><strong>Année</strong> : 2023</li>
    <li><strong>Granularité</strong> : Département, type d'intervention</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)
    
    st.warning("⚠️ **Limitations** : Les données ne couvrent pas les horaires d'intervention ni le détail du matériel déployé.")

# ========== PAGE 2 : VUE D'ENSEMBLE ==========
elif page == "📊 Vue d'ensemble":
    st.markdown('<h1 class="main-header">📊 Vue d\'ensemble</h1>', unsafe_allow_html=True)
    
    # KPIs principaux - CALCULS CORRIGÉS
    col1, col2, col3, col4 = st.columns(4)
    
    total_inter = float(df_filtered['Total_interventions'].sum())
    medical = float(df_filtered['Total_Medical'].sum())
    incendies = float(df_filtered['Incendies'].sum())
    accidents = float(df_filtered['Accidents_circulation'].sum())
    
    with col1:
        st.metric("🚨 Total interventions", 
                 f"{int(total_inter):,}".replace(',', ' '))
    with col2:
        pct_medical = (medical/total_inter*100) if total_inter > 0 else 0
        st.metric("🏥 Urgences médicales", f"{pct_medical:.1f}%")
    with col3:
        st.metric("🔥 Incendies", f"{int(incendies):,}".replace(',', ' '))
    with col4:
        st.metric("🚗 Accidents", f"{int(accidents):,}".replace(',', ' '))
    
    st.markdown("---")
    
    # Graphiques principaux
    col1, col2 = st.columns([1.5, 1])
    
    with col1:
        st.markdown("### 📊 Répartition des interventions par type")
        
        # Données pour le pie chart
        sav = float(df_filtered['Secours_victime'].sum())
        sap = float(df_filtered['Secours_personne'].sum())
        inc = float(df_filtered['Incendies'].sum())
        acc = float(df_filtered['Accidents_circulation'].sum())
        ops = float(df_filtered['Operations_diverses'].sum())
        
        categories_data = {
            'Secours à victime': sav,
            'Secours à personne': sap,
            'Incendies': inc,
            'Accidents circulation': acc,
            'Opérations diverses': ops
        }
        
        # Filtrer les valeurs nulles
        categories_data = {k: v for k, v in categories_data.items() if v > 0}
        
        if categories_data:
            fig_pie = go.Figure(data=[go.Pie(
                labels=list(categories_data.keys()),
                values=list(categories_data.values()),
                hole=0.4,
                marker=dict(colors=['#e74c3c', '#e67e22', '#f39c12', '#3498db', '#95a5a6']),
                textinfo='label+percent',
                textposition='outside',
                textfont=dict(size=12, color='#2c3e50')
            )])
            
            fig_pie.update_layout(
                title="Distribution des types d'interventions",
                height=400,
                showlegend=True,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.warning("Aucune donnée à afficher pour cette sélection")
    
    with col2:
        st.markdown("### 🔢 Détails par catégorie")
        
        for cat, val in categories_data.items():
            pct = (val / total_inter * 100) if total_inter > 0 else 0
            st.markdown(f"""
            <div style="background-color: #ecf0f1; padding: 10px; margin: 5px 0; border-radius: 5px; color: #2c3e50;">
                <strong style="color: #2c3e50;">{cat}</strong><br>
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
    }).reset_index()
    
    top_depts = top_depts[top_depts['Total_interventions'] > 0].nlargest(15, 'Total_interventions')
    
    if len(top_depts) > 0:
        fig_bar = go.Figure()
        
        fig_bar.add_trace(go.Bar(
            name='Urgences médicales',
            x=top_depts['Departement'],
            y=top_depts['Total_Medical'],
            marker_color='#e74c3c',
            text=top_depts['Total_Medical'].apply(lambda x: f"{int(x):,}".replace(',', ' ')),
            textposition='auto'
        ))
        
        fig_bar.add_trace(go.Bar(
            name='Incendies',
            x=top_depts['Departement'],
            y=top_depts['Incendies'],
            marker_color='#f39c12',
            text=top_depts['Incendies'].apply(lambda x: f"{int(x):,}".replace(',', ' ')),
            textposition='auto'
        ))
        
        fig_bar.update_layout(
            barmode='stack',
            xaxis_title="Département",
            yaxis_title="Nombre d'interventions",
            height=400,
            hovermode='x unified',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#2c3e50')
        )
        
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.warning("Aucune donnée à afficher pour cette sélection")
    
    st.markdown('<div class="insight-box"><strong>💡 Insight</strong> : Les départements les plus peuplés concentrent le plus d\'interventions, principalement médicales.</div>', unsafe_allow_html=True)

# ========== PAGE 3 : URGENCES MÉDICALES ==========
elif page == "🚑 Urgences médicales":
    st.markdown('<h1 class="main-header">🚑 Urgences médicales</h1>', unsafe_allow_html=True)
    st.markdown('<p style="color: #2c3e50; text-align: center; font-size: 1.1rem;">La mission première des pompiers : secourir les personnes</p>', unsafe_allow_html=True)
    
    # KPIs médicaux
    col1, col2, col3, col4 = st.columns(4)
    
    sav = float(df_filtered['Secours_victime'].sum())
    sap = float(df_filtered['Secours_personne'].sum())
    urgence = float(df_filtered['Malaises_Urgence'].sum())
    carence = float(df_filtered['Malaises_Carence'].sum())
    total_mal = float(df_filtered['Total_Malaises'].sum())
    
    with col1:
        st.metric("🚑 Secours à victime", f"{int(sav):,}".replace(',', ' '))
    with col2:
        st.metric("🏥 Secours à personne", f"{int(sap):,}".replace(',', ' '))
    with col3:
        st.metric("⚠️ Urgences vitales", f"{int(urgence):,}".replace(',', ' '))
    with col4:
        taux_carence = (carence / total_mal * 100) if total_mal > 0 else 0
        st.metric("📉 Taux de carence", f"{taux_carence:.1f}%")
    
    st.markdown("---")
    
    # Comparaison urgences vs carences
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### ⚡ Urgences vitales vs Carences")
        
        if urgence > 0 or carence > 0:
            fig_compare = go.Figure()
            
            fig_compare.add_trace(go.Bar(
                name='Urgence vitale',
                x=['Malaises à domicile'],
                y=[urgence],
                marker_color='#27ae60',
                text=[f"{int(urgence):,}".replace(',', ' ')],
                textposition='auto'
            ))
            
            fig_compare.add_trace(go.Bar(
                name='Carence ambulancière',
                x=['Malaises à domicile'],
                y=[carence],
                marker_color='#e74c3c',
                text=[f"{int(carence):,}".replace(',', ' ')],
                textposition='auto'
            ))
            
            fig_compare.update_layout(
                barmode='group',
                height=400,
                yaxis_title="Nombre d'interventions",
                showlegend=True,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#2c3e50')
            )
            
            st.plotly_chart(fig_compare, use_container_width=True)
        else:
            st.warning("Aucune donnée disponible")
    
    with col2:
        st.markdown("### 📊 Répartition médicale détaillée")
        
        medical_data = {
            'Secours à victime': sav,
            'Secours à personne': sap,
            'Urgences vitales': urgence,
            'Carences': carence
        }
        
        # Filtrer valeurs nulles
        medical_data = {k: v for k, v in medical_data.items() if v > 0}
        
        if medical_data:
            fig_medical = go.Figure(data=[go.Pie(
                labels=list(medical_data.keys()),
                values=list(medical_data.values()),
                hole=0.5,
                marker=dict(colors=['#3498db', '#9b59b6', '#27ae60', '#e74c3c']),
                textfont=dict(color='#2c3e50')
            )])
            
            fig_medical.update_layout(
                height=400,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig_medical, use_container_width=True)
        else:
            st.warning("Aucune donnée disponible")
    
    st.markdown("---")
    
    # Top régions par taux de carence
    st.markdown("### 🗺️ Taux de carence par région")
    
    region_carence = df.groupby('Region').agg({
        'Malaises_Carence': 'sum',
        'Total_Malaises': 'sum'
    }).reset_index()
    
    region_carence = region_carence[region_carence['Total_Malaises'] > 0]
    region_carence['Taux'] = (region_carence['Malaises_Carence'] / region_carence['Total_Malaises'] * 100)
    region_carence = region_carence.sort_values('Taux', ascending=False).head(20)
    
    if len(region_carence) > 0:
        fig_carence = px.bar(
            region_carence,
            x='Taux',
            y='Region',
            orientation='h',
            color='Taux',
            color_continuous_scale='Reds',
            labels={'Taux': 'Taux de carence (%)'},
            title='Top 20 des régions avec le plus fort taux de carence'
        )
        
        fig_carence.update_layout(
            height=600,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#2c3e50')
        )
        st.plotly_chart(fig_carence, use_container_width=True)
    else:
        st.warning("Aucune donnée disponible")
    
    st.markdown('<div class="insight-box"><strong>💡 Insight critique</strong> : Un taux de carence élevé indique une surcharge du système de secours médical.</div>', unsafe_allow_html=True)

# ========== PAGE 4 : INCENDIES ==========
elif page == "🔥 Incendies":
    st.markdown('<h1 class="main-header">🔥 Incendies &
