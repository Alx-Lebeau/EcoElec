"""Équilibre de court terme d'un parc donné : coûts variables, merit order, prix.

Données :

- `data/exemple/parc-court-terme.csv` : parc illustratif (capacité disponible en GW,
  valeur d'usage en €/MWh des filières sans combustible acheté) ;
- `data/exemple/demande-court-terme.csv` : demande illustrative (usages non
  flexibles, valorisés à la VOLL, et largeur de la partie flexible, en GW) ;
- `data/couts/` : prix du gaz et du CO₂, caractéristiques des centrales au gaz.

Fonctions :

- `load_gas_plants` : rendement, facteur d'émission et VOM des CCG et des TAC ;
- `gas_plant_costs` : décomposition du coût variable des CCG et des TAC ;
- `load_fleet`, `load_demand` : parc avec ses coûts variables, situations de demande ;
- `fleet_and_demand` : le problème du planificateur, capacités disponibles et demande ;
- `gas_cost_breakdown` : barres empilées gaz, CO₂, VOM ;
- `supply_curve` : merit order en paliers ;
- `load_gas_prices`, `load_annual_prices`, `fuel_prices` : prix du gaz et du CO₂ ;
- `gas_plant_flow` : bilan d'une centrale au gaz pour 1 MWh de gaz brûlé ;
- `equilibrium` : offre, demande (VOLL hors d'échelle, axe interrompu), prix,
  surplus, énergie non distribuée.

Usage :

    from pyelec import dispatch, style
    style.use()
    fleet = dispatch.load_fleet()
    fig, ax = plt.subplots(figsize=dispatch.FIGSIZE)
    dispatch.equilibrium(ax, fleet, dispatch.load_demand().loc["normale"])
"""

from dataclasses import dataclass

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

from pyelec.palette import color, label
from pyelec.paths import DATA_DIR
from pyelec.schema import ACCENTS, TEXT, TEXT_LIGHT, _shade

DEMAND = ACCENTS["consommation"]
CONSUMER = _shade(DEMAND, 0.72)
PRODUCER = _shade(ACCENTS["production"], 0.6)
ALERT = "#dc2626"
CO2 = "#64748b"
VOM = "#cbd5e1"

# Figure en colonne de slide, à côté d'un texte.
FIGSIZE = (5.6, 4.1)


class _Text(str):
    """Chaîne dont le `repr` garde les caractères tels quels.

    Quarto affiche le `repr` d'une expression en ligne (`{python} …`), et le `repr`
    d'une chaîne ordinaire échappe l'espace fine insécable (« 3\\u202f099 »).
    """

    def __repr__(self) -> str:
        return f"'{self}'"


def number(x: float, digits: int = 0) -> str:
    """Nombre à la française : virgule décimale, espace fine des milliers."""
    text = f"{x:,.{digits}f}".replace(",", "\u202f").replace(".", ",")
    return _Text(text)


def load_gas_plants() -> pd.DataFrame:
    """Centrales au gaz, grandeurs rapportées au MWh de gaz PCS (unité des prix du gaz).

    Colonnes : `rendement_pci` (convention usuelle), `rendement` (MWh électriques par
    MWh PCS), `facteur_emission` (tCO₂ par MWh PCS), `vom` (€/MWh électrique).
    """
    plants = pd.read_csv(DATA_DIR / "couts" / "centrales-gaz.csv").set_index("filiere")
    gas = load_natural_gas()
    plants["rendement"] = plants["rendement_pci"] * gas["pci_par_pcs"]
    plants["facteur_emission"] = gas["facteur_emission_pci"] * gas["pci_par_pcs"]
    return plants


def load_natural_gas() -> pd.Series:
    """Constantes du gaz naturel : `facteur_emission_pci` (tCO₂/MWh PCI), `pci_par_pcs`."""
    return pd.read_csv(DATA_DIR / "couts" / "gaz-naturel.csv").set_index("grandeur")["valeur"]


