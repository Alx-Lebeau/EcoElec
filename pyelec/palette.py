"""Palette et libellés des filières, communs au poly, aux slides et aux TP.

Teintes de la convention éCO2mix (RTE), familière du public : nucléaire jaune,
hydraulique bleu, gaz rouge, solaire orange, éolien vert d'eau ; adoucies
pour une charte plus moderne (les TP d'origine utilisaient des couleurs
saturées). Toute modification se fait ici et nulle part ailleurs.
"""

COLORS: dict[str, str] = {
    "nucleaire": "#f0b429",
    "hydraulique": "#3b7fc4",
    "gaz": "#d9534f",
    "solaire": "#f28c28",
    "eolien": "#4fb3a9",
    "echanges": "#94a3b8",
    "imports": "#94a3b8",
    "exports": "#94a3b8",
    "charbon-fioul": "#7a6a5f",
    "bioenergies": "#6aa84f",
    "stockage": "#c77dba",
    "END": "#1f2937",
}


# Libellés affichés (légendes, tableaux) ; les identifiants restent sans accents.
LABELS: dict[str, str] = {
    "nucleaire": "Nucléaire",
    "hydraulique": "Hydraulique",
    "gaz": "Gaz",
    "solaire": "Solaire",
    "eolien": "Éolien",
    "echanges": "Échanges",
    "imports": "Imports",
    "exports": "Exports",
    "charbon-fioul": "Charbon et fioul",
    "bioenergies": "Bioénergies",
    "stockage": "Stockage",
    "END": "Énergie non distribuée",
}


def label(tech: str) -> str:
    """Libellé d'une filière (l'identifiant lui-même si aucun libellé n'est défini)."""
    return LABELS.get(tech, tech)


def color(tech: str) -> str:
    """Couleur d'une filière ; erreur explicite si la filière n'a pas de couleur."""
    try:
        return COLORS[tech]
    except KeyError:
        known = ", ".join(sorted(COLORS))
        raise KeyError(
            f"Pas de couleur pour la filière « {tech} ». Filières connues : {known}"
        ) from None


# Secteurs de consommation (mêmes règles : identifiants sans accents).
SECTOR_COLORS: dict[str, str] = {
    "residentiel": "#4f6fd6",
    "tertiaire": "#2aa39a",
    "industrie": "#e0883a",
    "agriculture": "#7cb342",
    "non-affecte": "#a7b0be",
}
SECTOR_LABELS: dict[str, str] = {
    "residentiel": "Résidentiel",
    "tertiaire": "Tertiaire",
    "industrie": "Industrie",
    "agriculture": "Agriculture",
    "non-affecte": "Non affecté",
}
