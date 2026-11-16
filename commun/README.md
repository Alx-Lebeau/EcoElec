# commun/

Éléments partagés par le poly et les slides : une seule source pour chacun.

| Fichier | Rôle |
|---|---|
| `_macros.qmd` | Notations mathématiques (macros LaTeX). Inclus en tête de chaque chapitre et de chaque deck généré. |
| `biblio.bib` | Bibliographie unique, une entrée par référence avec DOI ou lien. |
| `poly.scss` | Thème HTML du poly. |
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
| `.a-retenir` | liste numérotée de la slide « À retenir » qui clôt chaque module |
| `.transport`, `.distribution`, `.concurrence` | titre en gras coloré comme `pyelec.schema.ACCENTS` |

Charte : bleu nuit (`$nuit`), bleu des titres, accent cyan (`$accent`) réservé à
l'habillage (filets sous les titres, étiquettes de partie, progression). L'accent
ne reprend aucune couleur des schémas ni des filières : il ne porte aucun sens.
Slide de titre sur fond bleu nuit avec un réseau en filigrane ; pied de page avec
le titre du deck (champ `footer` posé par `ecoelec generer`).

Parties : `## Titre {partie="Système physique"}` ouvre une partie, qui vaut pour
les slides suivantes du module ; chaque slide affiche alors l'étiquette de la
partie et une barre découpée en autant de segments que le module a de parties.

Règles automatiques : contenu centré verticalement sous le titre (sauf schéma
`schema-focus`), filet entre colonnes, images en colonnes non déformées.
Les couleurs de `slides.scss` qui reprennent `ACCENTS` doivent rester alignées
avec `pyelec/schema.py`.