def gas_plant_costs(year: int | None = None) -> pd.DataFrame:
    """Coût variable des centrales au gaz (€/MWh électrique), par composante.

    Colonnes `gaz` (prix du gaz / rendement), `co2` (facteur d'émission × prix
    du CO₂ / rendement), `vom` et `total`, une ligne par filière (`ccg`, `tac`).
    L'année retenue (par défaut la dernière disponible) est dans `attrs["annee"]`.
    """
    prices = pd.read_csv(DATA_DIR / "couts" / "prix-gaz-co2.csv").set_index("annee")
    year = int(prices.index.max()) if year is None else year
    p = prices.loc[year]
    plants = load_gas_plants()
    costs = pd.DataFrame(
        {
            "gaz": p["gaz_eur_mwh"] / plants["rendement"],
            "co2": plants["facteur_emission"] * p["co2_eur_t"] / plants["rendement"],
            "vom": plants["vom"],
        }
    )
    costs["total"] = costs.sum(axis=1)
    costs.attrs["annee"] = year
    costs.attrs["prix_gaz"] = float(p["gaz_eur_mwh"])
    costs.attrs["prix_co2"] = float(p["co2_eur_t"])
    return costs


def load_fleet(year: int | None = None) -> pd.DataFrame:
    """Parc illustratif : `filiere`, `capacite` (GW), `cout_variable` (€/MWh).

    Coût variable : valeur d'usage pour les filières qui en ont une, coût calculé
    par `gas_plant_costs` pour les centrales au gaz. Ordre du fichier conservé.
    """
    fleet = pd.read_csv(DATA_DIR / "exemple" / "parc-court-terme.csv")
    gas = gas_plant_costs(year)["total"]
    fleet["cout_variable"] = fleet["valeur_usage"].fillna(fleet["filiere"].map(gas))
    return fleet[["filiere", "capacite", "cout_variable"]]


def load_demand() -> pd.DataFrame:
    """Situations de demande : `non_flexible` et `flexible` (GW), indexées par situation."""
    return pd.read_csv(DATA_DIR / "exemple" / "demande-court-terme.csv").set_index("situation")


def merit_order(fleet: pd.DataFrame) -> pd.DataFrame:
    """Parc classé par coût variable croissant, avec les bornes `debut` et `fin` (GW)."""
    ordered = fleet.sort_values("cout_variable", kind="stable").reset_index(drop=True)
    ordered["fin"] = ordered["capacite"].cumsum()
    ordered["debut"] = ordered["fin"] - ordered["capacite"]
    return ordered


def _axes(ax: plt.Axes, xmax: float, xlabel: str = "Puissance (GW)") -> None:
    ax.grid(False)
    ax.set_xlim(0, xmax)
    ax.set_xlabel(xlabel, color=TEXT, fontsize=12)
    ax.tick_params(colors=TEXT_LIGHT, labelsize=11)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(TEXT)


def fleet_and_demand(ax: plt.Axes, fleet: pd.DataFrame, demand: float) -> None:
    """Le problème du planificateur : un parc et une demande, sans suggérer de réponse.

    Une vignette par filière (ordre alphabétique des libellés, tailles égales, donc
    sans classement ni proportion), et la demande à part.
    """
    tiles = fleet.assign(nom=fleet["filiere"].map(label)).sort_values("nom")
    n = len(tiles)
    w, gap = 1.25, 0.18
    ax.set_xlim(-0.1, n * (w + gap) + 1.6)
    ax.set_ylim(-0.15, 1.25)
    ax.axis("off")
    ax.text(0, 1.18, "Centrales disponibles", ha="left", va="center", color=TEXT, fontsize=13,
            fontweight="bold")  # fmt: skip
    for i, row in enumerate(tiles.itertuples()):
        x = i * (w + gap)
        c = color(row.filiere)
        ax.add_patch(FancyBboxPatch((x, 0), w, 1, fc=_shade(c, 0.8), ec=c, lw=2.5,
                                    boxstyle="round,pad=0,rounding_size=0.06"))  # fmt: skip
        ax.text(x + w / 2, 0.66, row.nom, ha="center", va="center", color=_shade(c, -0.35),
                fontsize=12.5, fontweight="bold")  # fmt: skip
        ax.text(x + w / 2, 0.32, f"{number(row.capacite)} GW", ha="center", va="center",
                color=TEXT, fontsize=14)  # fmt: skip
    x = n * (w + gap) + 0.35
    ax.text(x, 1.18, "À servir", ha="left", va="center", color=TEXT, fontsize=13,
            fontweight="bold")  # fmt: skip
    ax.add_patch(FancyBboxPatch((x, 0), 1.2, 1, fc=_shade(DEMAND, 0.82), ec=DEMAND, lw=2.5,
                                boxstyle="round,pad=0,rounding_size=0.06"))  # fmt: skip
    ax.text(x + 0.6, 0.66, "Demande", ha="center", va="center", color=_shade(DEMAND, -0.3),
            fontsize=13, fontweight="bold")  # fmt: skip
    ax.text(x + 0.6, 0.32, f"{number(demand)} GW", ha="center", va="center", color=TEXT,
            fontsize=14)  # fmt: skip
    ax.vlines(x - 0.2, 0, 1, color=TEXT_LIGHT, lw=1.2, ls=":")


