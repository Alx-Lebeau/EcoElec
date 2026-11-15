"""Schéma simplifié d'un système électrique, réutilisé d'une slide à l'autre.

Le même schéma sert à décrire la physique (niveaux de tension, transport maillé,
distribution arborescente, production centralisée et décentralisée) puis à
montrer qui fait quoi selon l'organisation du secteur : on le recolore en
mettant en évidence des groupes d'éléments.

Usage :

    from pyelec.schema import grid_diagram, new_figure
    fig, ax = new_figure()
    grid_diagram(ax)                                      # couleurs d'origine
    grid_diagram(ax, labels=True)                         # niveaux et noms des éléments
    grid_diagram(ax, highlight={"transport": ACCENTS["transport"]})  # reste estompé

Chaque élément porte des étiquettes (voir `TAGS`) : `highlight` associe une
étiquette ou un identifiant d'élément à une couleur, ou à `None` pour garder
la couleur d'origine. Les éléments non retenus sont estompés.
"""

import itertools
import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyBboxPatch, Polygon, Rectangle

from pyelec.palette import color

# Étiquettes disponibles pour `highlight`.
TAGS: dict[str, str] = {
    "production": "moyens de production (centralisés et décentralisés)",
    "production-centralisee": "grandes centrales raccordées au réseau de transport",
    "production-decentralisee": "production raccordée au réseau de distribution",
    "consommation": "tous les consommateurs",
    "transport": "réseau de transport : lignes THT et HTB, postes THT/HTB",
    "distribution": "réseau de distribution : postes sources, lignes HTA et BT",
    "interconnexion": "liaison avec le pays voisin",
    "lignes": "toutes les lignes",
    "postes": "tous les transformateurs",
}

# Teintes du schéma (indépendantes des filières, qui viennent de la palette).
TEXT = "#334155"
TEXT_LIGHT = "#64748b"
CONSUMER = "#475569"
FADED = "#dfe4ea"

# Couleurs de mise en évidence (transport, distribution, acteurs…).
ACCENTS: dict[str, str] = {
    "transport": "#1d4ed8",
    "distribution": "#0f9d76",
    "production": "#e07a1f",
    "consommation": "#7c3aed",
    "integre": "#1f4e79",
}
BAND = "#f4f6f9"

# Niveaux de tension : (clé, nom, tension, y bas, y haut, couleur des lignes,
# épaisseur). Repère [XMIN, XMAX] × [0, HEIGHT] ; la colonne x < 0 est
# réservée aux noms des niveaux.
XMIN, XMAX, HEIGHT = -2.6, 17.2, 10.0
WIDTH = XMAX - XMIN
LEVELS = [
    ("THT", "Très haute tension", "400 kV", 7.2, 10.0, "#1e293b", 3.4),
    ("HTB", "Haute tension", "63 à 225 kV", 5.0, 7.2, "#335c8a", 2.6),
    ("HTA", "Moyenne tension", "20 kV", 2.6, 5.0, "#5b8fc7", 2.0),
    ("BT", "Basse tension", "230/400 V", 0.0, 2.6, "#93b8e0", 1.6),
]
LINE = {key: (c, lw) for key, *_, c, lw in LEVELS}

# Nœuds (jeux de barres) : identifiant → (x, y).
NODES: dict[str, tuple[float, float]] = {
    # THT : réseau maillé
    "A": (4.4, 7.9),
    "B": (7.8, 9.0),
    "C": (11.2, 7.9),
    "D": (13.4, 9.0),
    # HTB
    "E": (4.4, 6.0),
    "F": (7.8, 6.0),
    "G": (11.2, 6.0),
    # HTA : réseau arborescent
    "H": (7.8, 3.9),
    "I": (10.2, 3.9),
    "J": (12.4, 3.9),
    # BT : réseau arborescent
    "K": (10.2, 2.15),
}


