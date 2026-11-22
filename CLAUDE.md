# CLAUDE.md — dépôt EcoElec

Consignes pour travailler dans ce dépôt. Les choix de conception du cours
(organisation, banque de modules, état d'avancement) sont tenus hors du dépôt,
dans le projet de travail de l'auteur ; ce fichier couvre la mise en œuvre.

## Le projet

Cours modulaire d'économie de l'électricité. Un seul projet Quarto produit le
poly (livre HTML + PDF), les slides (reveal.js, un deck par séance, aussi en HTML
autonome et en PDF) et les TP (notebooks). Le cours est une banque de modules ;
chaque format (3h, 6h, 12h) ou session y pioche au moyen d'un parcours. Chaque
module a une *base* (contenu non marqué, présent partout) et deux *options* qu'un
parcours ajoute ou non : `approfondissement` et `formel`. Le mot « avancé » est
proscrit : il confond les deux options. « Socle » désigne les modules communs à
tous les formats, pas la base d'un module.

## Commandes

```sh
uv sync                                          # environnement (versions figées dans uv.lock)
uv run pytest                                    # tests de l'outillage et des filtres
uv run ecoelec verifier                          # modules, parcours, chapitres du poly
uv run ecoelec generer                           # vérifie puis génère decks/
uv run quarto render --profile poly              # poly → _rendu/poly/
uv run quarto render --profile slides            # decks → _rendu/slides/
uv run quarto render decks/parcours --profile slides,autonome --output-dir _rendu/autonome
uv run ecoelec pdf                               # PDF des decks autonomes (decktape, Chrome)
uv run quarto render --profile outils            # outils interactifs (OJS) → _rendu/outils/
uv run ecoelec site                              # adresses courtes des parcours (_rendu/parcours/)
npm ci --prefix accueil && npm run build --prefix accueil   # accueil React → _rendu/index.html
npm run preview --prefix accueil                 # sert tout _rendu/ (http://localhost:4173)
uv run ecoelec controler poly.log slides.log     # avertissements Quarto, images manquantes
uv run ecoelec nouveau-module ID --titre "…"     # module en ébauche
```

Toujours lancer `ecoelec generer` avant de rendre les slides. Quarto est installé à
part (version figée dans `.github/workflows/rendu.yml`) ; `uv run quarto …` lui
fournit le Python du projet.

## Arborescence

| Chemin | Contenu |
|---|---|
| `_quarto.yml`, `_quarto-*.yml` | configuration commune et profils `poly`, `slides`, `autonome`, `outils` |
| `commun/` | macros, bibliographie, thèmes, filtres Lua (voir `commun/README.md`) |
| `modules/<id>/` | `module.yml`, `poly.qmd` (chapitre), `slides.qmd` (slides marquées), `tp/`, `outil.qmd` et `modele.js` (outil OJS, port JS d'un modèle de `pyelec`, testé par `tests/test_modele_js.py`) |
| `modules/_exemple/` | module de démonstration des marques, hors poly et parcours, rendu par la CI |
| `parcours/*.yml` | un parcours par format type ou par session réelle |
| `pyelec/` | code partagé : chemins, palette, style, figures, schémas (`schema`, `organisation`, `lois`) |
| `outils/` | commande `ecoelec` |
| `data/` | petits jeux de données ouverts par thème, documentés dans `data/README.md` |
| `accueil/` | accueil du site (React + Vite), lit `decks/catalogue.json` |
| `decks/` | **généré** par `ecoelec generer`, non versionné : ne jamais l'éditer (dont `catalogue.json`, données de l'accueil) |
| `_freeze/` | résultats de calcul en cache, non versionnés (cache de la CI) |

## Modules

`module.yml` :

```yaml
titre: "Équilibre de court terme et formation des prix"
prerequis: [systeme]          # identifiants de modules
objectifs:                    # affichés en ouverture du module dans chaque deck
  - Construire un merit order et en déduire le prix
duree: 30                     # minutes de la base ; null tant que non estimée
supplements: {approfondissement: 45, formel: 10}   # minutes ajoutées par option
tp: [tp-court-terme]          # notebooks modules/<id>/tp/<tp>.ipynb
```

- `supplements` est facultatif. Une option sans supplément compte pour 0 si les
  slides n'ont pas la marque correspondante, sinon sa durée est « à estimer ».
- Un module n'a ni introduction ni conclusion générales : elles appartiennent au
  parcours (clés `introduction` et `conclusion` d'une séance). Il se termine en
  revanche par une slide « À retenir » propre au module (`::: {.a-retenir}` autour
  d'une liste numérotée).
- `poly.qmd` commence par `# Titre {#sec-<id>}` puis l'inclusion des macros.
  Tout nouveau chapitre est ajouté à la liste de `_quarto-poly.yml` (`ecoelec verifier` le contrôle).
- `slides.qmd` ne contient que des slides `##`, sans en-tête YAML : le générateur
  ajoute le titre du module, les objectifs et les options.

## Marques (slides)

| Marque | Visible dans |
|---|---|
| `.approfondissement` | les decks qui prennent l'option `approfondissement` |
| `.formel` | les decks qui prennent l'option `formel` |
| `.rappel` | les parcours où un prérequis ne précède pas le module ; `module="id"` pour un prérequis précis |

- Slide entière : `## Titre {.formel}` (jusqu'au titre suivant de même niveau ou au `---` suivant).
- Bloc : `::: {.formel}` … `:::`. Passage : `[texte]{.formel}`.
- Marques cumulées sur un élément : visible seulement si toutes le sont.
- **Règle d'or** : un contenu non marqué ne s'appuie jamais sur un contenu marqué
  (pas de renvoi `@eq-…` vers une équation `.formel` depuis du texte commun), et
  un contenu `.formel` ne s'appuie pas sur un contenu `.approfondissement` (ni
  l'inverse) sans porter les deux marques. La CI rend chaque module en base seule
  (`base`) et avec toutes les options (`integral`), plus les decks des parcours,
  et échoue sur tout renvoi non résolu.
- Pas de marque `.intuitif` : la base tient seule, sans phrase de liaison réservée
  aux decks sans maths (`ecoelec verifier` refuse la marque).
- Le formalisme s'ajoute à l'intuition : graphique et raisonnement communs, maths en surcouche.
- Vérifier dans la vue auteur (`_rendu/slides/decks/modules/<id>/auteur.html`) que
  le discours tient avec ou sans chaque option, et dans `base` comme dans `integral`
  qu'aucune slide ne déborde à 1280 × 720 (taille de projection).
- Parties d'un module : `## Titre {partie="Système physique"}` sur la première slide
  de chaque partie (étiquette et barre de progression, filtre `parties.lua`).
- Mise en page : classes de `commun/slides.scss` (`schema-focus`, `sous-schema`,
  `figure-large`, `attention`, `a-retenir`), décrites dans `commun/README.md`.

Poly : pas de marques. Les développements mathématiques vont dans
`::: {.formalisation titre="…"}` (encadré replié en HTML).

## Parcours

```yaml
titre: Comprendre le prix de l'électricité
options: [formel]                    # facultatif, pour tout le parcours
seances:
  - titre: Du merit order au prix de long terme
    duree: 90
    modules:
      - court-terme
      - long-terme: {avec: approfondissement}   # exception : option en plus
      - cadre: {sans: formel}                   # exception : option en moins
```

Sans `options`, le parcours ne prend que la base de chaque module.
`publie: false` masque un parcours sur le site (accueil, adresse courte) : il reste
vérifié et ses decks sont générés et rendus.

`ecoelec generer` vérifie que les durées tiennent dans chaque séance, signale les
prérequis absents (les slides `.rappel` sont alors incluses) et produit, par
parcours, une page des séances avec les chapitres du poly à lire.

## Code

- Identifiants (variables, fonctions, modules Python) en anglais ; commentaires,
  docstrings et messages en français. Noms de dossiers et sous-commandes en français.
- Chemins : toujours `pyelec.DATA_DIR` / `pyelec.ROOT`, jamais de chemin relatif
  (les documents s'exécutent depuis des dossiers différents).
- Couleurs et libellés des filières : `pyelec.color()` et `pyelec.label()` uniquement ;
  couleurs de mise en évidence des schémas : `pyelec.schema.ACCENTS`.
- Schéma du système électrique : `pyelec.schema.grid_diagram`, recoloré avec
  `highlight` plutôt que redessiné.
- Figures : `pyelec.style.use()`, puis `style.add_source(fig, source, date)` sous chaque figure
  de données (pas sous les schémas de principe).
- Slides : figures de données interactives en ECharts (`pyelec.echarts`, option calculée en
  Python, cellule `output: asis`, `source` et `date` passées à `chart`). Schémas matplotlib
  en SVG, texte vectorisé en Source Sans 3 (`style.use_svg()`). `ecoelec generer` charge
  ECharts dans les decks qui en ont besoin. Les figures matplotlib de `pyelec.figures` restent la version statique (poly, TP).
- Code réutilisé d'un module à l'autre : dans `pyelec`, pas copié dans les documents.
- Optimisation : PuLP avec HiGHS.
- `uv run ruff check . && uv run ruff format .` avant de valider.

## Rédaction

- Français ; reformulation minimale, tournures impersonnelles, rapport signal/bruit élevé.
- Pas de point-virgule : couper en deux phrases ou mettre une virgule.
- Sigles : jamais sans les expliciter à leur première occurrence. Sur une slide
  qui réemploie des sigles vus longtemps avant, cartouche de rappel `::: {.sigles}`
  (liste en fin de slide, classe de `commun/slides.scss`).
- Formulations épicènes : « le public », « les élèves », « on » plutôt que « le lecteur », « l'étudiant ».
- Typographie : guillemets « » ; les espaces insécables avant `: ; ! ?` et dans
  les guillemets sont posées automatiquement au rendu (`typographie.lua`) :
  écrire des espaces ordinaires.
- Notations mathématiques : macros de `commun/_macros.qmd` (seule source).
- Aucun chiffre recopié à la main dans une slide : le calculer depuis `data/`.
- Chiffres et éléments réglementaires datés : vérifier contre des sources
  actuelles, signaler toute modification, citer les sources (`commun/biblio.bib`).

## Site publié

Un seul site GitHub Pages (job `publier` de la CI, sur `main`), de racine `_rendu/` :

- `index.html` et `accueil/` : accueil React (`accueil/`, Vite), construit par
  `npm run build` dans `_rendu/` sans effacer les rendus Quarto. Vues adressées par le
  fragment de l'URL : `#/` (sections `#/parcours`, `#/modules`, `#/outils`),
  `#/parcours/<nom>` (séances : decks en ligne, autonomes et PDF, chapitres, outils),
  `#/modules/<id>` (objectifs, durées, prérequis, ressources, parcours qui l'utilisent).
- Données : `decks/catalogue.json`, écrit par `ecoelec generer` (`outils/site.py`) avec
  les chemins des rendus relatifs à `_rendu/`. Toute information affichée vient de là :
  pas de contenu de cours écrit dans les composants React.
- `parcours/<nom>/` : adresse courte d'un parcours, redirige vers `#/parcours/<nom>`
  (`ecoelec site`).
- `poly/`, `slides/`, `autonome/`, `outils/` : rendus Quarto. Leur barre de navigation
  renvoie à l'accueil (`../index.html`).
- Liens entre rendus : chemins relatifs, ou `{{< meta site-cours >}}` (adresse du
  site, `_quarto.yml`) depuis les slides, dont les decks autonomes et les PDF.
- Thème : une seule charte (`commun/charte.scss`) pour les slides, le poly, les outils
  et l'accueil (`accueil/src/style.scss`). Ordre des couches et mode sombre :
  `commun/README.md`. En-têtes du poly, des outils et de l'accueil identiques : les
  modifier ensemble.
- Textes de l'interface de l'accueil en français, espaces insécables écrites (`NBSP`
  de `accueil/src/format.js`) : `typographie.lua` ne s'applique pas à l'accueil.

## Données et publication

Le dépôt deviendra public : ni données internes, ni données sous licence
restrictive (EPEX, EEX), ni contenus d'autres personnes sans leur accord (pas de
logos d'entreprises). Voir `data/README.md`.

- Données ouvertes (ODRÉ, éCO2mix) : un script `data/<thème>/telecharger.py`
  régénère le fichier versionné.
- Chiffres saisis à la main depuis un rapport (CRE, entreprises) : dans un CSV de
  `data/`, avec source, date et précautions dans `data/README.md` ; jamais dans la slide.

## Points techniques

- **Empreinte des decks** : `freeze: auto` ne réexécute un document que si son
  propre texte change. Chaque deck généré porte une empreinte de ses sources
  (fichiers inclus, `pyelec/`, `data/`), donc toute modification de l'une d'elles
  le fait réexécuter. Les chapitres du poly n'en ont pas : après une modification
  de `pyelec/` ou `data/`, supprimer `_freeze/modules/<id>/` ou rendre le chapitre seul.
- **`_freeze/` n'est pas versionné** (historique alourdi par les PNG à chaque
  retouche). La CI le conserve avec `actions/cache`, clé calculée sur le code, les
  données et les sources : tout changement relance les calculs. Ne pas le commiter ;
  seule exception envisageable, un document au calcul long (optimisation), dont on
  versionnerait le seul dossier `_freeze`.
- `commun/_macros.qmd` ne contient que des `\providecommand` : tout autre contenu
  apparaîtrait dans les documents.
- Le profil `slides` est un projet *website* (bibliothèques partagées) ; son
  rendu complet nettoie `_rendu/slides/` seulement.
- Quarto ignore les fichiers et dossiers préfixés par `_` (d'où `modules/_exemple/`
  rendu via `decks/modules/exemple/`).
- PDF local sans LuaTeX complet : `uv run quarto render --profile poly -M pdf-engine:xelatex`.
- Maths des slides : MathJax depuis un CDN dans le site ; embarqué dans les decks autonomes.