def gas_cost_breakdown(ax: plt.Axes, costs: pd.DataFrame) -> None:
    """Coût variable des CCG et des TAC décomposé : gaz, CO₂, VOM (barres empilées)."""
    parts = [("gaz", "gaz", color("gaz")), ("co2", "CO₂", CO2), ("vom", "VOM", VOM)]
    plants = list(costs.index)
    for y, plant in enumerate(reversed(plants)):
        left = 0.0
        for col, name, c in parts:
            v = costs.loc[plant, col]
            ax.barh(y, v, left=left, height=0.55, color=c, ec="white", lw=1.5)
            if v > 8:
                ax.text(left + v / 2, y, f"{name}\n{number(v)}", ha="center", va="center",
                        color="white", fontsize=11, fontweight="bold")  # fmt: skip
            elif y == len(plants) - 1:
                ax.text(left + v / 2, y + 0.33, f"{name} : {number(v, 1)}", ha="center",
                        va="bottom", color=TEXT_LIGHT, fontsize=11)  # fmt: skip
            left += v
        ax.text(left + 2, y, f"{number(left)} €/MWh", ha="left", va="center", color=TEXT,
                fontsize=13, fontweight="bold")  # fmt: skip
    ax.set_yticks(range(len(plants)), [label(p) for p in reversed(plants)], fontsize=13)
    _axes(ax, costs["total"].max() * 1.35, xlabel="")
    ax.tick_params(axis="y", length=0, colors=TEXT)
    ax.set_xticks([])
    ax.spines[["left", "bottom"]].set_visible(False)
    ax.set_ylim(-0.6, len(plants) - 0.4)


def _steps(ax: plt.Axes, ordered: pd.DataFrame, labels: bool = True) -> None:
    for row in ordered.itertuples():
        c = color(row.filiere)
        ax.fill_between([row.debut, row.fin], 0, row.cout_variable, color=c, alpha=0.3, lw=0)
        ax.hlines(row.cout_variable, row.debut, row.fin, color=c, lw=4)
        if labels:
            narrow = row.capacite < 0.2 * ordered["fin"].iloc[-1]
            x, ha = (row.fin, "right") if narrow else ((row.debut + row.fin) / 2, "center")
            if row.debut == 0:  # premier palier : collé à l'axe
                x, ha = 0.5, "left"
            ax.text(x, row.cout_variable + 4, label(row.filiere), ha=ha, va="bottom", color=_shade(c, -0.3), fontsize=12,
                    fontweight="bold")  # fmt: skip
    ax.vlines(ordered["fin"].iloc[:-1], ordered["cout_variable"].iloc[:-1],
              ordered["cout_variable"].iloc[1:], color=TEXT_LIGHT, lw=1)  # fmt: skip


def supply_curve(ax: plt.Axes, fleet: pd.DataFrame) -> None:
    """Merit order : filières classées par coût variable croissant, en paliers."""
    ordered = merit_order(fleet)
    _steps(ax, ordered)
    cap = ordered["fin"].iloc[-1]
    top = ordered["cout_variable"].max() * 1.3
    ax.vlines(cap, 0, top, color=TEXT, lw=1.5, ls=(0, (4, 3)))
    ax.text(cap + 1, top, "capacité\ndu parc", ha="left", va="top", color=TEXT, fontsize=11)
    ax.set_xticks(ordered["fin"], [number(x) for x in ordered["fin"]])
    ax.set_yticks(ordered["cout_variable"], [number(y) for y in ordered["cout_variable"]])
    ax.set_ylabel("Coût variable (€/MWh)", color=TEXT, fontsize=12)
    _axes(ax, cap * 1.2)
    ax.set_ylim(0, top * 1.02)


