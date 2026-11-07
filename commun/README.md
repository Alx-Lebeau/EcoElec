# commun/

Éléments partagés par le poly et les slides : une seule source pour chacun.

| Fichier | Rôle |
|---|---|
| `_macros.qmd` | Notations mathématiques (macros LaTeX). Inclus en tête de chaque chapitre et de chaque deck généré. |
| `biblio.bib` | Bibliographie unique, une entrée par référence avec DOI ou lien. |
| `poly.scss` | Thème HTML du poly. |
| `slides.scss` | Thème des slides, dont les bandeaux de la vue auteur. |
| `filtres/marques.lua` | Marques `.approfondissement`, `.formel`, `.intuitif`, `.rappel` des slides. |
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
