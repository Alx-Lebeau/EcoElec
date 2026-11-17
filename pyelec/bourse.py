"""Bourse de l'électricité : carnet d'ordres d'un portefeuille, enchère J-1.

Portefeuille illustratif (`data/exemple/portefeuille-bourse.csv`) : des actifs de
production et, pour un fournisseur, la consommation de ses clients. Coûts
variables : 0 pour l'éolien, calculé par `pyelec.dispatch` pour le gaz.

- `load_portfolio` : actifs (puissance, coût variable) et demande des clients ;
- `order_book` : ordres d'achat et de vente qui reproduisent la position nette
  du portefeuille quand chaque actif est offert à son coût variable ;
- `order_book_html` : le même carnet en tableau HTML (cellule `output: asis`) ;
- `portfolio_offer` : coût variable du portefeuille en paliers, et la demande ;
- `load_orders`, `clear`, `exchange_overview` : ordres élémentaires, courbes
  agrégées et prix de l'enchère.
"""

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import FancyBboxPatch

from pyelec.dispatch import gas_plant_costs, number
from pyelec.palette import color
from pyelec.paths import DATA_DIR
from pyelec.schema import ACCENTS, TEXT, TEXT_LIGHT, _shade

BUY = ACCENTS["consommation"]
SELL = ACCENTS["production"]
FIGSIZE = (5.2, 3.8)


def load_portfolio() -> tuple[pd.DataFrame, float]:
    """Actifs du portefeuille (`element`, `filiere`, `puissance` en MW, `cout_variable`)
    classés par coût croissant, et demande des clients (MW)."""
    data = pd.read_csv(DATA_DIR / "exemple" / "portefeuille-bourse.csv")
    demand = float(data.loc[data["filiere"] == "demande", "puissance"].sum())
    assets = data[data["filiere"] != "demande"].copy()
    gas = gas_plant_costs()["total"]
    costs = {"eolien": 0.0, "solaire": 0.0, **gas.to_dict()}
    assets["cout_variable"] = assets["filiere"].map(costs)
    assets = assets.sort_values("cout_variable", kind="stable").reset_index(drop=True)
    return assets, demand


def order_book(assets: pd.DataFrame, demand: float = 0.0) -> pd.DataFrame:
    """Carnet d'ordres d'un portefeuille offert à son coût variable.

    Chaque actif couvre d'abord la demande des clients : cette part devient un ordre
    d'achat à son coût variable (acheter si le prix est plus bas que produire). Le
    reste devient un ordre de vente au même prix. La demande au-delà de la capacité
    serait achetée sans limite de prix (non traitée ici). Colonnes : `sens`
    (« achat » ou « vente »), `quantite` (MW), `prix` (€/MWh, prix limite).
    """
    orders = []
    before = 0.0
    for row in assets.itertuples():
        after = before + row.puissance
        covered = max(0.0, min(after, demand) - before)
        surplus = after - max(demand, before)
        if covered > 0:
            orders.append(("achat", covered, row.cout_variable))
        if surplus > 0:
            orders.append(("vente", surplus, row.cout_variable))
        before = after
    book = pd.DataFrame(orders, columns=["sens", "quantite", "prix"])
    # Achats : du prix limite le plus élevé au plus bas, comme un carnet affiché.
    buy = book[book["sens"] == "achat"].sort_values("prix", ascending=False)
    sell = book[book["sens"] == "vente"].sort_values("prix")
    return pd.concat([buy, sell], ignore_index=True)


def order_book_html(book: pd.DataFrame | None = None, rows: int = 2) -> str:
    """Carnet d'ordres en tableau HTML (classe `carnet`), achats et ventes côte à côte.

    Sans `book`, un carnet vide de `rows` lignes, à remplir avec le public. À
    afficher depuis une cellule `#| output: asis`.
    """
    buy = [] if book is None else book[book["sens"] == "achat"].to_dict("records")
    sell = [] if book is None else book[book["sens"] == "vente"].to_dict("records")
    n = max(rows, len(buy), len(sell))

    def cells(orders, i, side):
        if i < len(orders):
            o = orders[i]
            return f'<td class="{side}">{number(o["quantite"])}</td><td class="{side}">{number(o["prix"])}</td>'
        return f'<td class="{side}"></td><td class="{side}"></td>'

    body = "".join(f"<tr>{cells(buy, i, 'achat')}{cells(sell, i, 'vente')}</tr>" for i in range(n))
    return (
        '<table class="carnet"><thead>'
        '<tr><th colspan="2" class="achat">Achat</th><th colspan="2" class="vente">Vente</th></tr>'
        '<tr><th class="achat">volume<br>(MW)</th><th class="achat">prix max<br>(€/MWh)</th>'
        '<th class="vente">volume<br>(MW)</th><th class="vente">prix min<br>(€/MWh)</th></tr>'
        f"</thead><tbody>{body}</tbody></table>"
    )


