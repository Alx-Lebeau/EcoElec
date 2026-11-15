"""Deux lois physiques qui contraignent le système électrique.

- `balance` : injections et soutirages s'égalisent à chaque instant ; la
  fréquence signale tout déséquilibre.
- `kirchhoff` : sur un réseau maillé, les flux se répartissent selon les
  impédances des lignes (calcul en courant continu, `dc_flows`).
"""

import math

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch, Wedge

from pyelec.schema import ACCENTS, TEXT, TEXT_LIGHT, _shade

INJECT = ACCENTS["production"]
WITHDRAW = ACCENTS["consommation"]
OK = "#16a34a"
ALERT = "#dc2626"


def dc_flows(
    lines: list[tuple[int, int]], reactances: list[float], injections: list[float]
) -> np.ndarray:
    """Flux sur chaque ligne d'un réseau, approximation en courant continu.

    `injections` : puissance nette injectée à chaque nœud (somme nulle, en MW).
    Le nœud 0 sert de référence. Renvoie le flux de `a` vers `b` pour chaque
    ligne (a, b).
    """
    n = len(injections)
    b_matrix = np.zeros((n, n))
    for (a, b), x in zip(lines, reactances):
        b_matrix[a, a] += 1 / x
        b_matrix[b, b] += 1 / x
        b_matrix[a, b] -= 1 / x
        b_matrix[b, a] -= 1 / x
    theta = np.zeros(n)
    theta[1:] = np.linalg.solve(b_matrix[1:, 1:], np.asarray(injections, float)[1:])
    return np.array([(theta[a] - theta[b]) / x for (a, b), x in zip(lines, reactances)])


def _pill(ax, x, y, w, h, text, fc, tc="white", size=11):
    ax.add_patch(
        FancyBboxPatch(
            (x - w / 2, y - h / 2),
            w,
            h,
            boxstyle=f"round,pad=0,rounding_size={h / 2}",
            fc=fc,
            ec="none",
            zorder=3,
        )
    )
    ax.text(x, y, text, ha="center", va="center", fontsize=size, color=tc, zorder=4)


H = 7.2  # hauteur des panneaux (largeur 10)


def balance(ax: plt.Axes) -> None:
    """Injections = soutirages, et la fréquence comme signal du déséquilibre."""
    ax.text(5, 6.85, "À chaque instant", ha="center", va="center", fontsize=13.5,
            fontweight="bold", color=TEXT)  # fmt: skip
    columns = [
        (2.3, "Injections", INJECT, ["production", "déstockage", "importations"]),
        (7.7, "Soutirages", WITHDRAW, ["consommation", "stockage", "exportations", "pertes"]),
    ]
    for x, title, c, items in columns:
        ax.text(x, 6.05, title, ha="center", va="center", fontsize=13, fontweight="bold",
                color=_shade(c, -0.2))  # fmt: skip
        for k, item in enumerate(items):
            _pill(ax, x, 5.35 - 0.62 * k, 3.6, 0.5, item, _shade(c, 0.82), tc=TEXT)
    ax.text(5, 4.75, "=", ha="center", va="center", fontsize=34, fontweight="bold", color=TEXT)
    ax.text(5, 2.85, "Le réseau ne stocke rien : batteries et STEP injectent ou soutirent.",
            ha="center", va="center", fontsize=10.5, color=TEXT_LIGHT)  # fmt: skip

    # Cadran de fréquence : zone normale autour de 50 Hz.
    cx, cy, r = 5, 0.35, 1.75
    span = (49.0, 51.0)

    def angle(f):
        return 180 - 180 * (f - span[0]) / (span[1] - span[0])

    for f0, f1, c in ((49.0, 49.8, ALERT), (49.8, 50.2, OK), (50.2, 51.0, ALERT)):
        ax.add_patch(Wedge((cx, cy), r, angle(f1), angle(f0), width=0.32,
                           fc=_shade(c, 0.35), ec="white", lw=2, zorder=2))  # fmt: skip
    a = math.radians(angle(50.0))
    ax.plot([cx, cx + 0.82 * r * math.cos(a)], [cy, cy + 0.82 * r * math.sin(a)], color=TEXT,
            lw=3, solid_capstyle="round", zorder=3)  # fmt: skip
    ax.add_patch(Circle((cx, cy), 0.13, fc=TEXT, zorder=4))
    ax.text(cx, cy + r + 0.3, "fréquence : 50 Hz", ha="center", va="center", fontsize=11.5,
            fontweight="bold", color=TEXT)  # fmt: skip
    ax.text(cx - r - 0.15, cy + 0.35, "consommation\n> production", ha="right", va="center",
            fontsize=10.5, color=TEXT_LIGHT, linespacing=1.1)  # fmt: skip
    ax.text(cx + r + 0.15, cy + 0.35, "production\n> consommation", ha="left", va="center",
            fontsize=10.5, color=TEXT_LIGHT, linespacing=1.1)  # fmt: skip
    ax.set_xlim(0, 10)
    ax.set_ylim(0, H)
    ax.set_aspect("equal")
    ax.axis("off")


