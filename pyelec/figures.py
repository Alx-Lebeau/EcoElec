"""Figures réutilisées d'un module à l'autre (poly, slides, TP)."""

import matplotlib.pyplot as plt
import pandas as pd

from pyelec.palette import color, label


def merit_order(ax: plt.Axes, fleet: pd.DataFrame, demand: float | None = None) -> float | None:
    """Trace la courbe d'offre (merit order) d'un parc et renvoie le prix d'équilibre.

    `fleet` : une ligne par filière, colonnes `filiere`, `capacite` (GW) et
    `cout_variable` (€/MWh). Si `demand` (GW) est donnée, trace la demande
    inélastique et renvoie le coût variable de la filière marginale (None si la
    demande dépasse la capacité totale).
    """
    fleet = fleet.sort_values("cout_variable", kind="stable").reset_index(drop=True)
    left = fleet["capacite"].cumsum() - fleet["capacite"]
    for x0, row in zip(left, fleet.itertuples()):
        c = color(row.filiere)
        ax.bar(
            x0,
            row.cout_variable,
            width=row.capacite,
            align="edge",
            color=c,
            alpha=0.35,
            linewidth=0,
        )
        ax.hlines(
            row.cout_variable, x0, x0 + row.capacite, color=c, linewidth=4, label=label(row.filiere)
        )
    ax.set_xlim(0, fleet["capacite"].sum() * 1.05)
    ax.set_ylim(0, fleet["cout_variable"].max() * 1.2)
    ax.set_xlabel("Capacité cumulée (GW)")
    ax.set_ylabel("Coût variable (€/MWh)")

    price = None
    if demand is not None:
        ax.axvline(demand, color="black", linewidth=1.5, linestyle="--", label="demande")
        right = left + fleet["capacite"]
        marginal = fleet[(left < demand) & (right >= demand)]
        if not marginal.empty:
            price = float(marginal["cout_variable"].iloc[0])
            ax.axhline(price, color="0.3", linewidth=1, linestyle=":")
    ax.legend(loc="upper left", ncols=2)
    return price