def portfolio_offer(
    ax: plt.Axes, assets: pd.DataFrame, demand: float | None = None, answer: bool = False
) -> None:
    """Coût variable du portefeuille en paliers, et la demande des clients s'il y en a.

    Avec `answer`, les flèches de la réponse : à gauche de la demande la part à acheter,
    à droite la part à vendre (à réserver à la slide qui donne la réponse).
    """
    total = float(assets["puissance"].sum())
    top = float(assets["cout_variable"].max()) * 1.9 + 10
    x0 = 0.0
    for row in assets.itertuples():
        c = color(row.filiere)
        ax.fill_between([x0, x0 + row.puissance], 0, row.cout_variable, color=c, alpha=0.3,
                        lw=0)  # fmt: skip
        ax.hlines(row.cout_variable, x0, x0 + row.puissance, color=c, lw=4)
        # Libellé collé à gauche du palier : le centre peut porter la demande.
        y = row.cout_variable / 2 if row.cout_variable > top * 0.2 else row.cout_variable
        ax.text(x0 + total * 0.015, y + top * 0.02, row.element, ha="left",
                va="center" if y != row.cout_variable else "bottom",
                color=_shade(c, -0.35), fontsize=12, fontweight="bold")  # fmt: skip
        x0 += row.puissance
    costs = assets["cout_variable"].to_numpy()
    ends = assets["puissance"].cumsum().to_numpy()
    ax.vlines(ends[:-1], costs[:-1], costs[1:], color=TEXT_LIGHT, lw=1)
    ax.set_xlim(0, total * 1.12)
    ax.set_ylim(0, top)
    ax.set_xticks(ends, [number(e) for e in ends])
    ax.set_yticks(costs, [number(c) for c in costs])
    ax.set_xlabel("Puissance (MW)", color=TEXT, fontsize=12)
    ax.set_ylabel("Coût variable (€/MWh)", color=TEXT, fontsize=12)
    ax.grid(False)
    ax.tick_params(colors=TEXT_LIGHT, labelsize=11)
    if demand:
        ax.axvline(demand, color=BUY, lw=2.5)
        ax.text(demand, top * 0.99, f"demande des\nclients : {number(demand)} MW",
                ha="center", va="top", color=BUY, fontsize=11, fontweight="bold",
                bbox={"fc": "white", "ec": "none", "pad": 1})  # fmt: skip
    if demand and answer:
        y = top * 0.75
        arrow = {"arrowstyle": "<|-", "lw": 1.8, "mutation_scale": 14}
        ax.annotate("", xy=(demand, y), xytext=(demand * 0.25, y),
                    arrowprops={**arrow, "color": BUY})  # fmt: skip
        ax.text(demand * 0.6, y + top * 0.02, "à acheter\nsi moins cher", ha="center",
                va="bottom", color=BUY, fontsize=11)  # fmt: skip
        ax.annotate("", xy=(demand, y), xytext=(total, y),
                    arrowprops={**arrow, "color": SELL})  # fmt: skip
        ax.text((demand + total) / 2, y + top * 0.02, "à vendre\nsi plus cher",
                ha="center", va="bottom", color=SELL, fontsize=11)  # fmt: skip


def load_orders() -> pd.DataFrame:
    """Ordres illustratifs d'une enchère : `ordre`, `sens`, `volume` (MW), `prix_limite`."""
    return pd.read_csv(DATA_DIR / "exemple" / "ordres-bourse.csv")


def clear(orders: pd.DataFrame) -> tuple[float, float]:
    """Prix et volume de l'enchère : plus bas prix limite où la vente couvre l'achat.

    À un prix p, sont servis les achats de prix maximal au moins p et les ventes de
    prix minimal au plus p. Volume échangé : l'achat servi à ce prix.
    """
    buy = orders[orders["sens"] == "achat"]
    sell = orders[orders["sens"] == "vente"]
    for p in sorted(orders["prix_limite"].unique()):
        demand = buy.loc[buy["prix_limite"] >= p, "volume"].sum()
        supply = sell.loc[sell["prix_limite"] <= p, "volume"].sum()
        if supply >= demand:
            return float(p), float(demand)
    raise ValueError("pas d'équilibre : la vente ne couvre jamais l'achat")