@dataclass
class _Ctx:
    """Résout la couleur d'un élément selon `highlight`."""

    highlight: Mapping[str, str | None] | None

    def color(self, default: str, element_id: str, tags: Iterable[str]) -> str:
        if self.highlight is None:
            return default
        for key in (element_id, *tags):
            if key in self.highlight:
                chosen = self.highlight[key]
                return default if chosen is None else chosen
        return FADED


def _shade(hex_color: str, factor: float) -> str:
    """Éclaircit (factor > 0) ou fonce (factor < 0) une couleur."""
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (1, 3, 5))
    if factor >= 0:
        r, g, b = (round(v + (255 - v) * factor) for v in (r, g, b))
    else:
        r, g, b = (round(v * (1 + factor)) for v in (r, g, b))
    return f"#{r:02x}{g:02x}{b:02x}"


# --- Pictogrammes -----------------------------------------------------------
# Style plat : aplats sans contour, angles arrondis, une teinte plus claire ou
# plus foncée pour le relief. Chaque pictogramme est posé sur son point de
# raccordement (x, y).


def _rounded(ax, x, y, w, h, c, r=0.06, z=4):
    ax.add_patch(
        FancyBboxPatch(
            (x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}", fc=c, ec="none", zorder=z
        )
    )


def _nuclear(ax, x, y, c):
    # Tour de refroidissement (profil hyperbolique) et bâtiment réacteur.
    h, waist, top, cx = 0.95, 0.24, 0.62, x - 0.25
    right = []
    for i in range(21):
        t = i / 20
        half = waist * math.sqrt(1 + ((t - top) / 0.42) ** 2)
        right.append((cx + half, y + t * h))
    left = [(2 * cx - px, py) for px, py in reversed(right)]
    ax.add_patch(Polygon(right + left, closed=True, fc=c, ec="none", zorder=4))
    _rounded(ax, x + 0.18, y, 0.5, 0.36, _shade(c, -0.12), r=0.04)
    ax.add_patch(Circle((x + 0.43, y + 0.36), 0.25, fc=_shade(c, -0.12), ec="none", zorder=3.9))


def _drop(ax, x, y, r, c, z=4.3):
    """Goutte (ou flamme) : cercle de rayon r centré en (x, y), pointe vers le haut."""
    pts = []
    for i in range(41):
        t = math.pi * i / 40  # demi-tour du côté droit, du bas vers le haut
        a = -math.pi / 2 + t
        px, py = r * math.cos(a), r * math.sin(a)
        if py > 0:  # au-dessus du centre : on resserre vers la pointe
            k = py / r
            px *= (1 - k) ** 0.9
            py = r * (k * 1.9)
        pts.append((x + px, y + py))
    left = [(2 * x - px, py) for px, py in reversed(pts)]
    ax.add_patch(Polygon(pts + left, closed=True, fc=c, ec="none", zorder=z))


def _hydro(ax, x, y, c):
    # Retenue (surface ondulée), barrage, usine en pied, goutte d'eau.
    water = _shade(c, 0.55)
    x0, x1, top = x - 0.95, x - 0.14, y + 0.6
    surface = [
        (x0 + (x1 - x0) * i / 40, top + 0.045 * math.sin(2 * math.pi * 2.5 * i / 40))
        for i in range(41)
    ]
    ax.add_patch(
        Polygon(
            [(x0, y + 0.12), *surface, (x1, y + 0.12)], closed=True, fc=water, ec="none", zorder=3.9
        )
    )
    for k, dy in enumerate((0.2, 0.36)):
        xs = [x0 + 0.12 + 0.55 * i / 30 + 0.08 * k for i in range(31)]
        ys = [y + dy + 0.03 * math.sin(2 * math.pi * 2 * i / 30) for i in range(31)]
        ax.plot(xs, ys, color="white", lw=1.2, alpha=0.9, zorder=3.95, solid_capstyle="round")
    ax.add_patch(
        Polygon(
            [(x - 0.18, y), (x - 0.18, y + 0.78), (x, y + 0.78), (x + 0.3, y)],
            closed=True,
            fc=c,
            ec="none",
            zorder=4,
        )
    )
    _rounded(ax, x + 0.32, y, 0.42, 0.28, _shade(c, -0.2), r=0.04)


