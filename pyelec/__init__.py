"""Code partagé du cours d'économie de l'électricité.

Utilisé par le poly, les slides et les notebooks : chemins du projet, palette
des filières, style des figures. Les briques de modélisation (merit order,
dispatch, investissement) arriveront avec la migration des modules.
"""

from pyelec.palette import COLORS, LABELS, color, label
from pyelec.paths import DATA_DIR, ROOT

__all__ = ["COLORS", "DATA_DIR", "LABELS", "ROOT", "color", "label"]