def _order_card(ax, x, y, w, h, row, c):
    ax.add_patch(FancyBboxPatch((x, y), w, h, fc=_shade(c, 0.88), ec=c, lw=1.5,
                                boxstyle="round,pad=0,rounding_size=0.1"))  # fmt: skip
    verb, limit = ("achète", "max") if row.sens == "achat" else ("vend", "min")
    ax.text(x + 0.15, y + h / 2, row.ordre, ha="left", va="center", color=_shade(c, -0.35),
            fontsize=12, fontweight="bold")  # fmt: skip
    ax.text(x + 0.75, y + h * 0.68, f"{verb} {number(row.volume)} MW", ha="left",
            va="center", color=TEXT, fontsize=11)  # fmt: skip
    ax.text(x + 0.75, y + h * 0.3, f"prix {limit} {number(row.prix_limite)} €/MWh", ha="left",
            va="center", color=TEXT, fontsize=11)  # fmt: skip


def _aggregate(ax, orders, c, descending):
    """Courbe agrégée d'un côté du carnet ; renvoie les milieux de paliers par ordre."""
    side = orders.sort_values("prix_limite", ascending=not descending)
    x0, centers = 0.0, {}
    for row in side.itertuples():
        x1 = x0 + row.volume
        ax.hlines(row.prix_limite, x0, x1, color=c, lw=3)
        centers[row.ordre] = ((x0 + x1) / 2, row.prix_limite)
        x0 = x1
    ends = side["volume"].cumsum().to_numpy()[:-1]
    prices = side["prix_limite"].to_numpy()
    ax.vlines(ends, prices[:-1], prices[1:], color=c, lw=3)
    return centers


def exchange_overview(fig: plt.Figure, orders: pd.DataFrame) -> tuple[float, float]:
    """Des ordres élémentaires aux deux courbes de l'enchère, et leur croisement.

    À gauche, chaque ordre : volume et prix limite (maximal à l'achat, minimal à la
    vente). À droite, les mêmes ordres classés : achats par prix décroissant, ventes
    par prix croissant. Renvoie le prix et le volume de l'enchère.
    """
    left, right = fig.subplots(1, 2, gridspec_kw={"width_ratios": [1.3, 1], "wspace": 0.25})
    buy = orders[orders["sens"] == "achat"]
    sell = orders[orders["sens"] == "vente"]
    n = max(len(buy), len(sell))
    left.set_xlim(0, 7.0)
    left.set_ylim(0, n + 0.6)
    left.axis("off")
    for col, (side, c, title) in enumerate(((buy, BUY, "ordres d'achat"),
                                             (sell, SELL, "ordres de vente"))):  # fmt: skip
        x = col * 3.6
        left.text(x + 1.65, n + 0.35, title, ha="center", va="center", color=c, fontsize=12,
                  fontweight="bold")  # fmt: skip
        for k, row in enumerate(side.itertuples()):
            _order_card(left, x, n - 1 - k + 0.1, 3.3, 0.8, row, c)

    price, volume = clear(orders)
    centers = {**_aggregate(right, buy, BUY, True), **_aggregate(right, sell, SELL, False)}
    for name, (x, y) in centers.items():
        c = BUY if name.startswith("A") else SELL
        right.text(x, y + 6, name, ha="center", va="bottom", color=_shade(c, -0.3),
                   fontsize=11, fontweight="bold")  # fmt: skip
    right.hlines(price, 0, volume, color=TEXT, lw=1.2, ls="--")
    right.vlines(volume, 0, price, color=TEXT_LIGHT, lw=1.2, ls=":")
    right.plot(volume, price, "o", color=TEXT, ms=8, zorder=5)
    total = max(buy["volume"].sum(), sell["volume"].sum())
    right.text(total * 1.02, price, f"prix : {number(price)} €/MWh", ha="left", va="center",
               color=TEXT, fontsize=12, fontweight="bold")  # fmt: skip
    right.set_xlim(0, total * 1.5)
    right.set_ylim(-5, orders["prix_limite"].max() * 1.15)
    right.set_xticks([volume], [f"{number(volume)} MW\néchangés"])
    right.set_yticks(sorted(orders["prix_limite"].unique()))
    right.set_xlabel("MW", color=TEXT, loc="right")
    right.set_ylabel("€/MWh", color=TEXT)
    right.grid(False)
    right.tick_params(colors=TEXT_LIGHT, labelsize=10)
    return price, volume