@dataclass
class Equilibrium:
    """Résultat de `equilibrium` : quantité (GW), prix (€/MWh), énergie non distribuée (GW).

    `scarcity` : prix fixé par la demande (VOLL ou usages flexibles), pas par une filière.
    """

    quantity: float
    price: float
    unserved: float
    marginal: str | None
    scarcity: bool


def equilibrium(
    ax: plt.Axes,
    fleet: pd.DataFrame,
    demand: pd.Series,
    surplus: bool = False,
    voll_label: str = "VOLL",
) -> Equilibrium:
    """Offre en paliers et demande à la VOLL, prix d'équilibre, surplus éventuels.

    La VOLL est hors d'échelle : l'axe des prix est interrompu au-dessus du
    coût de la filière la plus chère, et la demande est stylisée entre la VOLL
    et les prix visibles. Les prix renvoyés ne sont fiables que lorsqu'une
    filière est marginale ; sinon (`scarcity`), le prix est celui de la demande.
    """
    ordered = merit_order(fleet)
    cap = float(ordered["fin"].iloc[-1])
    cmax = float(ordered["cout_variable"].max())
    y_break = cmax * 1.3  # haut de l'échelle réelle
    voll = cmax * 1.75  # position (stylisée) de la VOLL sur l'axe interrompu
    q_rigid, width = float(demand["non_flexible"]), float(demand["flexible"])

    def demand_price(q):
        return np.clip(voll * (1 - (np.asarray(q, float) - q_rigid) / width), 0, voll)

    # Équilibre : première filière dont le coût dépasse le prix demandé à sa borne droite.
    eq = None
    for row in ordered.itertuples():
        qd = q_rigid + width * (1 - row.cout_variable / voll)
        if row.debut <= qd <= row.fin:
            eq = Equilibrium(qd, row.cout_variable, 0.0, row.filiere, False)
            break
        if qd < row.debut:  # demande coupée sur la verticale entre deux paliers
            p = float(demand_price(row.debut))
            eq = Equilibrium(row.debut, p, 0.0, None, True)
            break
    if eq is None:  # la demande dépasse le parc
        eq = Equilibrium(cap, float(demand_price(cap)), max(q_rigid - cap, 0.0), None, True)

    xmax = max(cap, q_rigid + width) * 1.06
    _axes(ax, xmax)
    ax.set_ylim(0, voll * 1.12)
    if surplus:
        q = np.linspace(0, eq.quantity, 400)
        ax.fill_between(q, eq.price, demand_price(q), color=CONSUMER, lw=0)
        for row in ordered.itertuples():
            x0, x1 = row.debut, min(row.fin, eq.quantity)
            if x1 > x0 and row.cout_variable < eq.price:
                ax.fill_between([x0, x1], row.cout_variable, eq.price, color=PRODUCER, lw=0)
    _steps(ax, ordered, labels=not surplus)

    qd = np.linspace(0, q_rigid + width, 400)
    ax.plot(qd, demand_price(qd), color=DEMAND, lw=3)
    ax.text(q_rigid * 0.04, voll + cmax * 0.05, "demande", color=DEMAND, fontsize=13,
            fontweight="bold", va="bottom")  # fmt: skip

    # Axe interrompu entre l'échelle réelle et la VOLL.
    gap = cmax * 0.08
    ax.axhspan(y_break, y_break + gap, color="white", zorder=4)
    for y in (y_break, y_break + gap):
        ax.plot([-0.012, 0.012], [y - gap * 0.3, y + gap * 0.3], color=TEXT, lw=1.2,
                transform=ax.get_yaxis_transform(), clip_on=False, zorder=6)  # fmt: skip
    ticks = [c for c in ordered["cout_variable"] if c > 0] + [voll]
    names = [number(c) for c in ticks[:-1]] + [voll_label]
    ax.set_yticks(ticks, names)
    ax.get_yticklabels()[-1].set_color(DEMAND)
    ax.set_ylabel("€/MWh", color=TEXT, fontsize=12)
    ax.set_xticks([])

    # Point d'équilibre et prix.
    ax.vlines(eq.quantity, 0, eq.price, color=TEXT_LIGHT, lw=1.2, ls=":", zorder=5)
    ax.hlines(eq.price, 0, eq.quantity, color=TEXT, lw=1.2, ls="--", zorder=5)
    ax.plot(eq.quantity, eq.price, "o", color=TEXT, ms=8, zorder=7)
    ax.text(eq.quantity, -0.02, "q*", ha="center", va="top", color=TEXT, fontsize=13,
            transform=ax.get_xaxis_transform())  # fmt: skip
    if eq.price < y_break:
        ax.text(xmax * 0.01, eq.price + cmax * 0.03, "p*", color=TEXT, fontsize=14,
                fontweight="bold", zorder=7)  # fmt: skip
    else:
        ax.text(eq.quantity - xmax * 0.015, eq.price + cmax * 0.04, f"p* = {voll_label}",
                ha="right", color=TEXT, fontsize=14, fontweight="bold", zorder=7)  # fmt: skip
    if surplus:
        ax.text(eq.quantity * 0.35, (eq.price + y_break) / 2, "surplus des\nconsommateurs",
                ha="center", va="center", color=_shade(DEMAND, -0.35), fontsize=12,
                zorder=6, bbox={"fc": CONSUMER, "ec": "none", "pad": 1})  # fmt: skip
        ax.text(eq.quantity * 0.6, eq.price * 0.55, "surplus des\nproducteurs",
                ha="center", va="center", color=_shade(ACCENTS["production"], -0.45),
                fontsize=12)  # fmt: skip
    if eq.unserved > 0:
        ax.vlines(cap, ordered["cout_variable"].iloc[-1], voll * 1.08, color=TEXT, lw=1.5,
                  ls=(0, (4, 3)))  # fmt: skip
        y = voll * 0.93
        ax.annotate("", xy=(q_rigid, y), xytext=(cap, y),
                    arrowprops={"arrowstyle": "<->", "color": ALERT, "lw": 2})  # fmt: skip
        ax.text((cap + q_rigid) / 2, y - cmax * 0.06, "énergie non\ndistribuée", ha="center",
                va="top", color=ALERT, fontsize=12, fontweight="bold", zorder=6,
                bbox={"fc": "white", "ec": "none", "pad": 1})  # fmt: skip
    return eq


