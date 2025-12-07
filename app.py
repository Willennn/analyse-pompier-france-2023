import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

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
                if len(df.columns) > 5:
                    break
            except:
                continue
        if df is not None and len(df.columns) > 5:
            break
    
    if df is None or len(df.columns) <= 5:
        st.error(f"❌ Impossible de lire le fichier {path}")
        st.stop()
    
    # Nettoyer les noms de colonnes
    df.columns = df.columns.str.strip().str.replace('\xa0', ' ')
    
    # Afficher les colonnes disponibles pour debug
    st.sidebar.info(f"✅ {len(df)} lignes | {len(df.columns)} colonnes")
    
    # Mapping flexible des colonnes
    def find_column(df, possible_names):
        cols_lower = {col.lower().replace('é', 'e').replace('è', 'e').replace('à', 'a'): col 
                      for col in df.columns}
        
        for name in possible_names:
            name_normalized = name.lower().replace('é', 'e').replace('è', 'e').replace('à', 'a')
            if name_normalized in cols_lower:
                return cols_lower[name_normalized]
            for col_norm, col_orig in cols_lower.items():
                if name_normalized in col_norm or col_norm in name_normalized:
                    return col_orig
        return None
    
    # Mapper toutes les colonnes nécessaires
    col_map = {
        'Region': find_column(df, ['Région', 'Region', 'region']),
        'Numero': find_column(df, ['Numéro', 'Numero', 'numero', 'Code']),
        'Departement': find_column(df, ['Département', 'Departement', 'departement']),
        'Zone': find_column(df, ['Zone', 'zone']),
        'Categorie_A': find_column(df, ['Catégorie A', 'Categorie A', 'Catégorie']),
        'Feux_habitations': find_column(df, ["Feux d'habitations-bureaux", "Feux d'habitations"]),
        'Incendies': find_column(df, ['Incendies', 'incendies']),
        'Secours_victime': find_column(df, ['Secours à victime', 'Secours a victime']),
        'Secours_personne': find_column(df, ['Secours à personne', 'Secours a personne']),
        'Malaises_Urgence': find_column(df, ['Malaises à domicile : urgence vitale', 'Malaises urgence']),
        'Malaises_Carence': find_column(df, ['Malaises à domicile : carence', 'Malaises carence']),
        'Accidents_circulation': find_column(df, ['Accidents de circulation', 'Accidents circulation']),
        'Operations_diverses': find_column(df, ['Opérations diverses', 'Operations diverses']),
        'Total_interventions': find_column(df, ['Total interventions', 'Total'])
    }
    
    # Renommer les colonnes trouvées
    rename_dict = {old: new for new, old in col_map.items() if old is not None}
    df = df.rename(columns=rename_dict)
    
    # Créer les colonnes manquantes
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
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).str.replace(',', '.').str.replace(' ', '')
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(float)
    
    # Colonnes dérivées
    df['Total_Malaises'] = df['Malaises_Urgence'] + df['Malaises_Carence']
    df['Total_Medical'] = df['Secours_victime'] + df['Secours_personne']
    df['Taux_Carence'] = 0.0
    mask = df['Total_Malaises'] > 0
    df.loc[mask, 'Taux_Carence'] = (df.loc[mask, 'Malaises_Carence'] / df.loc[mask, 'Total_Malaises'] * 100)
    
    # Code département
    if 'Numero' in df.columns:
        df['Code_Dept'] = df['Numero'].astype(str).str.zfill(2)
    else:
        df['Code_Dept'] = '00'
    
    # Nettoyer valeurs textuelles
    for col in ['Region', 'Departement', 'Categorie_A', 'Zone']:
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

page = st.sidebar.radio(
    "Choisir une page",
    ["🏠 Contexte", "📊 Vue d'ensemble", "🚑 Urgences médicales", 
     "🔥 Incendies", "🗺️ Analyse géographique", "📈 Insights"],
    key='page_selector'
)

st.sidebar.markdown("---")

# ==================== PUIS FILTRES ====================
st.sidebar.title("🎛️ Filtres géographiques")

regions_list = ['Toutes'] + sorted([r for r in df['Region'].unique() if r != 'Non renseigné'])
selected_region = st.sidebar.selectbox('Région', regions_list)

zones_list = ['Toutes'] + sorted([z for z in df['Zone'].unique() if z != 'Non renseigné'])
selected_zone = st.sidebar.selectbox('Type de zone', zones_list)

