"""Schémas de l'organisation du secteur électrique libéralisé.

- `two_circuits` : circuit contractuel (marchés de gros et de détail,
  fournisseurs) et circuit physique (réseaux) en parallèle, entre producteurs
  et consommateurs.
- `market_chain` : la chaîne contractuelle seule, de l'amont à l'aval, avec
  des exemples d'acteurs et des ordres de grandeur.

Usage :

    from pyelec.organisation import new_figure, two_circuits
    fig, ax = new_figure()
    two_circuits(ax)
"""

from collections.abc import Sequence

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

from pyelec.palette import color
from pyelec.schema import (
    ACCENTS,
    CONSUMER,
    TEXT,
    TEXT_LIGHT,
    _building,
    _factory,
    _gas,
    _house,
    _hydro,
    _nuclear,
    _shade,
    _solar,
    _wind,
)

CONTRACT = ACCENTS["production"]  # orange : ce qui relève de la concurrence
CARD_EDGE = "#cbd5e1"

# Couleurs des acteurs dans les barres de parts de marché.
ACTOR_COLORS: dict[str, str] = {
    "edf": ACCENTS["integre"],
    "edf-clair": "#4f7cac",
    "cnr": "#2aa39a",
    "autres": "#94a3b8",
    "alternatifs": CONTRACT,
}


def new_figure(width: float = 10.0, height: float = 5.6) -> tuple[plt.Figure, plt.Axes]:
    """Figure sans marges pour les schémas d'organisation."""
    fig, ax = plt.subplots(figsize=(width, height))
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    return fig, ax


def _box(ax, x0, y0, x1, y1, fc, ec="none", lw=0, r=0.18, z=2):
    ax.add_patch(
        FancyBboxPatch(
            (x0, y0),
            x1 - x0,
            y1 - y0,
            boxstyle=f"round,pad=0,rounding_size={r}",
            fc=fc,
            ec=ec,
            lw=lw,
            zorder=z,
        )
    )


def _arrow(ax, start, end, c, lw=2.5, ls="-", both=False, z=3):
    """Flèche ; en pointillés, le trait est tracé à part et les pointes restent pleines."""
    (x0, y0), (x1, y1) = start, end
    head = 0.22  # longueur de pointe, en unités du schéma
    length = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
    ux, uy = (x1 - x0) / length, (y1 - y0) / length
    if ls == "-":
        ax.add_patch(
            FancyArrowPatch(
                start,
                end,
                arrowstyle="<|-|>" if both else "-|>",
                mutation_scale=16,
                color=c,
                lw=lw,
                shrinkA=2,
                shrinkB=2,
                zorder=z,
            )
        )
        return
    a = (x0 + ux * head, y0 + uy * head) if both else start
    b = (x1 - ux * head, y1 - uy * head)
    ax.plot([a[0], b[0]], [a[1], b[1]], color=c, lw=lw, ls=ls, zorder=z,
            solid_capstyle="butt", dash_capstyle="butt")  # fmt: skip
    tips = [(b, end)] + ([(a, start)] if both else [])
    for base, tip in tips:
        ax.add_patch(
            FancyArrowPatch(
                base,
                tip,
                arrowstyle="-|>",
                mutation_scale=16,
                color=c,
                lw=lw,
                shrinkA=0,
                shrinkB=1,
                zorder=z,
            )
        )


def _title(ax, x, y, text, sub=None, c=TEXT, size=13):
    ax.text(x, y, text, ha="center", va="center", fontsize=size, fontweight="bold", color=c,
            zorder=5)  # fmt: skip
    if sub:
        ax.text(x, y - 0.42, sub, ha="center", va="center", fontsize=10.5, color=c, zorder=5,
                linespacing=1.15)  # fmt: skip