# ---------------------------------------------------------------------------
# Prix du gaz et du CO₂, centrale au gaz, valeur d'usage


def load_gas_prices() -> pd.Series:
    """Prix mensuel du gaz au TTF (€/MWh), indexé par mois (Timestamp)."""
    gas = pd.read_csv(DATA_DIR / "couts" / "prix-gaz-ttf-mensuel.csv")
    return gas.set_index(pd.to_datetime(gas["mois"]))["gaz_eur_mwh"]


def load_annual_prices() -> pd.DataFrame:
    """Prix annuels (CRE) : gaz au PEG, CO₂ moyen, minimum et maximum, indexés par année."""
    return pd.read_csv(DATA_DIR / "couts" / "prix-gaz-co2.csv").set_index("annee")


def fuel_prices(fig: plt.Figure, gas: pd.Series, annual: pd.DataFrame, start: str = "2019") -> None:
    """Prix mensuel du gaz (TTF) et prix annuel du CO₂ (moyenne, minimum et maximum)."""
    ax_gas, ax_co2 = fig.subplots(1, 2, gridspec_kw={"width_ratios": [2.1, 1], "wspace": 0.25})
    gas = gas[gas.index >= start]
    c = color("gaz")
    ax_gas.fill_between(gas.index, 0, gas.to_numpy(), color=c, alpha=0.15, lw=0)
    ax_gas.plot(gas.index, gas.to_numpy(), color=c, lw=2.5)
    peak = gas.idxmax()
    ax_gas.annotate(f"{number(gas.max())} €/MWh\n({peak.year})", xy=(peak, gas.max()),
                    xytext=(-12, -6), textcoords="offset points", ha="right", va="top",
                    color=TEXT, fontsize=11)  # fmt: skip
    ax_gas.set_title("Gaz au TTF (€/MWh PCS, moyenne mensuelle)", color=TEXT, fontsize=13)
    ax_gas.set_ylim(0, gas.max() * 1.1)
    ax_gas.grid(axis="y", alpha=0.3)
    ax_gas.grid(axis="x", visible=False)

    co2 = annual.dropna(subset=["co2_eur_t"])
    years = co2.index.astype(int)
    ax_co2.bar(years, co2["co2_eur_t"], width=0.6, color=CO2, alpha=0.85)
    span = co2.dropna(subset=["co2_min", "co2_max"])
    ax_co2.vlines(span.index, span["co2_min"], span["co2_max"], color=TEXT, lw=1.5)
    ax_co2.plot(span.index, span["co2_min"], "_", color=TEXT, ms=10)
    ax_co2.plot(co2.index, co2["co2_max"], "_", color=TEXT, ms=10)
    for y, v in co2["co2_eur_t"].items():
        ax_co2.text(y, v / 2, number(v), ha="center", va="center", color="white", fontsize=11,
                    fontweight="bold")  # fmt: skip
    ax_co2.set_xticks(years, [str(y) for y in years])
    ax_co2.set_title("Quota de CO₂ (€/t, moyenne annuelle\net extrêmes)", color=TEXT,
                     fontsize=13)  # fmt: skip
    ax_co2.set_ylim(0, co2["co2_max"].max() * 1.12)
    ax_co2.grid(axis="y", alpha=0.3)
    ax_co2.grid(axis="x", visible=False)
    for ax in (ax_gas, ax_co2):
        ax.tick_params(colors=TEXT_LIGHT, labelsize=11)
        for side in ("left", "bottom"):
            ax.spines[side].set_color(TEXT_LIGHT)