def kirchhoff(ax: plt.Axes, power: float = 300.0) -> np.ndarray:
    """Triangle de trois nœuds : la production en A, la consommation en B.

    Lignes d'impédances égales : le chemin direct porte deux tiers du flux, le
    détour par C un tiers. Renvoie les flux A→B, A→C, C→B (MW).
    """
    nodes = {"A": (1.6, 4.4), "B": (8.4, 4.4), "C": (5.0, 1.25)}
    lines = [(0, 1), (0, 2), (2, 1)]
    flows = dc_flows(lines, [1.0, 1.0, 1.0], [power, -power, 0.0])
    names = ["A", "B", "C"]
    line_color = ACCENTS["transport"]
    ax.text(5, 6.85, "Les flux suivent la physique", ha="center", va="center", fontsize=13.5,
            fontweight="bold", color=TEXT)  # fmt: skip
    for (a, b), f in zip(lines, flows):
        (x0, y0), (x1, y1) = nodes[names[a]], nodes[names[b]]
        ax.add_patch(
            FancyArrowPatch(
                (x0, y0),
                (x1, y1),
                arrowstyle="-|>",
                mutation_scale=22,
                lw=2 + 6 * abs(f) / power,
                color=line_color,
                shrinkA=22,
                shrinkB=22,
                zorder=2,
            )
        )
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        if y0 == y1:
            dx, dy, ha = 0, 0.5, "center"
        else:
            dx, dy, ha = (-0.55, 0, "right") if mx < 5 else (0.55, 0, "left")
        ax.text(mx + dx, my + dy, f"{abs(f):.0f} MW", ha=ha, va="center", fontsize=12,
                fontweight="bold", color=_shade(line_color, -0.2))  # fmt: skip
    for name, (x, y) in nodes.items():
        ax.add_patch(Circle((x, y), 0.45, fc="white", ec=TEXT, lw=1.8, zorder=3))
        ax.text(x, y, name, ha="center", va="center", fontsize=13, fontweight="bold",
                color=TEXT, zorder=4)  # fmt: skip
    ax.text(nodes["A"][0], nodes["A"][1] + 0.7, f"production\n{power:.0f} MW", ha="center",
            va="bottom", fontsize=11, color=_shade(INJECT, -0.2), linespacing=1.1)  # fmt: skip
    ax.text(nodes["B"][0], nodes["B"][1] + 0.7, f"consommation\n{power:.0f} MW", ha="center",
            va="bottom", fontsize=11, color=_shade(WITHDRAW, -0.1), linespacing=1.1)  # fmt: skip
    ax.text(5, 0.25, "lignes identiques : on ne choisit pas le chemin", ha="center",
            va="center", fontsize=11, color=TEXT_LIGHT)  # fmt: skip
    ax.set_xlim(0, 10)
    ax.set_ylim(0, H)
    ax.set_aspect("equal")
    ax.axis("off")
    return flows


def physical_laws(fig: plt.Figure) -> np.ndarray:
    """Les deux panneaux côte à côte, séparés par un filet. Renvoie les flux de `kirchhoff`."""
    left = fig.add_axes((0.0, 0.0, 0.49, 1.0))
    right = fig.add_axes((0.51, 0.0, 0.49, 1.0))
    balance(left)
    flows = kirchhoff(right)
    fig.add_artist(plt.Line2D([0.5, 0.5], [0.06, 0.94], color="#e2e8f0", lw=1.2))
    return flows
