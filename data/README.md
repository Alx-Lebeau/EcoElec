# data/

Petits jeux de données utilisés par le poly, les slides et les TP. Les figures
sont produites par du code à partir de ces fichiers, jamais collées à la main.

## Règles

- **Le dépôt deviendra public** : n'y verser que des données redistribuables.
  - ODRÉ et éCO2mix (RTE) : Licence Ouverte, redistribuables.
  - ENTSO-E Transparency : conditions de réutilisation à vérifier avant tout dépôt.
  - EPEX, EEX : licence commerciale, **jamais** dans le dépôt.
- Gros volumes : un script de téléchargement plutôt qu'un fichier versionné.
  Les fichiers téléchargés vont dans `data/telechargements/`, ignoré par git.
- Chaque jeu de données est documenté ci-dessous : source, date, traitements, licence.

## Jeux de données

### `exemple/merit-order-illustratif.csv`

- **Contenu** : capacité (GW) et coût variable (€/MWh) de six filières.
- **Source** : valeurs illustratives du TP 01 (dépôt Cours-EcoElec), capacités converties de MW en GW.
- **Usage** : module d'exemple uniquement. Ce n'est pas le système stylisé commun
  (« fil rouge »), qui reste à définir.
- **Licence** : CC BY-SA 4.0.

## À migrer

- Consommation France et disponibilités horaires 2024 des TP (source ENTSO-E
  Transparency) : conditions de réutilisation et origine des disponibilités
  constantes (nucléaire, hydraulique, gaz) à documenter avant migration.