def two_circuits(ax: plt.Axes) -> None:
    """Circuit contractuel et circuit physique, entre producteurs et consommateurs."""
    W, H = 16.0, 9.0
    transport, distribution = ACCENTS["transport"], ACCENTS["distribution"]

    # Couloirs des deux circuits.
    _box(ax, 3.35, 5.0, 12.65, 8.6, _shade(CONTRACT, 0.9), r=0.25, z=0)
    _box(ax, 3.35, 0.4, 12.65, 4.0, _shade(transport, 0.92), r=0.25, z=0)
    ax.text(3.6, 8.3, "FLUX CONTRACTUELS", fontsize=10.5, fontweight="bold",
            color=_shade(CONTRACT, -0.25), va="center")  # fmt: skip
    ax.text(3.6, 7.9, "qui vend à qui, à quel prix", fontsize=10, color=TEXT_LIGHT, va="center")
    ax.text(3.6, 3.7, "FLUX PHYSIQUES", fontsize=10.5, fontweight="bold",
            color=_shade(transport, -0.2), va="center")  # fmt: skip
    ax.text(3.6, 3.3, "l'électricité suit le réseau", fontsize=10, color=TEXT_LIGHT, va="center")

    # Producteurs et consommateurs : présents dans les deux circuits.
    for x0, x1, name in ((0.2, 3.0, "Producteurs"), (13.0, 15.8, "Consommateurs")):
        _box(ax, x0, 0.4, x1, 8.6, "white", ec=CARD_EDGE, lw=1.2, r=0.25, z=1)
        _title(ax, (x0 + x1) / 2, 8.05, name)
    _nuclear(ax, 1.45, 6.7, color("nucleaire"))
    _hydro(ax, 1.75, 5.45, color("hydraulique"))
    _gas(ax, 1.5, 4.05, color("gaz"))
    _wind(ax, 1.6, 2.25, color("eolien"), size=1.05)
    _solar(ax, 1.6, 0.95, color("solaire"), n=3, w=0.38)
    _factory(ax, 13.75, 5.6, CONSUMER)
    _building(ax, 14.4, 3.25, CONSUMER)
    _house(ax, 14.4, 1.2, CONSUMER)

    # Circuit contractuel : marché de gros, fournisseurs, marché de détail.
    yc = 6.45
    for x0, x1, name, sub in (
        (3.9, 6.3, "Marché\nde gros", None),
        (9.7, 12.1, "Marché\nde détail", None),
    ):
        _box(ax, x0, yc - 0.85, x1, yc + 0.85, "white", ec=CONTRACT, lw=2, z=2)
        _title(ax, (x0 + x1) / 2, yc, name, c=_shade(CONTRACT, -0.3))
    for k in (2, 1, 0):  # plusieurs fournisseurs : cartes empilées
        d = 0.14 * k
        _box(ax, 6.9 + d, yc - 0.85 + d, 9.1 + d, yc + 0.85 + d,
             _shade(CONTRACT, 0.15 * k), z=2 - 0.1 * k)  # fmt: skip
    _title(ax, 8.0, yc, "Fournisseurs", c="white")
    for a, b in ((3.0, 3.9), (6.3, 6.9), (9.1, 9.7), (12.1, 13.0)):
        _arrow(ax, (a, yc), (b, yc), _shade(CONTRACT, -0.15), lw=2, ls="--", both=True)

    # Circuit physique : réseaux de transport et de distribution.
    yp = 1.85
    _box(ax, 3.9, yp - 0.85, 7.6, yp + 0.85, transport, z=2)
    _title(ax, 5.75, yp + 0.2, "Réseau de transport", "RTE", c="white")
    _box(ax, 8.4, yp - 0.85, 12.1, yp + 0.85, distribution, z=2)
    _title(ax, 10.25, yp + 0.2, "Réseaux de distribution", "Enedis, entreprises locales",
           c="white")  # fmt: skip
    _arrow(ax, (3.0, yp), (3.9, yp), transport, lw=3.5)
    _arrow(ax, (7.6, yp), (8.4, yp), distribution, lw=3.5)
    _arrow(ax, (12.1, yp), (13.0, yp), distribution, lw=3.5)

    # Régulateur, entre les deux circuits.
    _box(ax, 4.6, 4.15, 11.4, 4.85, TEXT, r=0.3, z=2)
    ax.text(8.0, 4.5, "CRE : régule les réseaux, surveille les marchés", ha="center",
            va="center", fontsize=10, color="white", zorder=5)  # fmt: skip

    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.set_aspect("equal")
    ax.axis("off")


# Chaîne contractuelle : (étape, couleur de fond ; None pour un marché, encadré).
CHAIN_STEPS = [
    ("Producteurs", ACCENTS["integre"]),
    ("Marché de gros", None),
    ("Fournisseurs", CONTRACT),
    ("Marché de détail", None),
    ("Consommateurs", ACCENTS["consommation"]),
]


def market_chain_html() -> str:
    """Chaîne contractuelle en HTML (slides) : mêmes étapes et couleurs que `market_chain`."""
    boxes = []
    for step, fill in CHAIN_STEPS:
        if fill is None:
            style = f"border:3px solid {CONTRACT};color:{_shade(CONTRACT, -0.3)};background:white"
        else:
            style = f"background:{fill};color:white;border:3px solid {fill}"
        boxes.append(f'<div class="chaine-etape" style="{style}">{step}</div>')
    arrow = f'<div class="chaine-fleche" style="color:{TEXT_LIGHT}">→</div>'
    return '<div class="chaine">' + arrow.join(boxes) + "</div>"


