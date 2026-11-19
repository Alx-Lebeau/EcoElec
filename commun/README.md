# commun/

Éléments partagés par le poly, les slides, les outils et l'accueil : une seule source pour chacun.

| Fichier | Rôle |
|---|---|
| `_macros.qmd` | Notations mathématiques (macros LaTeX). Inclus en tête de chaque chapitre et de chaque deck généré. |
| `biblio.bib` | Bibliographie unique, une entrée par référence avec DOI ou lien. |
| `charte.scss` | Charte : couleurs et polices de tous les rendus (slides, poly, outils, accueil React). Seule source. |
| `polices/` | Source Serif 4 (titres) et Source Sans 3 (texte), licence OFL, déclarées par `polices.css` (option `css` des profils) et par `accueil/src/style.scss`. |
| `site.scss` | Thème HTML du poly et des outils (mode clair), en-tête aligné sur celui de l'accueil. Styles communs des outils OJS : onglets, boutons, champs, police des graphiques Observable Plot. |
| `site-sombre.scss` | Mode sombre du poly. |
| `logo.svg` | Logo de l'en-tête et icône d'onglet de tous les rendus HTML (petit carré bleu de la charte). |
| `slides.scss` | Thème des slides, dont les bandeaux de la vue auteur. |
| `filtres/parties.lua` | Parties d'un module (`## Titre {partie="…"}`) : étiquette au-dessus du titre, barre de progression par partie. |
| `filtres/marques.lua` | Marques `.approfondissement`, `.formel`, `.rappel` des slides. |
| `filtres/formalisation.lua` | Encadrés « Formalisation » du poly. |
| `filtres/typographie.lua` | Espaces insécables de la typographie française. |

## Macros

`_macros.qmd` ne contient que des définitions `\providecommand`, sans commentaire :
tout autre contenu apparaîtrait dans les documents (une slide vide en tête de deck,
par exemple). Pandoc développe ces macros pour tous les formats (HTML, PDF,
reveal.js). `\providecommand` plutôt que `\newcommand`, car le PDF du livre
réunit tous les chapitres et une même macro y serait définie plusieurs fois.

Notations actuelles, reprises des TP 01 et 02 (à compléter au fil de la migration) :

| Macro | Rendu | Sens |
|---|---|---|
| `\Filieres`, `\Temps` | $\mathcal{F}$, $\mathcal{T}$ | ensembles des filières, des pas de temps |
| `\CV`, `\CF` | CV, CF | coût variable (€/MWh), coût fixe annualisé (€/MW/an) |
| `\VOLL`, `\END` | VOLL, END | valeur de l'énergie non distribuée (€/MWh), énergie non distribuée (MW) |
| `\Pmax` | $\overline{P}$ | capacité maximale (MW) |
| `\unite{€/MWh}` | € /MWh | unité dans une formule |

## Mise en page des slides

Classes définies dans `slides.scss`, à utiliser dans les `slides.qmd` :

