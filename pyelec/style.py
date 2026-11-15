"""Style commun des figures.

Usage dans un chapitre ou un deck :

    from pyelec import style
    style.use()
    fig, ax = plt.subplots()
    ...
    style.add_source(fig, "éCO2mix (RTE)", "2025")

Règle du cours : source et date sous chaque figure.
"""

import matplotlib as mpl
import matplotlib.pyplot as plt

# Taille et résolution des figures : laissées à Quarto (fig-width, fig-height, fig-dpi).
RC_PARAMS = {
    # Même famille que le thème des slides ; repli sur DejaVu Sans si absente.
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
    "font.size": 12,
    "axes.titlesize": 13,
    "axes.titleweight": "bold",
    "axes.titlelocation": "left",
    "axes.labelsize": 12,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "legend.frameon": False,
}


def use() -> None:
    """Applique le style commun à matplotlib."""
    mpl.rcParams.update(RC_PARAMS)


def add_source(fig: plt.Figure, source: str, date: str) -> None:
    """Ajoute la mention « Source : …, date » en bas à gauche de la figure."""
    fig.text(
        0.0,
        -0.02,
        f"Source : {source}, {date}",
        ha="left",
        va="top",
        fontsize=9,
        color="0.4",
        transform=fig.transFigure,
    )
