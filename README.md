# Les Pompiers en France - 2023

Quand on pense aux pompiers, on imagine des camions rouges qui foncent eteindre des incendies. 
En vrai ? En 2023, seulement 3% de leurs interventions concernent des feux. Le reste, c'est surtout des urgences medicales.

Et le truc fou : plus de 200 000 fois dans l'annee, ils sont intervenus juste parce qu'aucune ambulance n'etait dispo. Ca s'appelle une "carence".

Ce dashboard explore ca.

## Le projet

C'est un dashboard Streamlit qui raconte une histoire simple :
- On croit que les pompiers eteignent des feux
- En fait ils font surtout des urgences medicales
- Et souvent ils remplacent les ambulances qui manquent
- C'est un signe que le systeme de sante est sous tension

## Lancer l'app

```
pip install -r requirements.txt
streamlit run app.py
```

Faut que le fichier `interventions2023.csv` soit dans le meme dossier.

## Les donnees

Ca vient de data.gouv.fr, c'est les stats officielles du Ministere de l'Interieur sur toutes les interventions des pompiers en 2023.

Lien : https://www.data.gouv.fr/datasets/interventions-realisees-par-les-services-d-incendie-et-de-secours/

## Ce qu'il y a dans le dashboard

- Des filtres pour explorer par region ou type de territoire
- Les chiffres cles qui changent selon les filtres
- Un graphique sur la repartition des interventions
- Une analyse des carences (quand les pompiers remplacent les ambulances)
- Une comparaison entre regions
- Une section sur la qualite des donnees

---

EFREI Paris - Data Visualization  
#EFREIDataStories2025