| Classe | Usage |
|---|---|
| `#| classes: schema-focus` | cellule du schéma `pyelec.schema` recoloré : il reste collé sous le titre, à la même place d'une slide à l'autre |
| `.sous-schema` | texte court sous un schéma ou une figure (taille réduite) |
| `.figure-large` | figure étirée à toute la largeur, hauteur plafonnée |
| `#| classes: figure-colonne` | figure étirée à toute la largeur de sa colonne (graphique à côté d'un texte) |
| `.attention` | mise en garde compacte (icône ⚠) |
| `table.carnet` | carnet d'ordres achat et vente, produit par `pyelec.bourse.order_book_html` (cellule `output: asis`) |
| `.sigles` | cartouche de rappel des sigles, coin supérieur droit (liste, placée en fin de slide) |
| `.a-retenir` | liste numérotée de la slide « À retenir » qui clôt chaque module |
| `.transport`, `.distribution`, `.concurrence` | titre en gras coloré comme `pyelec.schema.ACCENTS` |

Charte (`charte.scss`), registre « note de recherche » : titres en serif
(`$police-titres`) à l'encre (`$encre`), texte en sans (`$police`), un seul bleu
(`$bleu`) réservé aux repères (cours, module, partie, progression, puces) et aux
liens. Le bleu ne reprend aucune couleur des schémas ni des filières : il ne porte
aucun sens. Repères en petites capitales, filets fins à l'encre, pas de coins
arrondis ni d'ombres. Slide de titre sur fond blanc, filet pleine largeur au-dessus
de l'auteur. Pied de page avec le titre du deck (champ `footer` posé par `ecoelec generer`).

Parties : `## Titre {partie="Système physique"}` ouvre une partie, qui vaut pour
les slides suivantes du module ; chaque slide affiche alors l'étiquette de la
partie et une barre découpée en autant de segments que le module a de parties.

Règles automatiques : contenu centré verticalement sous le titre (sauf schéma
`schema-focus`), filet entre colonnes, images en colonnes non déformées.
Les couleurs de `slides.scss` qui reprennent `ACCENTS` doivent rester alignées
avec `pyelec/schema.py`.

## Thèmes

`charte.scss` est une couche de thème Quarto (variables seulement), listée en
**dernier** : Quarto empile les couches `scss:defaults` en ordre inverse, la charte
est donc déclarée avant les fichiers qui utilisent ses variables. La lister en
premier fait échouer la compilation (« Undefined variable »). Un `@import` fonctionne
mais produit des avertissements « variable used before declaration ».

| Rendu | `theme` |
|---|---|
| slides | `[default, commun/slides.scss, commun/charte.scss]` |
| poly (clair) | `[cosmo, commun/site.scss, commun/charte.scss]` |
| poly (sombre) | `[cosmo, commun/site.scss, commun/site-sombre.scss, commun/charte.scss]` |
| outils | `[cosmo, commun/site.scss, commun/charte.scss]` (clair seulement) |

`site.scss` donne ses valeurs avec `!default`, que `site-sombre.scss` redéfinit.
L'accueil React lit la même charte (`@use` dans `accueil/src/style.scss`).

Mode sombre : le poly le propose (bouton de l'en-tête), comme l'accueil. Les deux
mémorisent le choix sous la même clé (`quarto-color-scheme` dans `localStorage`,
valeurs de Quarto : `alternate` pour sombre, `default` pour clair), qui vaut donc pour
tout le site. Les outils restent en mode clair : les couleurs de leurs graphiques
(Observable Plot) et de leurs tableaux sont écrites pour un fond clair.

En-tête : la barre de navigation du poly et des outils (`_quarto-poly.yml`,
`_quarto-outils.yml`) et l'en-tête de l'accueil (`accueil/src/App.jsx`) ont les
mêmes entrées (Parcours, Modules, Outils, Poly) : les modifier ensemble.

## Polices

Fichiers variables du dépôt google/fonts (`ofl/sourceserif4/SourceSerif4[opsz,wght].ttf`,
`ofl/sourcesans3/SourceSans3[wght].ttf` et son italique), réduits pour garder le
latin, les indices et exposants (CO₂), le grec, les flèches et les opérateurs :

```sh
uvx --from 'fonttools[woff]' pyftsubset SourceSans3[wght].ttf --flavor=woff2 \
  --layout-features='*' --output-file=commun/polices/source-sans-3.woff2 \
  --unicodes="U+0000-00FF,U+0131,U+0152-0153,U+0178,U+02C6,U+02DA,U+02DC,U+0300-0308,U+0391-03C9,U+2000-206F,U+2070-209F,U+20AC,U+2122,U+2190-2199,U+2200-22FF,U+FEFF,U+FFFD"
```

Les figures matplotlib et le PDF du poly gardent leurs polices propres.
