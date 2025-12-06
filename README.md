# Interventions des Sapeurs-Pompiers en France (2023)

Dashboard interactif analysant les 4.7 millions d'interventions des pompiers francais en 2023.

## Contexte et problematique

On associe souvent les pompiers a la lutte contre les incendies. Pourtant, les donnees revelent une realite differente : en 2023, seulement 3% des interventions concernaient des feux. La grande majorite (88%) etait des urgences medicales.

Plus revelateur encore : le phenomene des "carences", ces interventions ou les pompiers remplacent les ambulances indisponibles. Plus de 200 000 cas en 2023, un indicateur de tension du systeme de sante.

## Structure narrative

Le dashboard suit une progression claire :

1. **Constat initial** : Decalage entre perception et realite du metier
2. **Analyse des donnees** : Repartition des types d'interventions
3. **Focus sur les carences** : Le role de substitution des pompiers
4. **Dimension geographique** : Disparites regionales
5. **Implications** : Consequences pour les pompiers et les citoyens

## Fonctionnalites

- Filtres interactifs par region, type de territoire et categorie de SDIS
- KPIs dynamiques qui s'adaptent aux filtres selectionnes
- 4 visualisations interactives (Plotly)
- Section qualite des donnees avec documentation des limites

## Installation

```bash
pip install -r requirements.txt
streamlit run app.py
```

Le fichier `interventions2023.csv` doit etre present dans le repertoire racine.

## Source des donnees

**Dataset** : Interventions realisees par les services d'incendie et de secours  
**Editeur** : Ministere de l'Interieur - DGSCGC  
**Annee** : 2023  
**Licence** : Licence Ouverte / Open Licence  
**Lien** : [data.gouv.fr](https://www.data.gouv.fr/datasets/interventions-realisees-par-les-services-d-incendie-et-de-secours/)

## Technologies

- Python 3.10+
- Streamlit
- Pandas
- Plotly
- NumPy

## Limites identifiees

- Donnees agregees au niveau departemental uniquement
- Methodes de comptage potentiellement variables selon les SDIS
- BSPP et BMPM : unites militaires au fonctionnement specifique

---

Projet realise dans le cadre du cours de Data Visualization - EFREI Paris  
#EFREIDataStories2025
