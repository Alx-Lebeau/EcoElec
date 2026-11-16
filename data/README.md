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

### `couts/prix-gaz-co2.csv`

- **Contenu** : prix annuels publiés par la CRE, 2022 à 2025 : gaz naturel au PEG
  (`gaz_eur_mwh`, €/MWh de gaz, moyenne des prix *day-ahead*) et quota de CO₂
  (`co2_eur_t`, €/t, moyenne du contrat de référence de décembre de l'année), avec le
  minimum et le maximum de l'année pour le CO₂ (`co2_min`, `co2_max`), et l'écart
  moyen entre le TTF et le PEG *day-ahead* (`ecart_ttf_peg`, €/MWh).
- **Sources** : CRE, *La surveillance et le fonctionnement des marchés de gros de
  l'électricité et du gaz naturel*, rapports 2022 (§ 3 p. 31 : CO₂ 81,3 €/t, maximum
  98 €/t le 19 août, gaz 98,1 €/MWh), 2023 (p. 33 : CO₂ 85,3 €/t entre 66,4 et
  100,3), 2024 (p. 84 : CO₂ 66,5 €/t entre 52,4 et 77,5) et 2025 (rapport n° 2026-07,
  synthèse p. 13, p. 64 et annexe : CO₂ 74,9 €/t entre 61,1 et 88,5, gaz 2023-2025).
  Entrée `cre-surveillance-2025` de `commun/biblio.bib`. Saisie manuelle.
- **Précautions** : gaz 2023 révisé de 38,8 (rapport 2023) à 38,9 €/MWh (rapport
  2025), valeur la plus récente retenue. Minimum 2022 du CO₂ non publié (« sous la
  barre des 60 € »). Prix sources EEX, ICE et Argus, publiés sous forme agrégée par
  la CRE seulement : aucune série quotidienne ou mensuelle du quota sous licence ouverte.
- **Mise à jour** : chaque année, depuis le rapport de surveillance suivant.

### `couts/prix-gaz-ttf-mensuel.csv`

- **Contenu** : prix mensuel du gaz naturel en Europe, d'avril 2015 au dernier mois
  publié : `gaz_usd_mmbtu` ($/mmbtu), `usd_par_eur`, `gaz_eur_mwh` (€/MWh PCS).
- **Sources** : Banque mondiale, *Commodity Price Data* (Pink Sheet), série « Natural
  gas, Europe », TTF néerlandais depuis avril 2015, CC BY 4.0. BCE, taux de change
  EUR/USD mensuel moyen (série EXR.M.USD.EUR.SP00.A).
- **Traitements** : conversion $/mmbtu → €/MWh (1 mmbtu = 0,293071 MWh), au taux du
  mois. `couts/telecharger.py` régénère le fichier (`uv run data/couts/telecharger.py`).
  L'adresse du classeur de la Banque mondiale change chaque année.
- **Précautions** : la Banque mondiale ne précise pas le contrat (*day-ahead* ou mois
  suivant). Ses moyennes annuelles sont plus proches du contrat du mois suivant :
  132 €/MWh en 2022, contre 120 €/MWh pour le TTF *day-ahead* (PEG *day-ahead* plus
  écart TTF-PEG, CRE). Écart de l'ordre de 1 €/MWh avec les moyennes PEG de la CRE (hub
  différent), sauf en 2022 où le PEG a coté en moyenne 22,3 €/MWh sous le TTF (CRE,
  rapport 2022).

### `couts/centrales-gaz.csv` et `couts/gaz-naturel.csv`

- **Contenu** : rendement sur pouvoir calorifique inférieur (`rendement_pci`) et coût
  variable d'exploitation et de maintenance (VOM, €/MWh électrique) des CCG et des TAC.
  Constantes du gaz naturel : facteur d'émission (tCO₂/MWh PCI) et rapport PCI/PCS.
  `pyelec.dispatch.load_gas_plants` en déduit rendement et facteur d'émission par
  MWh PCS, l'unité des prix du gaz.
- **Sources** :
  - rendements (55 % et 35 %) : CRE, rapport de surveillance 2025, note 85 p. 77,
    « rendement théorique », base non précisée, lue ici en PCI (convention usuelle) ;
  - facteur d'émission : GIEC, lignes directrices 2006, vol. 2, tableau 1.4,
    56 100 kgCO₂/TJ PCI, soit 0,202 tCO₂/MWh PCI (`giec-2006-energie`) ;
  - rapport PCI/PCS de 0,9 : ADEME, Base Carbone, combustion du gaz naturel
    0,181 kgCO₂e/kWh PCS et 0,201 kgCO₂e/kWh PCI (`ademe-base-carbone`) ;
  - VOM : ENTSO-E, *ERAA 2024, Annex 1: Assumptions*, tableau 15 (CCGT 2,3 à
    2,7 €/MWh, milieu de fourchette retenu, OCGT 2,4 €/MWh), `entsoe-eraa-2024-hypotheses`.
- **Précautions** : la CRE retient 0,198 tCO₂ par MWh de gaz avec un rendement de
  55 %, sans préciser la base. Le cours travaille en base cohérente (tout par MWh PCS),
  d'où un coût variable plus élevé d'environ 8 % que celui de la CRE. Une centrale
  réelle s'écarte des valeurs de référence selon son âge, sa charge et ses démarrages.

### `exemple/parc-court-terme.csv` et `exemple/demande-court-terme.csv`

- **Contenu** : parc illustratif du module court terme, capacité disponible (GW) de
  quatre filières et valeur d'usage (€/MWh) de celles qui n'achètent pas de
  combustible. Le coût variable des CCG et des TAC est calculé depuis `couts/`.
  Demande illustrative pour deux situations : usages non flexibles (GW, valorisés
  à la VOLL) et largeur de la partie flexible (GW).
- **Source** : valeurs choisies pour l'exemple, ordres de grandeur d'une heure
  d'hiver en France sans prétention de réalisme. La valeur d'usage du nucléaire
  n'est pas calculée.
- **Licence** : CC BY-SA 4.0.

## À migrer

- Consommation France et disponibilités horaires 2024 des TP (source ENTSO-E
  Transparency) : conditions de réutilisation et origine des disponibilités
  constantes (nucléaire, hydraulique, gaz) à documenter avant migration.
