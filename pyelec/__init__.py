"""Code partagé du cours d'économie de l'électricité.

Utilisé par le poly, les slides et les notebooks :

- `paths`, `palette`, `style` : chemins du projet, couleurs et libellés, style des figures ;
- `figures` : figures de données (merit order, mix, consommation) ;
- `schema` : schéma du système électrique, recoloré par groupes d'éléments ;
- `organisation` : flux physiques et contractuels, chaîne amont-aval, parts de marché ;
- `lois` : équilibre injections-soutirages et répartition des flux (Kirchhoff).
- `economie` : graphiques conceptuels (coûts, utilité, équilibre, surplus).
- `dispatch` : court terme d'un parc illustratif (coûts variables, merit order,
  prix, surplus, VOLL).

Les briques de modélisation (dispatch, investissement) arriveront avec la
migration des modules.
"""

from pyelec.palette import COLORS, LABELS, color, label
from pyelec.paths import DATA_DIR, ROOT

__all__ = ["COLORS", "DATA_DIR", "LABELS", "ROOT", "color", "label"]