def _gas(ax, x, y, c):
    # Centrale thermique : bâtiment marqué d'une flamme, deux cheminées.
    _rounded(ax, x - 0.55, y, 0.8, 0.5, c)
    for dx, h in ((0.3, 0.9), (0.5, 0.75)):
        _rounded(ax, x + dx, y, 0.14, h, _shade(c, -0.15), r=0.03)
    _drop(ax, x - 0.15, y + 0.17, 0.12, "white", z=4.2)
    _drop(ax, x - 0.15, y + 0.13, 0.06, _shade(c, 0.35), z=4.3)


def _pylon(ax, x, y_base, y_line, c):
    """Pylône à treillis sous la ligne, qui repose sur deux isolateurs."""
    top = y_line - 0.16
    half = lambda yy: 0.22 - 0.14 * (yy - y_base) / (top - y_base)
    kw = {"color": c, "zorder": 2.9, "solid_capstyle": "round"}
    for sign in (-1, 1):
        ax.plot([x + sign * half(y_base), x + sign * half(top)], [y_base, top], lw=1.5, **kw)
    levels = [y_base + (top - y_base) * k / 3 for k in range(4)]
    for y0, y1 in itertools.pairwise(levels):
        ax.plot([x - half(y0), x + half(y1)], [y0, y1], lw=0.8, **kw)
        ax.plot([x + half(y0), x - half(y1)], [y0, y1], lw=0.8, **kw)
    ax.plot([x - 0.42, x + 0.42], [top, top], lw=1.6, **kw)
    for dx in (-0.34, 0.34):
        ax.plot([x + dx, x + dx], [top, y_line], lw=1.6, **kw)


def _wind(ax, x, y, c, size=1.0):
    # Mât effilé, trois pales fines, moyeu.
    top = y + 0.95 * size
    ax.add_patch(
        Polygon(
            [(x - 0.05 * size, y), (x + 0.05 * size, y), (x + 0.02, top), (x - 0.02, top)],
            closed=True,
            fc=_shade(c, -0.25),
            ec="none",
            zorder=4,
        )
    )
    for angle in (105, 225, 345):
        a = math.radians(angle)
        tip = (x + 0.48 * size * math.cos(a), top + 0.48 * size * math.sin(a))
        nx, ny = -math.sin(a) * 0.045 * size, math.cos(a) * 0.045 * size
        ax.add_patch(
            Polygon(
                [(x + nx, top + ny), tip, (x - nx, top - ny)],
                closed=True,
                fc=c,
                ec="none",
                zorder=4.1,
            )
        )
    ax.add_patch(Circle((x, top), 0.06 * size, fc="white", ec=_shade(c, -0.25), lw=1, zorder=4.2))


def _solar(ax, x, y, c, n=3, w=0.34):
    # Rangées de panneaux inclinés.
    for i in range(n):
        x0 = x - n * (w + 0.08) / 2 + i * (w + 0.08)
        ax.plot([x0 + w / 2] * 2, [y, y + 0.16], color=_shade(c, -0.3), lw=1, zorder=3.9)
        ax.add_patch(
            Polygon(
                [
                    (x0, y + 0.16),
                    (x0 + w, y + 0.16),
                    (x0 + w + 0.1, y + 0.44),
                    (x0 + 0.1, y + 0.44),
                ],
                closed=True,
                fc=c,
                ec="white",
                lw=0.8,
                zorder=4,
            )
        )


