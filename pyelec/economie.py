"""Graphiques conceptuels de l'analyse économique : coûts, utilité, optimum, surplus.

Schémas de principe sans données : courbes stylisées, axes sans graduations,
donc sans mention de source. Les mêmes courbes servent d'une slide à l'autre
(l'optimum, le surplus social, puis l'équilibre de marché), pour que le public
retrouve le même graphique. L'option `voll` remplace l'utilité marginale
générique par sa forme électrique : VOLL pour les usages non flexibles, puis
décroissance forte.

- `fixed_and_variable_costs` : coût total d'une centrale selon sa production
- `short_run_marginal_cost` : coût marginal de court terme, continu et croissant
- `marginal_cost_zoom` : le même coût marginal vu de loin (continu) et de près (paliers)
- `merit_order_steps` : coût marginal en paliers d'un parc stylisé, par filière
- `long_run_marginal_cost` : coût marginal de long terme selon la durée de la
  hausse de demande
- `marginal_utility` : utilité marginale et utilité totale, générique ou avec
  la VOLL (usages non flexibles, puis usages flexibles)
- `welfare` : surplus social pour une quantité donnée
- `optimum` : surplus maximal en q*, perte au-delà
- `market` : équilibre de marché, prix et partage du surplus.

Usage :

    from pyelec import economie, style
    style.use()
    fig, ax = plt.subplots(figsize=economie.FIGSIZE)
    economie.optimum(ax)
"""

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import ConnectionPatch, Rectangle

from pyelec.palette import color
from pyelec.schema import ACCENTS, TEXT, TEXT_LIGHT, _shade

# Couleurs : l'offre reprend la production des schémas, la demande la consommation.
SUPPLY = ACCENTS["production"]
DEMAND = ACCENTS["consommation"]
WELFARE = "#0f766e"  # surplus social, avant tout partage
ALERT = "#dc2626"  # perte de surplus
PRICE = TEXT

# Taille des figures en colonne de slide (55 % de la largeur).
FIGSIZE = (5.2, 3.9)

# Courbes stylisées, quantités et montants sur [0, 1] (unités arbitraires).
Q_MAX = 1.0
Y_MAX = 1.0
VOLL = 0.85  # utilité marginale des usages non flexibles
Q_RIGID = 0.5  # consommation valorisée à la VOLL
Q_SATED = 0.85  # au-delà, plus aucun usage n'a de valeur


def marginal_cost(q):
    """Coût marginal stylisé : croissant et convexe."""
    return 0.08 + 0.75 * np.asarray(q) ** 2


def marginal_utility_curve(q, voll: bool = False):
    """Utilité marginale stylisée.

    Générique (défaut) : décroissance affine. Avec `voll` : VOLL jusqu'à Q_RIGID
    (usages non flexibles), puis décroissance affine forte (usages flexibles).
    """
    q = np.asarray(q, dtype=float)
    if not voll:
        return 0.92 - 0.75 * q
    slope = VOLL / (Q_SATED - Q_RIGID)
    return np.clip(VOLL - slope * (q - Q_RIGID), 0, VOLL)


def _utility_end(voll: bool) -> float:
    """Quantité où s'arrête le tracé de l'utilité marginale."""
    return Q_SATED if voll else Q_MAX


def optimum_point(voll: bool = False) -> tuple[float, float]:
    """Quantité où l'utilité marginale égale le coût marginal, et leur valeur commune."""
    lo, hi = 0.0, _utility_end(voll)
    for _ in range(60):
        mid = (lo + hi) / 2
        if marginal_utility_curve(mid, voll) > marginal_cost(mid):
            lo = mid
        else:
            hi = mid
    q = (lo + hi) / 2
    return float(q), float(marginal_cost(q))