def _node(ax, x, y, w, h, text, fc, tc="white", size=13):
    ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, fc=fc, ec="none",
                                boxstyle="round,pad=0,rounding_size=0.12", zorder=2))  # fmt: skip
    ax.text(x, y, text, ha="center", va="center", color=tc, fontsize=size, fontweight="bold",
            zorder=3, linespacing=1.3)  # fmt: skip


def _flow(ax, start, end, c, lw=2.5):
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=18, color=c,
                                 lw=lw, shrinkA=0, shrinkB=0, zorder=1))  # fmt: skip


def gas_plant_flow(ax: plt.Axes, plant: pd.Series, plant_label: str = "CCG") -> None:
    """Bilan d'une centrale au gaz pour 1 MWh PCS de gaz : électricité produite et CO₂ émis.

    `plant` : une ligne de `load_gas_plants` (rendements, facteur d'émission PCS).
    """
    ax.set_xlim(-0.2, 10.2)
    ax.set_ylim(0, 4.8)
    ax.axis("off")
    eta, e = float(plant["rendement"]), float(plant["facteur_emission"])
    gas_c, elec_c = color("gaz"), ACCENTS["transport"]
    y = 2.1
    eta_pci = float(plant["rendement_pci"])
    _node(ax, 1.3, y, 2.6, 1.3, "1 MWh PCS\nde gaz", gas_c, size=12)
    _node(
        ax, 5.0, y, 2.8, 2.0, f"{plant_label}\nrendement\n{eta_pci * 100:.0f} % PCI", TEXT, size=12
    )
    _node(ax, 8.7, y, 2.6, 1.3, f"{number(eta, 2)} MWh\nd'électricité", elec_c, size=12)
    _node(ax, 5.0, 4.35, 2.8, 0.75, f"{number(e, 2)} t de CO₂", CO2, size=12)
    _flow(ax, (2.6, y), (3.6, y), gas_c)
    _flow(ax, (6.4, y), (7.4, y), elec_c)
    _flow(ax, (5.0, y + 1.0), (5.0, 3.97), CO2)
    _flow(ax, (5.0, y - 1.0), (5.0, 0.55), TEXT_LIGHT, lw=1.8)
    ax.text(5.0, 0.3, f"pertes : {number(1 - eta, 2)} MWh de chaleur", ha="center", va="center",
            color=TEXT_LIGHT, fontsize=12, style="italic")  # fmt: skip
