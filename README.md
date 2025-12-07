# 🚒 Pompiers France 2023 - Dashboard Analytique

## 🌐 Accès direct au dashboard
**👉 [https://pompiers-france-2023.streamlit.app](https://pompiers-france-2023.streamlit.app/#pompiers-france-2023)**

---

## 📋 Description

Dashboard interactif d'analyse des interventions des services d'incendie et de secours (SDIS) en France pour l'année 2023. Ce projet propose une visualisation complète et intuitive des **4,77 millions d'interventions** recensées sur le territoire français.

### 🎯 Objectifs
- Comprendre la répartition des interventions par type et géographie
- Identifier les zones sous tension et les problématiques de carences
- Analyser la transformation du rôle des pompiers (médicalisation croissante)
- Fournir des insights stratégiques pour l'optimisation des ressources

---

## 📊 Fonctionnalités

### 6 pages d'analyse

1. **🏠 Contexte** : Présentation de la problématique et chiffres clés
2. **📊 Vue d'ensemble** : KPIs globaux et répartition par type d'intervention
3. **🚑 Urgences médicales** : Focus sur les interventions médicales et taux de carence
4. **🔥 Incendies** : Analyse spécifique des feux (habitations, autres)
5. **🗺️ Analyse géographique** : Comparaison départementale et régionale
6. **📈 Insights** : Recommandations stratégiques et conclusions

### 🎛️ Filtres dynamiques
- Filtrage par région
- Filtrage par type de zone (urbain/rural)
- Filtrage par catégorie démographique

---

## 🔑 Points clés découverts

### 🏥 Transformation médicale
- **71,8%** des interventions sont des secours à victime
- **79,2%** si on inclut les secours à personne
- Les pompiers sont devenus le premier acteur du secours d'urgence en France

### 🚨 Problématique des carences
- Taux de carence variable selon les territoires
- Certaines régions dépassent **15%** de carences
- Indicateur clé de surcharge du système de santé

### 📍 Disparités territoriales
- Forte concentration des interventions dans les zones urbaines
- Zones rurales confrontées à des défis d'accessibilité
- Nécessité de mutualisation inter-départementale

### 🔥 Incendies
- Seulement **5,8%** des interventions totales
- Mais requièrent des moyens et une expertise spécifiques
- Maintien des compétences incendie reste crucial

---

## 🛠️ Technologies utilisées

- **Python 3.10+**
- **Streamlit** : Framework de visualisation
- **Pandas** : Manipulation des données
- **Plotly** : Graphiques interactifs
- **NumPy** : Calculs numériques

---

## 📦 Installation locale

### Prérequis
```bash
pip install streamlit pandas numpy plotly
```

### Lancement
```bash
streamlit run pompiers_dashboard.py
```

Le fichier de données `interventions2023.csv` doit être placé dans le même répertoire que le script.

---

## 📂 Structure des données

### Colonnes principales utilisées
- **Région / Département** : Localisation géographique
- **Total interventions** : Nombre total d'interventions
- **Secours à victime / personne** : Interventions médicales
- **Malaises urgence / carence** : Détail des interventions médicales
- **Incendies** : Dont feux d'habitations
- **Accidents de circulation** : Interventions routières
- **Opérations diverses** : Autres types d'interventions

### Source
- **Origine** : Ministère de l'Intérieur
- **Plateforme** : data.gouv.fr
- **Année** : 2023
- **Granularité** : Départementale

---

## 💡 Recommandations stratégiques

Le dashboard met en lumière 6 axes d'amélioration prioritaires :

1. **👨‍⚕️ Formation médicale** : Renforcer les compétences en urgence vitale
2. **🚑 Coordination** : Meilleure intégration avec le système ambulancier
3. **📊 Allocation des ressources** : Optimisation data-driven
4. **🌍 Équité territoriale** : Réduction des inégalités rural/urbain
5. **💻 Digitalisation** : Outils prédictifs et systèmes d'information
6. **🏥 Partenariats santé** : Coopération renforcée hôpitaux/SAMU

---

## ⚠️ Limitations

- Données agrégées annuelles (pas de saisonnalité intra-annuelle)
- Taux de carence potentiellement sous-estimés
- Absence de données sur les délais d'intervention
- Pas d'informations sur les effectifs et le matériel

---

## 👨‍🎓 À propos

**Projet académique** réalisé par **Willen CHIBOUT**  
Dans le cadre du cours de **Data Visualization & Analysis**  
**EFREI Paris** - 2025

---

## 📄 Licence

Projet éducatif - Données publiques (Ministère de l'Intérieur)

---

## 🤝 Contact

Pour toute question ou suggestion d'amélioration, n'hésitez pas à me contacter !

**🔗 Dashboard en ligne** : [https://pompiers-france-2023.streamlit.app](https://pompiers-france-2023.streamlit.app/#pompiers-france-2023)
