# Économie de l'électricité

Cours modulaire d'économie de l'électricité : marchés, formation des prix,
investissement, régulation. Un seul projet [Quarto](https://quarto.org) produit :

- un **poly** (livre, en HTML et en PDF) ;
- des **slides** (reveal.js), un deck par séance, aussi disponibles en HTML
  autonome (utilisable hors connexion) et en PDF ;
- les **TP** et exemples de code (notebooks Jupyter, module Python `pyelec`).

> Dépôt en cours de construction : la refonte du cours est en cours, la plupart
> des modules sont encore des ébauches.

## Principe

Le cours est une **banque de modules**. Chaque format (3h, 6h, 12h) ou session
réelle y pioche au moyen d'un **parcours**. Chaque module existe en quatre
versions tirées d'une seule source :

|              | intuitif | formel |
|--------------|----------|--------|
| **essentiel** (≈ 30 min) | graphiques, raisonnements, ordres de grandeur | + formulation mathématique |
| **complet** (≈ 1h30)     | + approfondissements | + approfondissements et démonstrations |

Le poly, lui, est unique et complet : chaque parcours renvoie aux chapitres utiles.

## Arborescence

```
_quarto.yml            configuration commune
_quarto-poly.yml       profil « poly » (livre)
_quarto-slides.yml     profil « slides » (decks générés)
_quarto-autonome.yml   profil « autonome » (decks en un seul fichier HTML)
commun/                macros, bibliographie, thèmes, filtres Lua
modules/<id>/          module.yml, poly.qmd (chapitre), slides.qmd (slides marquées), tp/
modules/_exemple/      module de démonstration des marques, qui sert aussi de test
parcours/              un fichier .yml par format ou par session
pyelec/                code partagé (palette, style des figures, chemins…)
outils/                commande `ecoelec` : vérification des parcours, génération des decks
data/                  petits jeux de données ouverts et scripts de téléchargement
tests/                 tests de l'outillage
decks/                 decks générés par `ecoelec generer` (non versionnés)
_freeze/               résultats de calcul en cache (non versionnés)
```

## Installation

Prérequis : [uv](https://docs.astral.sh/uv/), [Quarto](https://quarto.org/docs/get-started/)
(version figée dans la CI), une distribution TeX pour le PDF du poly
(`quarto install tinytex`) et Chrome ou Chromium pour le PDF des decks.

```sh
uv sync
```

## Utilisation

```sh
# Vérifier les modules et les parcours, puis générer les decks dans decks/
uv run ecoelec generer

# Poly (HTML + PDF) → _rendu/poly/
uv run quarto render --profile poly

# Slides : decks des parcours, quatre versions et vue auteur de chaque module → _rendu/slides/
uv run quarto render --profile slides

# Decks des parcours en HTML autonome → _rendu/autonome/
uv run quarto render decks/parcours --profile slides,autonome --output-dir _rendu/autonome

# PDF des decks autonomes (decktape, Chrome ou Chromium)
uv run ecoelec pdf

# Créer un module à partir du modèle
uv run ecoelec nouveau-module mon-module
```

Pour travailler un module, la **vue auteur** (`_rendu/slides/decks/modules/<id>/auteur.html`)
affiche tout le contenu, chaque marque signalée par un bandeau de couleur.

## Marques

Tout contenu non marqué apparaît dans toutes les versions.

| Marque | Visible dans |
|---|---|
| `.approfondissement` | la version complète seulement |
| `.formel` | la version formelle seulement |
| `.intuitif` | la version intuitive seulement |
| `.rappel` | les parcours où un module prérequis ne précède pas ce module |

Une marque s'applique à une slide entière (`## Titre {.formel}`) ou à un bloc
(`::: {.formel}` … `:::`). Règle d'or : un contenu non marqué ne s'appuie jamais
sur un contenu marqué. Détails dans [`CLAUDE.md`](CLAUDE.md).

## Licences

- Contenu (textes, slides, figures, données produites pour le cours) :
  [CC BY-SA 4.0](LICENSES/CC-BY-SA-4.0.txt).
- Code (`pyelec/`, `outils/`, `commun/filtres/`, cellules de code des documents et notebooks) :
  [MIT](LICENSES/MIT.txt).
- Données tierces : licence propre à chaque jeu, indiquée dans [`data/README.md`](data/README.md).