def market_chain(ax: plt.Axes) -> None:
    """Chaîne contractuelle, de l'amont à l'aval : cinq étapes reliées par des flèches."""
    W, H = 16.0, 1.6
    steps, fills = zip(*CHAIN_STEPS)
    width, gap = 2.75, 0.55
    x_start = (W - 5 * width - 4 * gap) / 2
    y0, y1 = 0.25, 1.35
    for i, (step, fill) in enumerate(zip(steps, fills)):
        x0 = x_start + i * (width + gap)
        if fill is None:
            _box(ax, x0, y0, x0 + width, y1, "white", ec=CONTRACT, lw=2)
            _title(ax, x0 + width / 2, (y0 + y1) / 2, step, c=_shade(CONTRACT, -0.3), size=12)
        else:
            _box(ax, x0, y0, x0 + width, y1, fill)
            _title(ax, x0 + width / 2, (y0 + y1) / 2, step, c="white", size=12)
        if i < 4:
            _arrow(ax, (x0 + width, (y0 + y1) / 2), (x0 + width + gap, (y0 + y1) / 2),
                   TEXT_LIGHT, lw=2)  # fmt: skip
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.set_aspect("equal")
    ax.axis("off")


def share_bars(
    ax: plt.Axes,
    rows: Sequence[tuple[str, Sequence[tuple[str, float, str]]]],
    groups: Sequence[tuple[int, str, int, int]] = (),
) -> None:
    """Barres horizontales empilées à 100 %, une par ligne.

    `rows` : (titre, segments) ; chaque segment est (libellé, part entre 0 et 1,
    couleur). Le libellé s'inscrit dans le segment s'il est assez large, sinon
    sous la barre. `groups` : accolades au-dessus de segments consécutifs,
    (ligne, libellé, premier segment, dernier segment).
    """
    height, step = 0.8, 1.75
    bounds = {}
    grouped = {g[0] for g in groups}
    for k, (title, segments) in enumerate(rows):
        y = -k * step
        ax.text(0, y + height / 2 + (0.55 if k in grouped else 0.12), title, ha="left", va="bottom", fontsize=12.5,
                fontweight="bold", color=TEXT)  # fmt: skip
        left = 0.0
        for i, (name, share, c) in enumerate(segments):
            ax.barh(y, share, left=left, height=height, color=c, edgecolor="white", linewidth=2)
            bounds[k, i] = (left, left + share)
            pct = f"{share * 100:.0f}\u202f%"
            if share >= 0.06:
                size = 11.5 if share >= 0.15 else 9
                ax.text(left + share / 2, y, f"{name}\n{pct}", ha="center", va="center",
                        fontsize=size, color="white", fontweight="bold", linespacing=1.1)  # fmt: skip
            else:
                ax.text(left + share / 2, y - height / 2 - 0.08, f"{name}\n{pct}", ha="center",
                        va="top", fontsize=10.5, color=TEXT, linespacing=1.1)  # fmt: skip
            left += share
    for k, label, first, last in groups:
        x0, x1 = bounds[k, first][0], bounds[k, last][1]
        yb = -k * step + height / 2 + 0.1
        ax.plot([x0 + 0.003, x0 + 0.003, x1 - 0.003, x1 - 0.003], [yb, yb + 0.12, yb + 0.12, yb],
                color=TEXT_LIGHT, lw=1.2)  # fmt: skip
        ax.text((x0 + x1) / 2, yb + 0.17, label, ha="center", va="bottom", fontsize=11,
                color=TEXT, fontweight="bold")  # fmt: skip
    ax.set_xlim(0, 1)
    ax.set_ylim(-(len(rows) - 1) * step - 0.75, 1.35)
    ax.axis("off")


def market_overview(fig: plt.Figure, rows, groups=()) -> None:
    """Chaîne contractuelle en bandeau, puis barres de parts de marché (`share_bars`)."""
    gs = fig.add_gridspec(2, 1, height_ratios=[1, 3.2], left=0.02, right=0.98, top=0.99,
                          bottom=0.02, hspace=0.05)  # fmt: skip
    market_chain(fig.add_subplot(gs[0]))
    share_bars(fig.add_subplot(gs[1]), rows, groups)