def _factory(ax, x, y, c):
    # Usine : toit en dents de scie, cheminée, fenêtres.
    pts = [(x, y), (x, y + 0.5)]
    for i in range(3):
        pts += [(x + i * 0.4, y + 0.5), (x + (i + 1) * 0.4, y + 0.78), (x + (i + 1) * 0.4, y + 0.5)]
    pts += [(x + 1.2, y)]
    ax.add_patch(Polygon(pts, closed=True, fc=c, ec="none", zorder=4))
    _rounded(ax, x + 1.25, y, 0.16, 1.0, _shade(c, -0.15), r=0.03)
    for i in range(3):
        _rounded(ax, x + 0.12 + i * 0.36, y + 0.14, 0.2, 0.18, _shade(c, 0.55), r=0.02, z=4.1)


def _building(ax, x, y, c):
    # Immeuble de bureaux, commerce, PME.
    _rounded(ax, x - 0.33, y, 0.66, 0.95, c, r=0.05)
    for i in range(3):
        for j in range(2):
            _rounded(
                ax,
                x - 0.21 + j * 0.25,
                y + 0.2 + i * 0.24,
                0.17,
                0.13,
                _shade(c, 0.6),
                r=0.02,
                z=4.1,
            )


def _house(ax, x, y, c, pv_color=None):
    _rounded(ax, x - 0.28, y, 0.56, 0.42, c, r=0.03)
    ax.add_patch(
        Polygon(
            [(x - 0.38, y + 0.4), (x, y + 0.75), (x + 0.38, y + 0.4)],
            closed=True,
            fc=_shade(c, -0.2),
            ec="none",
            zorder=4,
        )
    )
    _rounded(ax, x - 0.07, y, 0.14, 0.22, _shade(c, 0.6), r=0.02, z=4.1)
    if pv_color is not None:
        ax.add_patch(
            Polygon(
                [(x + 0.04, y + 0.47), (x + 0.3, y + 0.47), (x + 0.1, y + 0.66), (x, y + 0.66)],
                closed=True,
                fc=pv_color,
                ec="white",
                lw=0.6,
                zorder=4.2,
            )
        )


def _transformer(ax, x, y, c_top, c_bottom, r=0.17):
    # Symbole normalisé : deux enroulements, chacun de la couleur de sa tension.
    for dy in (r * 0.6, -r * 0.6):
        ax.add_patch(Circle((x, y + dy), r, fc="white", ec="none", zorder=5))
    for dy, c in ((r * 0.6, c_top), (-r * 0.6, c_bottom)):
        ax.add_patch(Circle((x, y + dy), r, fc="none", ec=c, lw=2, zorder=5.1))


def _busbar(ax, x, y, c, half=0.3):
    _rounded(ax, x - half, y - 0.055, 2 * half, 0.11, c, r=0.05, z=4.5)


# --- Schéma -----------------------------------------------------------------


def new_figure(width: float = 10.0) -> tuple[plt.Figure, plt.Axes]:
    """Figure aux proportions du schéma, sans marges."""
    fig, ax = plt.subplots(figsize=(width, width * HEIGHT / WIDTH))
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    return fig, ax


