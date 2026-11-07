"""Palette et libellés des filières, communs au poly, aux slides et aux TP.

Source : `notebooks/config.py` du dépôt Cours-EcoElec (TP 01 et 02), plus les
deux couleurs codées en dur dans les graphiques du TP 01 (décharge du stockage,
énergie non distribuée). Toute modification se fait ici et nulle part ailleurs.
"""

COLORS: dict[str, str] = {
    # config.py des TP
    "nucleaire": "#e4a600",
    "hydraulique": "#2772b0",
    "gaz": "#f20808",
    "solaire": "#d66b0e",
    "eolien": "#71cbb7",
    "echanges": "#969696",
    "imports": "#969696",
    "exports": "#969696",
    # graphiques du TP 01
    "stockage": "#ff99cc",
    "END": "#ffff00",
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