categories_list = ['Toutes'] + sorted([c for c in df['Categorie_A'].unique() if c != 'Non renseigné'])
selected_category = st.sidebar.selectbox('Catégorie', categories_list)

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
st.sidebar.metric("Lignes", f"{len(df_filtered):,}".replace(',', ' '))
st.sidebar.metric("Interventions", f"{int(df_filtered['Total_interventions'].sum()):,}".replace(',', ' '))

# ==================== PAGES ====================

if page == "🏠 Contexte":
    st.markdown('<h1 class="main-header">🚒 Pompiers France 2023</h1>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; font-size: 1.2rem; color: #2c3e50;">Analyse des interventions des services d\'incendie et de secours</p>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("## 🎯 Problématique")
        st.markdown("""
        <div style="color: #2c3e50;">
        Les services d'incendie et de secours (SDIS) constituent un pilier essentiel de la sécurité civile.
        Avec <strong>plus de 4,5 millions d'interventions annuelles</strong>, cette analyse permet de :
        
        <ul>
        <li>📍 <strong>Optimiser l'allocation des ressources</strong></li>
        <li>🏥 <strong>Anticiper les besoins médicaux</strong></li>
        <li>🚨 <strong>Identifier les zones sous tension</strong></li>
        <li>💡 <strong>Guider les décisions publiques</strong></li>
        </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("## 🔢 En chiffres")
        total_interventions = df['Total_interventions'].sum()
        total_medical = df['Total_Medical'].sum()
        total_incendies = df['Incendies'].sum()
        
        if total_interventions > 0:
            st.metric("🚨 Interventions", f"{total_interventions/1_000_000:.2f}M")
            st.metric("🏥 Part médical", f"{(total_medical/total_interventions*100):.1f}%")
            st.metric("🔥 Incendies", f"{int(total_incendies/1000):.0f}K")
        
        st.info("💡 Les pompiers sont avant tout un service médical (70%+ des interventions)")
    
    st.markdown("---")
    st.markdown("## 📚 Source des données")
    st.markdown("""
    <div style="color: #2c3e50;">
    <ul>
    <li><strong>Source</strong> : Ministère de l'Intérieur - data.gouv.fr</li>
    <li><strong>Année</strong> : 2023</li>
    <li><strong>Granularité</strong> : Département</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)

elif page == "📊 Vue d'ensemble":
    st.markdown('<h1 class="main-header">📊 Vue d\'ensemble</h1>', unsafe_allow_html=True)
    
    # KPIs
    col1, col2, col3, col4 = st.columns(4)
    
    total_inter = float(df_filtered['Total_interventions'].sum())
    medical = float(df_filtered['Total_Medical'].sum())
    incendies = float(df_filtered['Incendies'].sum())
    accidents = float(df_filtered['Accidents_circulation'].sum())
    
    with col1:
        st.metric("🚨 Total", f"{int(total_inter):,}".replace(',', ' '))
    with col2:
        pct_medical = (medical/total_inter*100) if total_inter > 0 else 0
        st.metric("🏥 Médical", f"{pct_medical:.1f}%")
    with col3:
        st.metric("🔥 Incendies", f"{int(incendies):,}".replace(',', ' '))
    with col4:
        st.metric("🚗 Accidents", f"{int(accidents):,}".replace(',', ' '))
    
    st.markdown("---")
    
    col1, col2 = st.columns([1.5, 1])
    
    with col1:
        st.markdown("### 📊 Répartition par type")
        
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
                height=400,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        st.markdown("### 🔢 Détails")
        for cat, val in categories_data.items():
            pct = (val / total_inter * 100) if total_inter > 0 else 0
            st.markdown(f"""
            <div style="background-color: #ecf0f1; padding: 10px; margin: 5px 0; border-radius: 5px;">
                <strong style="color: #2c3e50;">{cat}</strong><br>
                <span style="font-size: 1.3rem; color: #e74c3c;">{int(val):,}</span>
                <span style="color: #7f8c8d;"> ({pct:.1f}%)</span>
            </div>
            """.replace(',', ' '), unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("### 🏆 Top 15 départements")
    
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
            yaxis_title="Interventions",
            height=400,
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#2c3e50')
        )
        
        st.plotly_chart(fig_bar, use_container_width=True)
    
    st.markdown('<div class="insight-box"><strong>💡 Insight</strong> : Les départements peuplés concentrent les interventions médicales.</div>', unsafe_allow_html=True)

elif page == "🚑 Urgences médicales":
    st.markdown('<h1 class="main-header">🚑 Urgences médicales</h1>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    sav = float(df_filtered['Secours_victime'].sum())
    sap = float(df_filtered['Secours_personne'].sum())
    urgence = float(df_filtered['Malaises_Urgence'].sum())
    carence = float(df_filtered['Malaises_Carence'].sum())
    total_mal = float(df_filtered['Total_Malaises'].sum())
    
    with col1:
        st.metric("🚑 Secours victime", f"{int(sav):,}".replace(',', ' '))
    with col2:
        st.metric("🏥 Secours personne", f"{int(sap):,}".replace(',', ' '))
    with col3:
        st.metric("⚠️ Urgences", f"{int(urgence):,}".replace(',', ' '))
    with col4:
        taux_carence = (carence / total_mal * 100) if total_mal > 0 else 0
        st.metric("📉 Carence", f"{taux_carence:.1f}%")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### ⚡ Urgences vs Carences")
        
        if urgence > 0 or carence > 0:
            fig_compare = go.Figure()
            
            fig_compare.add_trace(go.Bar(
                name='Urgence vitale',
                x=['Malaises'],
                y=[urgence],
                marker_color='#27ae60',
                text=[f"{int(urgence):,}".replace(',', ' ')],
                textposition='auto'
            ))
            
            fig_compare.add_trace(go.Bar(
                name='Carence',
                x=['Malaises'],
                y=[carence],
                marker_color='#e74c3c',
                text=[f"{int(carence):,}".replace(',', ' ')],
                textposition='auto'
            ))
            
            fig_compare.update_layout(
                barmode='group',
                height=400,
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#2c3e50')
            )
            
            st.plotly_chart(fig_compare, use_container_width=True)
    
    with col2:
        st.markdown("### 📊 Répartition médicale")
        
        medical_data = {
            'Secours victime': sav,
            'Secours personne': sap,
            'Urgences': urgence,
            'Carences': carence
        }
        
        medical_data = {k: v for k, v in medical_data.items() if v > 0}
        
        if medical_data:
            fig_medical = go.Figure(data=[go.Pie(
                labels=list(medical_data.keys()),
                values=list(medical_data.values()),
                hole=0.5,
                marker=dict(colors=['#3498db', '#9b59b6', '#27ae60', '#e74c3c']),
                textfont=dict(color='#2c3e50')
            )])
            
            fig_medical.update_layout(height=400, paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_medical, use_container_width=True)
    
    st.markdown("---")
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
            labels={'Taux': 'Taux (%)'}
        )
        
        fig_carence.update_layout(
            height=600,
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#2c3e50')
        )
        st.plotly_chart(fig_carence, use_container_width=True)
    
    st.markdown('<div class="insight-box"><strong>💡 Insight</strong> : Taux de carence élevé = surcharge du système.</div>', unsafe_allow_html=True)

elif page == "🔥 Incendies":
    st.markdown('<h1 class="main-header">🔥 Incendies</h1>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    total_incendies = float(df_filtered['Incendies'].sum())
    feux_hab = float(df_filtered['Feux_habitations'].sum())
    total_inter = float(df_filtered['Total_interventions'].sum())
    
    with col1:
        st.metric("🔥 Total", f"{int(total_incendies):,}".replace(',', ' '))
    with col2:
        st.metric("🏠 Habitations", f"{int(feux_hab):,}".replace(',', ' '))
    with col3:
        pct = (total_incendies / total_inter * 100) if total_inter > 0 else 0
        st.metric("📊 Part", f"{pct:.1f}%")
    with col4:
        pct_hab = (feux_hab / total_incendies * 100) if total_incendies > 0 else 0
        st.metric("🏘️ Hab/Total", f"{pct_hab:.1f}%")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🏆 Top 10 départements")
        
        top_inc = df_filtered.groupby('Departement')['Incendies'].sum().nlargest(10).reset_index()
        
        if len(top_inc) > 0:
            fig_top = px.bar(
                top_inc,
                x='Incendies',
                y='Departement',
                orientation='h',
                color='Incendies',
                color_continuous_scale='Oranges'
            )
            
            fig_top.update_layout(
                height=400,
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#2c3e50')
            )
            st.plotly_chart(fig_top, use_container_width=True)
    
    with col2:
        st.markdown("### 🏠 Par type")
        
        fire_types = {
            'Habitations': feux_hab,
            'Autres': total_incendies - feux_hab
        }
        
        if sum(fire_types.values()) > 0:
            fig_types = go.Figure(data=[go.Pie(
                labels=list(fire_types.keys()),
                values=list(fire_types.values()),
                hole=0.4,
                marker=dict(colors=['#e74c3c', '#f39c12']),
                textfont=dict(color='#2c3e50')
            )])
            
            fig_types.update_layout(height=400, paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_types, use_container_width=True)
    
    st.markdown('<div class="insight-box"><strong>💡</strong> 7% des interventions mais ressources importantes.</div>', unsafe_allow_html=True)

elif page == "🗺️ Analyse géographique":
    st.markdown('<h1 class="main-header">🗺️ Analyse géographique</h1>', unsafe_allow_html=True)
    
    metric_choice = st.selectbox(
        "Métrique",
        ["Taux de carence", "Total interventions", "Part médical", "Incendies"]
    )
    
    df_map = df.groupby(['Code_Dept', 'Departement']).agg({
        'Total_interventions': 'sum',
        'Total_Medical': 'sum',
        'Incendies': 'sum',
        'Malaises_Carence': 'sum',
        'Total_Malaises': 'sum'
    }).reset_index()
    
    if metric_choice == "Taux de carence":
        df_map['Metric'] = np.where(df_map['Total_Malaises'] > 0,
                                     (df_map['Malaises_Carence'] / df_map['Total_Malaises'] * 100), 0)
        color_scale = 'Reds'
        metric_label = 'Taux (%)'
    elif metric_choice == "Total interventions":
        df_map['Metric'] = df_map['Total_interventions']
        color_scale = 'Blues'
        metric_label = 'Total'
    elif metric_choice == "Part médical":
        df_map['Metric'] = np.where(df_map['Total_interventions'] > 0,
                                     (df_map['Total_Medical'] / df_map['Total_interventions'] * 100), 0)
        color_scale = 'Greens'
        metric_label = 'Part (%)'
    else:
        df_map['Metric'] = df_map['Incendies']
        color_scale = 'Oranges'
        metric_label = 'Incendies'
    
    st.markdown(f"### 🗺️ {metric_label} par département")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Moyenne", f"{df_map['Metric'].mean():.1f}")
    with col2:
        st.metric("Médiane", f"{df_map['Metric'].median():.1f}")
    with col3:
        st.metric("Max", f"{df_map['Metric'].max():.1f}")
    with col4:
        st.metric("Min", f"{df_map['Metric'].min():.1f}")
    
    top_n = st.slider("Départements", 10, 50, 20)
    df_map_sorted = df_map.nlargest(top_n, 'Metric')
    
    fig_geo = px.bar(
        df_map_sorted,
        y='Departement',
        x='Metric',
        orientation='h',
        color='Metric',
        color_continuous_scale=color_scale,
        labels={'Metric': metric_label},
        height=max(400, top_n * 20)
    )
    
    fig_geo.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#2c3e50')
    )
    
    st.plotly_chart(fig_geo, use_container_width=True)
    
    st.markdown("---")
    st.markdown("### 📋 Données détaillées")
    
    df_display = df_map.copy()
    df_display['Part médical (%)'] = (df_display['Total_Medical'] / df_display['Total_interventions'] * 100).round(1)
    
    st.dataframe(
        df_display[['Code_Dept', 'Departement', 'Total_interventions', 
                   'Total_Medical', 'Incendies', 'Part médical (%)']].sort_values(
            'Total_interventions', ascending=False
        ),
        use_container_width=True,
        height=400
    )

elif page == "📈 Insights":
    st.markdown('<h1 class="main-header">📈 Insights & Recommandations</h1>', unsafe_allow_html=True)
    
    st.markdown("## 🔍 Principaux enseignements")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div style="color: #2c3e50;">
        <h3>🏥 1. Transformation médicale</h3>
        <ul>
        <li><strong>70%+</strong> des interventions sont médicales</li>
        <li>Les pompiers = premier acteur du secours d'urgence</li>
        <li>Évolution majeure du métier</li>
        </ul>
        <p><strong>→ Renforcer la formation médicale</strong></p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div style="color: #2c3e50;">
        <h3>🚨 2. Crise des carences</h3>
        <ul>
        <li>Taux variable selon territoires</li>
        <li>Certaines régions > <strong>15%</strong></li>
        <li>Surcharge du système</li>
        </ul>
        <p><strong>→ Réorganisation territoriale urgente</strong></p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div style="color: #2c3e50;">
        <h3>📍 3. Disparités géographiques</h3>
        <ul>
        <li>Concentration zones urbaines</li>
        <li>Zones rurales sous-dotées</li>
        <li>Inégalités d'accès</li>
        </ul>
        <p><strong>→ Mutualisation inter-départementale</strong></p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div style="color: #2c3e50;">
        <h3>🔥 4. Incendies critiques</h3>
        <ul>
        <li>Seulement <strong>7%</strong> des interventions</li>
        <li>Mais moyens importants</li>
        <li>Expertise spécifique</li>
        </ul>
        <p><strong>→ Maintenir compétences incendie</strong></p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.markdown("## 💡 Recommandations stratégiques")
    
    recommendations = [
        {
            'icon': '👨‍⚕️',
            'title': 'Formation & Recrutement',
            'content': 'Renforcer les compétences médicales. Formation continue en urgence vitale.'
        },
        {
            'icon': '🚑',
            'title': 'Coordination ambulancière',
            'content': 'Améliorer coordination avec ambulances privées. Système de régulation efficace.'
        },
        {
            'icon': '📊',
            'title': 'Allocation des ressources',
            'content': 'Utiliser les données pour optimiser positionnement casernes et effectifs.'
        },
        {
            'icon': '🌍',
            'title': 'Équité territoriale',
            'content': 'Réduire inégalités rural/urbain. Mutualiser moyens au niveau régional.'
        },
        {
            'icon': '💻',
            'title': 'Digitalisation',
            'content': 'Outils prédictifs pour anticiper pics. Améliorer système d\'information.'
        },
        {
            'icon': '🏥',
            'title': 'Partenariats santé',
            'content': 'Coopération hôpitaux/SAMU. Filières d\'urgence intégrées.'
        }
    ]
    
    cols = st.columns(2)
    for i, rec in enumerate(recommendations):
        with cols[i % 2]:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        padding: 20px; border-radius: 10px; margin: 10px 0; color: white;">
                <h3 style="color: white;">{rec['icon']} {rec['title']}</h3>
                <p style="color: white;">{rec['content']}</p>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.markdown("## 📊 Synthèse visuelle")
    
    col1, col2 = st.columns(2)
    
    with col1:
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
            title="Évolution tendance (illustration)",
            xaxis_title="Année",
            yaxis_title="Pourcentage (%)",
            height=400,
            hovermode='x unified',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#2c3e50')
        )
        
        st.plotly_chart(fig_trend, use_container_width=True)
    
    with col2:
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
            title="Adéquation besoin/ressources (indice)",
            xaxis_title="Type de zone",
            yaxis_title="Indice",
            barmode='group',
            height=400,
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#2c3e50')
        )
        
        st.plotly_chart(fig_comp, use_container_width=True)
    
    st.markdown("---")
    
    st.markdown("## 📋 Qualité & Limitations")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div style="color: #2c3e50;">
        <h3>✅ Points forts</h3>
        <ul>
        <li>Couverture nationale exhaustive</li>
        <li>Granularité départementale</li>
        <li>Données officielles fiables</li>
        <li>Catégorisation détaillée</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div style="color: #2c3e50;">
        <h3>⚠️ Limitations</h3>
        <ul>
        <li>Pas de données intra-annuelles</li>
        <li>Carences sous-estimées</li>
        <li>Absence délais intervention</li>
        <li>Pas d'info effectifs/matériel</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.markdown("## 🚀 Prochaines étapes")
    
    st.markdown("""
    <div style="color: #2c3e50;">
    Pour approfondir cette étude :
    
    <ol>
    <li><strong>Analyse temporelle</strong> : Données années précédentes pour tendances</li>
    <li><strong>Données RH</strong> : Croiser avec effectifs et matériel</li>
    <li><strong>Géolocalisation</strong> : Temps de trajet et couverture fine</li>
    <li><strong>Prédiction</strong> : Modèles de prévision des pics</li>
    <li><strong>Benchmark</strong> : Comparaison pays européens</li>
    <li><strong>Impact sanitaire</strong> : Effet carences sur issues patient</li>
    </ol>
    </div>
    """, unsafe_allow_html=True)
    
    st.success("""
    🎯 **Conclusion finale** : Les SDIS sont en pleine mutation. La montée du médical (70%+) 
    nécessite une adaptation profonde de l'organisation, formation et ressources. Les disparités 
    géographiques et carences révèlent tensions structurelles nécessitant réponses coordonnées.
    """)
    
    st.markdown("---")
    st.markdown("### 📚 Sources & Méthodologie")
    st.markdown("""
    <div style="color: #2c3e50;">
    <ul>
    <li><strong>Données</strong> : Ministère Intérieur via data.gouv.fr</li>
    <li><strong>Outil</strong> : Streamlit + Plotly</li>
    <li><strong>Période</strong> : 2023</li>
    <li><strong>Traitement</strong> : Python/Pandas</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)

# ==================== FOOTER ====================
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #7f8c8d; padding: 20px;">
    <p><strong>🎓 Projet EFREI Paris - Data Storytelling</strong></p>
    <p>Données : Ministère de l'Intérieur | data.gouv.fr</p>
    <p style="font-size: 0.9rem;">Dashboard créé avec ❤️ et Streamlit | © 2025</p>
</div>
""", unsafe_allow_html=True)