def _concept_axes(ax: plt.Axes, xlabel: str, ylabel: str, xmax=Q_MAX, ymax=Y_MAX) -> None:
    """Axes de schéma : sans graduations ni grille, flèches au bout des axes."""
    ax.set_xlim(0, xmax * 1.08)
    ax.set_ylim(0, ymax * 1.08)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.grid(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(TEXT)
        ax.spines[side].set_linewidth(1.2)
    ax.plot(1, 0, ">", color=TEXT, transform=ax.transAxes, clip_on=False, ms=6)
    ax.plot(0, 1, "^", color=TEXT, transform=ax.transAxes, clip_on=False, ms=6)
    ax.set_xlabel(xlabel, color=TEXT, loc="right", fontsize=13)
    ax.text(0.03, 1.0, ylabel, transform=ax.transAxes, ha="left", va="top", color=TEXT,
            fontsize=13)  # fmt: skip


def _tick(ax, value, text, axis="y", c=PRICE):
    """Repère nommé sur un axe (p*, q*, VOLL…), à la place des graduations."""
    if axis == "y":
        ax.text(-0.015, value, text, ha="right", va="center", color=c, fontsize=14,
                transform=ax.get_yaxis_transform())  # fmt: skip
    else:
        ax.text(value, -0.015, text, ha="center", va="top", color=c, fontsize=14,
                transform=ax.get_xaxis_transform())  # fmt: skip


def fixed_and_variable_costs(ax: plt.Axes) -> None:
    """Coût total annuel d'une centrale selon sa production : CF + CV × q."""
    _concept_axes(ax, "Production sur l'année (MWh)", "Coût total (€)")
    cf, cv = 0.35, 0.5
    q = np.array([0, Q_MAX])
    ax.fill_between(q, 0, cf, color=_shade(SUPPLY, 0.75), lw=0)
    ax.fill_between(q, cf, cf + cv * q, color=_shade(SUPPLY, 0.45), lw=0)
    ax.plot(q, cf + cv * q, color=SUPPLY, lw=3)
    ax.text(0.5, cf / 2, "Coûts fixes : payés même à l'arrêt", ha="center", va="center",
            color=TEXT, fontsize=14)  # fmt: skip
    ax.text(0.68, cf + 0.12, "Coûts variables :\nproportionnels\nà la production",
            ha="center", va="center", color=TEXT, fontsize=14)  # fmt: skip
    ax.annotate("pente : coût variable\n(€/MWh)", xy=(0.3, cf + cv * 0.3),
                xytext=(0.08, 0.76), color=TEXT, fontsize=13,
                arrowprops={"arrowstyle": "->", "color": TEXT_LIGHT})  # fmt: skip


# Parc stylisé du coût marginal de court terme : (filière, capacité, coût variable).
SHORT_RUN_FLEET = [
    ("nucleaire", 0.45, 0.15),
    ("gaz", 0.3, 0.42),
    ("charbon-fioul", 0.15, 0.7),
]


CAPACITY = 0.95  # capacité du parc stylisé, en unités de quantité


def short_run_marginal_cost(ax: plt.Axes, quantity: float = 0.6) -> None:
    """Coût marginal de court terme continu et croissant, l'aire dessous est le coût C(q)."""
    _concept_axes(ax, "Production (MWh)", "€/MWh")
    q = np.linspace(0, CAPACITY, 300)
    inside = q <= quantity
    ax.fill_between(q[inside], 0, marginal_cost(q[inside]), color=_shade(SUPPLY, 0.7), lw=0)
    ax.plot(q, marginal_cost(q), color=SUPPLY, lw=3)
    ax.vlines(CAPACITY, marginal_cost(CAPACITY), Y_MAX * 1.05, color=TEXT, lw=2,
              ls=(0, (4, 3)))  # fmt: skip
    ax.text(CAPACITY - 0.02, 1.0, "capacité\ndu parc", ha="right", va="top", color=TEXT,
            fontsize=13)  # fmt: skip
    ax.text(quantity * 0.6, 0.04, "C(q)", ha="center", va="bottom",
            color=_shade(SUPPLY, -0.4), fontsize=15, fontweight="bold")  # fmt: skip
    ax.text(0.5, 0.42, "coût marginal", ha="right", va="bottom", color=SUPPLY, fontsize=14,
            fontweight="bold")  # fmt: skip
    cm = float(marginal_cost(quantity))
    ax.vlines(quantity, 0, cm, color=TEXT_LIGHT, lw=1.2, ls=":")
    ax.hlines(cm, 0, quantity, color=TEXT_LIGHT, lw=1.2, ls=":")
    ax.plot(quantity, cm, "o", color=TEXT, ms=7, zorder=5)
    _tick(ax, quantity, "q", axis="x")
    _tick(ax, cm, "Cm(q)")


def _units(n: int = 120, seed: int = 4) -> tuple[np.ndarray, np.ndarray]:
    """Parc stylisé de n unités : bornes de capacité cumulée et coût variable de chacune."""
    widths = np.random.default_rng(seed).uniform(0.5, 1.5, n)
    bounds = np.concatenate([[0], np.cumsum(widths)]) / widths.sum() * CAPACITY
    costs = marginal_cost((bounds[:-1] + bounds[1:]) / 2)
    return bounds, costs


def _steps(ax, bounds, costs, lw, fill=False):
    for x0, x1, c in zip(bounds[:-1], bounds[1:], costs):
        if fill:
            ax.fill_between([x0, x1], 0, c, color=_shade(SUPPLY, 0.75), lw=0)
        ax.hlines(c, x0, x1, color=SUPPLY, lw=lw)
    ax.vlines(bounds[1:-1], costs[:-1], costs[1:], color=SUPPLY, lw=lw * 0.6)


def marginal_cost_zoom(fig: plt.Figure, window: tuple[float, float] = (0.6, 0.67)) -> None:
    """Le coût marginal d'un parc de nombreuses unités : continu de loin, en paliers de près."""
    far, near = fig.subplots(1, 2, gridspec_kw={"wspace": 0.35})
    bounds, costs = _units()
    _concept_axes(far, "Production (MWh)", "€/MWh")
    _steps(far, bounds, costs, lw=2.5)
    far.set_title("De loin : une courbe continue", color=TEXT, fontsize=14, loc="left")

    x0, x1 = window
    y0, y1 = float(marginal_cost(x0)) - 0.02, float(marginal_cost(x1)) + 0.02
    far.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, ec=TEXT, lw=1.2, zorder=5))

    _concept_axes(near, "Production (MWh)", "€/MWh")
    near.set_xlim(x0, x0 + (x1 - x0) * 1.08)
    near.set_ylim(y0, y0 + (y1 - y0) * 1.08)
    near.spines[["left", "bottom"]].set_color(TEXT_LIGHT)
    q = np.linspace(x0, x1, 100)
    near.plot(q, marginal_cost(q), color=TEXT_LIGHT, lw=1.5, ls="--")
    inside = (bounds[1:] > x0) & (bounds[:-1] < x1)
    k = np.flatnonzero(inside)
    _steps(near, bounds[k[0] : k[-1] + 2], costs[k[0] : k[-1] + 1], lw=3.5)
    near.set_title("De près : des paliers", color=TEXT, fontsize=14, loc="left")
    mid = k[len(k) // 2]
    near.annotate("une centrale :\ncoût variable\nconstant",
                  xy=((bounds[mid] + bounds[mid + 1]) / 2, costs[mid]),
                  xytext=(x0 + 0.01, y1 - 0.02), va="top", color=TEXT, fontsize=13,
                  arrowprops={"arrowstyle": "->", "color": TEXT_LIGHT})  # fmt: skip
    for y_far, y_near in ((y1, 1.0), (y0, 0.0)):
        fig.add_artist(ConnectionPatch((x1, y_far), (0, y_near), coordsA="data",
                                       coordsB="axes fraction", axesA=far, axesB=near,
                                       color=TEXT_LIGHT, lw=1, ls=":"))  # fmt: skip


def merit_order_steps(ax: plt.Axes, demand: float = 0.6) -> None:
    """Coût marginal en paliers d'un parc stylisé (une filière par palier), jusqu'à sa capacité."""
    _concept_axes(ax, "Production (MW)", "€/MWh")
    x0 = 0.0
    for tech, capacity, cv in SHORT_RUN_FLEET:
        c = color(tech)
        ax.fill_between([x0, x0 + capacity], 0, cv, color=c, alpha=0.3, lw=0)
        ax.hlines(cv, x0, x0 + capacity, color=c, lw=4)
        x0 += capacity
    ax.vlines(x0, SHORT_RUN_FLEET[-1][2], Y_MAX * 1.05, color=TEXT, lw=2, ls=(0, (4, 3)))
    ax.text(x0 - 0.02, 0.95, "capacité\ndu parc", ha="right", va="top", color=TEXT, fontsize=13)
    # coût marginal à un niveau de production donné
    bounds = np.cumsum([cap for _, cap, _ in SHORT_RUN_FLEET])
    k = int(np.searchsorted(bounds, demand))
    cm = SHORT_RUN_FLEET[k][2]
    ax.vlines(demand, 0, cm, color=TEXT_LIGHT, lw=1.2, ls=":")
    ax.hlines(cm, 0, demand, color=TEXT_LIGHT, lw=1.2, ls=":")
    ax.plot(demand, cm, "o", color=TEXT, ms=7, zorder=5)
    _tick(ax, demand, "q", axis="x")
    _tick(ax, cm, "Cm(q)")


HOURS = 8760


def long_run_marginal_cost(ax: plt.Axes) -> None:
    """Coût marginal de long terme d'une hausse de demande de 1 MW pendant h heures : CV + CF/h."""
    _concept_axes(ax, "Durée de la hausse de demande (h/an)", "€/MWh", xmax=HOURS)
    cf, cv = 455.0, 0.25  # coût fixe annuel et coût variable, unités arbitraires
    h = np.linspace(650, HOURS, 300)
    lrmc = cv + cf / h
    ax.fill_between(h, 0, cv, color=_shade(SUPPLY, 0.45), lw=0)
    ax.fill_between(h, cv, lrmc, color=_shade(SUPPLY, 0.78), lw=0)
    ax.plot(h, lrmc, color=SUPPLY, lw=3)
    ax.text(4700, cv / 2, "coût variable :\nle seul compté à court terme", ha="center",
            va="center", color=TEXT, fontsize=13)  # fmt: skip
    arrow = {"arrowstyle": "->", "color": TEXT_LIGHT}
    ax.text(1150, 0.36, "part des\ncoûts fixes", ha="left", va="center", color=TEXT,
            fontsize=13)  # fmt: skip
    ax.annotate("à la pointe :\npeu d'heures,\nMWh très cher", xy=(900, cv + cf / 900),
                xytext=(1500, 0.98), va="top", color=TEXT, fontsize=13,
                arrowprops=arrow)  # fmt: skip
    ax.annotate("en ruban :\ntoute l'année", xy=(HOURS, cv + cf / HOURS),
                xytext=(HOURS * 0.8, 0.55), ha="center", color=TEXT, fontsize=13,
                arrowprops=arrow)  # fmt: skip


def marginal_utility(ax: plt.Axes, voll: bool = False, quantity: float = 0.55) -> None:
    """Utilité marginale et utilité totale.

    Générique (défaut) : courbe décroissante, utilité totale jusqu'à `quantity`.
    Avec `voll` : usages valorisés à la VOLL, puis usages flexibles.
    """
    _concept_axes(ax, "Consommation (MWh)", "€/MWh")
    q = np.linspace(0, _utility_end(voll), 300)
    um = marginal_utility_curve(q, voll)
    if voll:
        ax.fill_between(q, 0, um, color=_shade(DEMAND, 0.85), lw=0)
        _tick(ax, VOLL, "VOLL", c=DEMAND)
        ax.text(0.03, VOLL - 0.04, "usages non flexibles :\nvalorisés à la VOLL", ha="left",
                va="top", color=TEXT, fontsize=13)  # fmt: skip
        ax.text(0.75, 0.55, "usages\nflexibles", ha="left", va="center", color=TEXT,
                fontsize=13)  # fmt: skip
    else:
        inside = q <= quantity
        ax.fill_between(q[inside], 0, um[inside], color=_shade(DEMAND, 0.85), lw=0)
        ax.vlines(quantity, 0, marginal_utility_curve(quantity), color=TEXT_LIGHT, lw=1.2,
                  ls=":")  # fmt: skip
        _tick(ax, quantity, "q", axis="x")
        ax.text(0.6, marginal_utility_curve(0.6) + 0.06, "utilité marginale", ha="left",
                color=DEMAND, fontsize=14, fontweight="bold")  # fmt: skip
    ax.plot(q, um, color=DEMAND, lw=3)
    ax.text(0.3, 0.3, "utilité totale\n(€)", ha="center", va="center", color=TEXT,
            fontsize=14)  # fmt: skip


def _curves(ax: plt.Axes, voll: bool) -> None:
    """Coût marginal et utilité marginale, avec leurs libellés."""
    q = np.linspace(0, Q_MAX, 300)
    ax.plot(q, marginal_cost(q), color=SUPPLY, lw=3)
    qu = np.linspace(0, _utility_end(voll), 300)
    ax.plot(qu, marginal_utility_curve(qu, voll), color=DEMAND, lw=3)
    bold = {"fontsize": 14, "fontweight": "bold"}
    if voll:
        ax.text(0.92, 0.45, "coût\nmarginal", ha="left", va="center", color=SUPPLY, **bold)
        ax.text(0.02, VOLL + 0.03, "utilité marginale", ha="left", va="bottom", color=DEMAND,
                **bold)  # fmt: skip
        _tick(ax, VOLL, "VOLL", c=DEMAND)
    else:
        ax.text(0.97, 0.86, "coût marginal", ha="right", va="bottom", color=SUPPLY, **bold)
        ax.text(0.05, float(marginal_utility_curve(0.05)) + 0.03, "utilité marginale",
                ha="left", va="bottom", color=DEMAND, **bold)  # fmt: skip


def welfare(ax: plt.Axes, quantity: float = 0.4, voll: bool = False) -> None:
    """Surplus social pour une quantité donnée : aire entre utilité et coût marginaux."""
    _concept_axes(ax, "Quantité (MWh)", "€/MWh")
    q = np.linspace(0, quantity, 300)
    ax.fill_between(q, marginal_cost(q), marginal_utility_curve(q, voll),
                    color=_shade(WELFARE, 0.75), lw=0)  # fmt: skip
    ax.text(quantity / 2, 0.5, "surplus\nsocial", ha="center", va="center",
            color=_shade(WELFARE, -0.3), fontsize=15, fontweight="bold")  # fmt: skip
    _curves(ax, voll)
    ax.vlines(quantity, 0, marginal_cost(quantity), color=TEXT_LIGHT, lw=1.2, ls=":")
    _tick(ax, quantity, "q", axis="x")


def optimum(ax: plt.Axes, voll: bool = False) -> tuple[float, float]:
    """Optimum : surplus maximal en q*, perte au-delà (coût marginal > utilité marginale).

    Renvoie la quantité optimale et la valeur commune des deux courbes.
    """
    _concept_axes(ax, "Quantité (MWh)", "€/MWh")
    q_opt, v_opt = optimum_point(voll)
    q = np.linspace(0, q_opt, 300)
    ax.fill_between(q, marginal_cost(q), marginal_utility_curve(q, voll),
                    color=_shade(WELFARE, 0.75), lw=0)  # fmt: skip
    ax.text(0.27, 0.52, "surplus\nmaximal", ha="center", va="center",
            color=_shade(WELFARE, -0.3), fontsize=15, fontweight="bold")  # fmt: skip
    end = _utility_end(voll)
    beyond = np.linspace(q_opt, end, 100)
    ax.fill_between(beyond, marginal_utility_curve(beyond, voll), marginal_cost(beyond),
                    facecolor="none", edgecolor=_shade(ALERT, 0.3), hatch="///", lw=0)  # fmt: skip
    if voll:
        ax.text(end + 0.02, 0.12, "perte", ha="left", va="center", color=ALERT, fontsize=14)
    else:
        ax.text(0.93, 0.47, "perte", ha="center", va="center", color=ALERT, fontsize=14,
                bbox={"fc": "white", "ec": "none", "pad": 1})  # fmt: skip
    _curves(ax, voll)
    ax.vlines(q_opt, 0, v_opt, color=TEXT_LIGHT, lw=1.2, ls=":")
    ax.plot(q_opt, v_opt, "o", color=TEXT, ms=8, zorder=5)
    _tick(ax, q_opt, "q*", axis="x")
    return q_opt, v_opt


def market(ax: plt.Axes, voll: bool = False) -> tuple[float, float]:
    """Équilibre de marché : le prix p* égalise offre et demande et partage le surplus.

    Renvoie la quantité et le prix d'équilibre.
    """
    _concept_axes(ax, "Quantité (MWh)", "€/MWh")
    q_eq, p_eq = optimum_point(voll)
    q = np.linspace(0, q_eq, 300)
    ax.fill_between(q, p_eq, marginal_utility_curve(q, voll), color=_shade(DEMAND, 0.7), lw=0)
    ax.fill_between(q, marginal_cost(q), p_eq, color=_shade(SUPPLY, 0.6), lw=0)
    ax.text(0.25 if voll else 0.18, 0.63 if voll else 0.56, "surplus des\nconsommateurs",
            ha="center", va="center", color=_shade(DEMAND, -0.35), fontsize=14)  # fmt: skip
    ax.text(0.2, 0.28, "surplus des\nproducteurs", ha="center", va="center",
            color=_shade(SUPPLY, -0.4), fontsize=14)  # fmt: skip
    _curves(ax, voll)
    ax.vlines(q_eq, 0, p_eq, color=TEXT_LIGHT, lw=1.2, ls=":")
    ax.hlines(p_eq, 0, q_eq, color=TEXT_LIGHT, lw=1.2, ls=":")
    ax.plot(q_eq, p_eq, "o", color=TEXT, ms=8, zorder=5)
    _tick(ax, p_eq, "p*")
    _tick(ax, q_eq, "q*", axis="x")
    return q_eq, p_eq
