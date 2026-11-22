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

from pyelec.paths import ROOT

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


# Police des slides (commun/charte.scss : $police), en TTF statiques : matplotlib
# ne lit ni le WOFF2 ni les axes d'une police variable (commun/README.md, Polices).
SLIDES_FONTS = ("source-sans-3-regular.ttf", "source-sans-3-gras.ttf")


def use_svg() -> None:
    """Figures des notebooks en SVG, texte en Source Sans 3 (slides).

    Vectoriel : net à toute taille de projection et dans les PDF. Le texte est
    vectorisé (`svg.fonttype: path`) : une image SVG n'a pas accès aux polices de
    la page, la police du deck s'affiche ainsi partout, même hors connexion.
    """
    from matplotlib import font_manager
    from matplotlib_inline.backend_inline import set_matplotlib_formats

    for name in SLIDES_FONTS:
        font_manager.fontManager.addfont(ROOT / "commun" / "polices" / name)
    mpl.rcParams["font.sans-serif"] = ["Source Sans 3", *RC_PARAMS["font.sans-serif"]]
    mpl.rcParams["svg.fonttype"] = "path"
    set_matplotlib_formats("svg")
