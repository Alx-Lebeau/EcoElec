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

### `consommation/conso-electricite-secteur.csv`

- **Contenu** : consommation finale d'électricité en France par secteur
  (résidentiel, tertiaire, industrie, agriculture, non affecté), en TWh, de 2012 à 2024.
- **Source** : ODRÉ, jeu « Consommation départementale annuelle », construit à partir
  des données locales de consommation du SDES (réseaux RTE, Enedis, entreprises
  locales de distribution, EDF-SEI pour les outre-mer).
- **Traitements** : somme des départements par année et par secteur, MWh → TWh
  (`consommation/telecharger.py` régénère le fichier).
- **Précautions** : consommation livrée aux sites, hors pertes et hors secteur
  de l'énergie, donc inférieure à la consommation nationale publiée par RTE
  (environ 410 TWh contre 449 TWh en 2024). Rupture de série en 2018 (une partie
  du résidentiel reclassée en tertiaire) : comparer les années avec prudence.
- **Licence** : Licence Ouverte v2.0 (Etalab).

### `mix/mix-france.csv`

- **Contenu** : capacité installée au 31 décembre (GW) et production annuelle (TWh)
  par filière en France, de 2012 à la dernière année publiée.
- **Source** : RTE, jeux ODRÉ « Parc national annuel de production par filière » et
  « Production nationale annuelle par filière ». Toutes installations raccordées aux
  réseaux publics (RTE, Enedis, EDF SEI, entreprises locales de distribution).
- **Traitements** : MW → GW ; fioul et charbon regroupés (« charbon-fioul »)
  ; `mix/telecharger.py` régénère le fichier.
- **Précautions** : RTE a recalculé l'autoconsommation photovoltaïque ; le parc et
  la production solaires de 2022 à 2024 ont été revus à la hausse. Les données de la
  dernière année peuvent encore être révisées.
- **Licence** : Licence Ouverte v2.0 (Etalab).

### `acteurs/marche-detail-electricite.csv`

- **Contenu** : indicateurs du marché de détail de l'électricité au 30 juin 2026 :
  sites et consommation, parts des offres de marché et des fournisseurs alternatifs,
  sites résidentiels aux tarifs réglementés, nombre de fournisseurs.
- **Source** : CRE, *Observatoire des marchés de détail, deuxième trimestre 2026*
  (30 septembre 2026), synthèse et figures 4 et 5 ; saisie manuelle.
- **Précautions** : `fournisseurs_residentiels_min` compte les fournisseurs engagés
  dans les lignes directrices de la CRE et actifs auprès des résidentiels (75, plus de
  98 % des clients) : c'est un minimum. Les parts sont arrondies par la CRE.
- **Mise à jour** : chaque trimestre, depuis l'observatoire suivant.

### `acteurs/production-par-acteur.csv`

- **Contenu** : production 2025 en France des principaux producteurs identifiables
  (EDF nucléaire, EDF hydraulique, CNR), en TWh. Le reste de la production
  (« autres producteurs ») se calcule par différence avec `mix/mix-france.csv`.
- **Sources** : EDF, communiqué des résultats annuels 2025 (25 février 2026) ;
  CNR, bilan 2025 rapporté par la presse (*LyonMag*, 2026) ; RTE pour le total.
  Saisie manuelle.
- **Précautions** : chiffres communiqués par les entreprises. La production éolienne,
  solaire et thermique d'EDF en France n'est pas publiée séparément (le chiffre
  « éolien et solaire » d'EDF couvre le groupe, hors de France compris) : elle est
  comptée dans « autres producteurs », ce qui sous-estime la part d'EDF.

### `consommation/courbe-charge-2025.csv`

- **Contenu** : consommation nationale horaire en 2025 (GW, heure locale de Paris).
- **Source** : RTE, « Données éCO2mix nationales consolidées et définitives » (ODRÉ).
- **Traitements** : pas de 15 ou 30 minutes moyenné par heure, MW → GW ;
  `consommation/telecharger_courbe.py ANNÉE` régénère le fichier. L'heure du passage
  à l'heure d'été n'existe pas (8 759 heures).
- **Licence** : Licence Ouverte v2.0 (Etalab).

### `consommation/temperature-2025.csv`

- **Contenu** : température moyenne quotidienne de la France métropolitaine en 2025 (°C).
- **Sources** : Météo-France, « Données climatologiques de base - quotidiennes »
  (data.gouv.fr), champ TNTXM ; pondération : consommation électrique résidentielle et
  tertiaire par département (SDES, via ODRÉ).
- **Traitements** : moyenne des stations de chaque département (stations de plus de
  800 m exclues), puis moyenne des départements pondérée par leur consommation
  résidentielle et tertiaire. `consommation/telecharger_temperature.py ANNÉE` régénère
  le fichier (fichiers Météo-France mis en cache dans `data/telechargements/`).
- **Précautions** : construction propre au cours, proche dans l'esprit de la
  température de référence de RTE mais pas identique.
- **Licence** : Licence Ouverte v2.0 (Etalab).

### `consommation/thermosensibilite-rte.csv`

- **Contenu** : thermosensibilité hivernale de la consommation française publiée par RTE
  (2,4 GW par degré perdu en vague de froid).
- **Source** : RTE, *L'équilibre offre-demande d'électricité pour l'hiver 2021-2022*
  (novembre 2021), entrée `rte-hiver-2021-2022` de `commun/biblio.bib` ; saisie manuelle.
- **Précautions** : chiffre de référence repris par RTE d'un bilan à l'autre depuis
  2017 ; pas de valeur plus récente trouvée dans les publications de 2025-2026.

## À migrer

- Consommation France et disponibilités horaires 2024 des TP (source ENTSO-E
  Transparency) : conditions de réutilisation et origine des disponibilités
  constantes (nucléaire, hydraulique, gaz) à documenter avant migration.