def grid_diagram(
    ax: plt.Axes,
    *,
    labels: bool = False,
    levels: bool = True,
    highlight: Mapping[str, str | None] | None = None,
) -> None:
    """Dessine le schéma du système électrique dans `ax`.

    `labels` : noms des niveaux de tension et des éléments.
    `levels` : bandes de fond des niveaux de tension.
    `highlight` : étiquette (voir `TAGS`) ou identifiant d'élément → couleur
    (`None` : couleur d'origine) ; les autres éléments sont estompés.
    """
    ctx = _Ctx(highlight)
    n = NODES
    T = ("transport",)
    D = ("distribution",)
    PC = ("production", "production-centralisee")
    PD = ("production", "production-decentralisee")
    CO = ("consommation",)

    def wire(eid, tags, kind, *pts):
        """Ligne passant par des nœuds (identifiants) ou des points (x, y)."""
        xs, ys = zip(*(n[p] if isinstance(p, str) else p for p in pts))
        c, lw = LINE[kind]
        ax.plot(
            xs,
            ys,
            color=ctx.color(c, eid, (*tags, "lignes")),
            lw=lw,
            solid_capstyle="round",
            solid_joinstyle="round",
            zorder=3,
        )

    def bus(tags, kind, *nodes):
        for node in nodes:
            _busbar(ax, *n[node], ctx.color(LINE[kind][0], f"noeud-{node}", tags))

    def transfo(eid, tags, top, bottom, kinds):
        (x, y0), (_, y1) = n[top], n[bottom]
        c0 = ctx.color(LINE[kinds[0]][0], eid, (*tags, "postes"))
        c1 = ctx.color(LINE[kinds[1]][0], eid, (*tags, "postes"))
        ym = (y0 + y1) / 2
        ax.plot([x, x], [y0, ym], color=c0, lw=1.8, zorder=3)
        ax.plot([x, x], [ym, y1], color=c1, lw=1.8, zorder=3)
        _transformer(ax, x, ym, c0, c1)

    def picto(eid, tags, fn, x, y, default, **kw):
        fn(ax, x, y, ctx.color(default, eid, tags), **kw)

    def text(x, y, s, **kw):
        if labels:
            ax.text(x, y, s, fontsize=12, color=TEXT, zorder=6, **kw)

    # Bandes des niveaux de tension et colonne des noms.
    if levels:
        for i, (_, name, voltage, y0, y1, c, _) in enumerate(LEVELS):
            if i % 2 == 0:
                ax.add_patch(Rectangle((XMIN, y0), WIDTH, y1 - y0, fc=BAND, ec="none", zorder=0))
            if labels:
                ym = (y0 + y1) / 2
                ax.plot(
                    [XMIN + 0.25, XMIN + 0.25],
                    [ym - 0.35, ym + 0.35],
                    color=c,
                    lw=4,
                    solid_capstyle="round",
                    zorder=1,
                )
                ax.text(XMIN + 0.5, ym + 0.06, name, ha="left", va="bottom", fontsize=12.5,
                        fontweight="bold", color=TEXT, zorder=1)  # fmt: skip
                ax.text(XMIN + 0.5, ym - 0.06, voltage, ha="left", va="top", fontsize=11.5,
                        color=TEXT_LIGHT, zorder=1)  # fmt: skip

    # Transport THT : maillé, interconnecté avec le pays voisin.
    for a, b in [("A", "B"), ("B", "C"), ("A", "C"), ("C", "D"), ("B", "D")]:
        wire(f"ligne-{a}{b}", T, "THT", a, b)
    # Interconnexion : ligne portée par un pylône jusqu'au réseau du pays voisin,
    # esquissé en teinte claire au-delà de la frontière.
    yc = n["C"][1]
    yi = yc + 0.45  # la ligne remonte pour laisser la place au pylône
    wire("interconnexion", ("interconnexion", "transport"), "THT", "C", (13.0, yc), (13.45, yi),
         (16.1, yi))  # fmt: skip
    _pylon(ax, 14.6, 7.3, yi, ctx.color(LINE["THT"][0], "pylone", ("interconnexion", "transport")))
    abroad = "#b8c4d4"
    for pts in ([(16.1, yi), (XMAX, yi)], [(16.1, yi), (XMAX, 9.2)], [(16.1, yi), (XMAX, 7.5)]):
        xs, ys = zip(*pts)
        ax.plot(xs, ys, color=abroad, lw=LINE["THT"][1], solid_capstyle="round", zorder=2)
    _busbar(ax, 16.1, yi, abroad)
    ax.plot([15.4, 15.4], [7.2, HEIGHT], color=TEXT_LIGHT, lw=1, ls=(0, (2, 3)), zorder=1)
    bus(T, "THT", "A", "B", "C", "D")
    text(16.3, 9.45, "pays\nvoisin", ha="center", va="center", linespacing=1.1)

    # Postes THT/HTB et transport HTB.
    transfo("poste-A-E", T, "A", "E", ("THT", "HTB"))
    transfo("poste-C-G", T, "C", "G", ("THT", "HTB"))
    wire("ligne-EG", T, "HTB", "E", "G")
    bus(T, "HTB", "E", "F", "G")

    # Poste source HTB/HTA et distribution HTA : arborescente.
    transfo("poste-source", D, "F", "H", ("HTB", "HTA"))
    wire("ligne-HTA", D, "HTA", (4.6, 3.9), "H", "I", "J", (13.95, 3.9))
    wire("ligne-HTA", D, "HTA", "J", (12.4, 3.2), (13.1, 3.2))
    bus(D, "HTA", "H")

    # Poste de distribution HTA/BT et distribution BT : arborescente.
    transfo("poste-distribution", D, "I", "K", ("HTA", "BT"))
    houses_x = [8.0, 9.1, 10.2, 11.3, 12.4]
    wire("ligne-BT", D, "BT", "K", (10.2, 1.65))
    wire("ligne-BT", D, "BT", (houses_x[0], 1.65), (houses_x[-1], 1.65))
    bus(D, "BT", "K")

    # Production centralisée, raccordée au réseau de transport.
    picto("nucleaire", PC, _nuclear, 2.75, 7.9, color("nucleaire"))
    wire("raccord-nucleaire", T, "THT", (3.4, 7.9), "A")
    text(2.75, 7.75, "centrale nucléaire", ha="center", va="top")
    picto("hydraulique", PC, _hydro, 6.2, 9.0, color("hydraulique"))
    wire("raccord-hydraulique", T, "THT", (6.9, 9.0), "B")
    text(5.1, 9.35, "barrage", ha="right", va="center")
    picto("gaz", PC, _gas, 14.3, 9.0, color("gaz"))
    wire("raccord-gaz", T, "THT", "D", (13.8, 9.0))
    text(13.2, 9.15, "cycle combiné gaz", ha="right", va="bottom")

    # Grand consommateur industriel, raccordé en HTB.
    wire("raccord-industrie", T, "HTB", "G", (12.6, 6.0))
    picto("industrie", CO, _factory, 12.6, 5.75, CONSUMER)
    text(13.3, 5.6, "industrie", ha="center", va="top")

    # Production décentralisée, raccordée au réseau de distribution.
    for i, (x, size) in enumerate([(5.0, 0.95), (5.9, 0.8), (6.8, 0.9)]):
        picto(f"eolien-{i}", PD, _wind, x, 3.9, color("eolien"), size=size)
    text(5.9, 3.7, "parc éolien", ha="center", va="top")
    picto("solaire", PD, _solar, 13.6, 3.2, color("solaire"))
    text(14.5, 3.45, "centrale\nsolaire", ha="left", va="center", linespacing=1.1)

    # Tertiaire, PME : raccordé en HTA.
    picto("tertiaire", CO, _building, 13.95, 3.9, CONSUMER)
    text(14.4, 4.4, "tertiaire,\nPME", ha="left", va="center", linespacing=1.1)

    # Ménages, raccordés en BT ; l'un d'eux produit (solaire en toiture).
    for i, x in enumerate(houses_x):
        wire("ligne-BT", D, "BT", (x, 1.65), (x, 1.4))
        pv = ctx.color(color("solaire"), "solaire-toiture", PD) if i == 3 else None
        picto(f"menage-{i}", CO, _house, x, 0.65, CONSUMER, pv_color=pv)
    text(10.2, 0.5, "ménages, dont autoproducteurs", ha="center", va="top")

    # Postes.
    text(n["F"][0] + 0.3, 4.95, "poste source", ha="left", va="center")
    text(n["I"][0] + 0.3, 3.02, "poste de distribution", ha="left", va="center")

    ax.set_xlim(XMIN, XMAX)
    ax.set_ylim(0, HEIGHT)
    ax.set_aspect("equal")
    ax.axis("off")
