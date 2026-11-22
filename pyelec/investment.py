"""Équilibre de long terme : annuités, LCOE, *screening curves* et monotone de charge.

Données :

- `data/exemple/parc-long-terme.csv` : options d'investissement illustratives
  (coût d'investissement en €/kW, durée de vie, taux d'actualisation, coût variable
  en €/MWh des filières sans combustible acheté) ;
- `data/couts/` : coût variable des CCG et des TAC (`pyelec.dispatch.gas_plant_costs`) ;
- `data/couts/securite-approvisionnement.csv` : VOLL et critère de sécurité
  d'approvisionnement (RTE, CRE) ;
- `data/exemple/semaine-vent.csv` : prix et production éolienne d'une semaine type ;
- `data/couts/eolien-terrestre.csv` : coûts de l'éolien terrestre (CRE) ;
- `data/consommation/courbe-charge-2025.csv` : consommation horaire de la France.

Fonctions :

- `annuity_factor`, `load_options` : annualisation de l'investissement, coût fixe
  annuel (€/MW/an) et coût variable de chaque filière ;
- `load_reliability`, `load_voll`, `with_load_shedding` : le délestage comme moyen fictif (coût fixe nul,
  coût variable égal à la VOLL) ;
- `capture_price_example` : prix moyen, prix capté et LCOE d'une centrale de pointe\n  sur une journée type ;
- `total_cost`, `lcoe` : coût total d'un MW et coût moyen du MWh selon la durée de
  fonctionnement ;
- `envelope` : filières retenues et durées d'équilibre (enveloppe inférieure) ;
- `load_curve`, `duration_curve` : courbe de charge horaire et monotone ;
- `optimal_fleet` : parc optimal par la méthode des *screening curves* ;
- figures : `annuity_schedule`, `screening_curves`, `lcoe_curves`, `lcoe_discount`,
  `shedding_zoom`, `chronological_load`, `load_duration`, `screening_method`,
  `capture_price`, `price_duration`, `rent_of`, `investment_loop`.

Usage :

    from pyelec import investment, style
    style.use()
    options = investment.load_options()
    ldc = investment.duration_curve(investment.load_curve())
    fig = plt.figure(figsize=(6.2, 5.4))
    investment.screening_method(fig, options, ldc)
"""

from dataclasses import dataclass

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

from pyelec.dispatch import gas_plant_costs, number
from pyelec.palette import color, label
from pyelec.paths import DATA_DIR
from pyelec.schema import ACCENTS, TEXT, TEXT_LIGHT, _shade

HOURS = 8760
DEMAND = ACCENTS["consommation"]
INTEREST = "#94a3b8"
ENVELOPE = "#eef1f5"  # aire sous l'enveloppe inférieure


def _num(x: float, digits: int = 0) -> str:
    """Nombre pour les figures : espace insécable ordinaire pour les milliers.

    L'espace fine (U+202F) ne fait qu'un pixel en gras dans les figures : illisible.
    """
    return str(number(x, digits)).replace("\u202f", "\u00a0")


# ---------------------------------------------------------------------------
# Calculs


def annuity_factor(rate: float, lifetime: float) -> float:
    """Facteur d'annuité : r / (1 - (1 + r)^-n). Vaut 1/n si le taux est nul."""
    if rate == 0:
        return 1 / lifetime
    return rate / (1 - (1 + rate) ** -lifetime)


def load_options(year: int | None = None, rate: float | None = None) -> pd.DataFrame:
    """Options d'investissement, indexées par filière (ordre du fichier).

    Colonnes : `investissement` (€/kW), `exploitation_fixe` (€/kW/an), `duree_vie`
    (ans), `taux_actualisation`, `annuite` (€/MW/an), `cout_fixe` (€/MW/an : annuité
    et coûts fixes d'exploitation), `cout_variable` (€/MWh). Coût variable des CCG et
    des TAC calculé avec les prix du gaz et du CO₂ de `year` (par défaut la dernière
    année). `rate` remplace le taux du fichier.
    """
    options = pd.read_csv(DATA_DIR / "exemple" / "parc-long-terme.csv").set_index("filiere")
    if rate is not None:
        options["taux_actualisation"] = rate
    gas = gas_plant_costs(year)
    options["cout_variable"] = options["cout_variable"].fillna(gas["total"])
    factors = [
        annuity_factor(r, n)
        for r, n in zip(options["taux_actualisation"], options["duree_vie"], strict=True)
    ]
    options["annuite"] = options["investissement"] * 1000 * np.array(factors)
    options["cout_fixe"] = options["annuite"] + options["exploitation_fixe"] * 1000
    options.attrs["annee"] = gas.attrs["annee"]
    return options


def load_reliability() -> pd.Series:
    """VOLL retenue en France (`voll`, €/MWh) et critères de sécurité d'approvisionnement
    (`critere_delestage`, `critere_defaillance`, heures par an en espérance)."""
    data = pd.read_csv(DATA_DIR / "couts" / "securite-approvisionnement.csv")
    return data.set_index("grandeur")["valeur"].astype(float)


def load_voll() -> float:
    """Valeur de l'énergie non distribuée retenue en France (€/MWh)."""
    return float(load_reliability()["voll"])


def with_load_shedding(options: pd.DataFrame, hours: float | None = None) -> pd.DataFrame:
    """Options complétées du délestage : moyen fictif, coût fixe nul, coût variable = VOLL.

    Sans `hours`, VOLL retenue en France. Avec `hours`, VOLL stylisée, choisie pour que
    le délestage et la filière au coût fixe le plus bas coûtent autant à `hours` heures.
    La VOLL retenue est dans `attrs["voll"]`.
    """
    if hours is None:
        voll = load_voll()
    else:
        peak = options.loc[options["cout_fixe"].idxmin()]
        voll = float(peak.cout_fixe / hours + peak.cout_variable)
    shedding = pd.DataFrame({"cout_fixe": [0.0], "cout_variable": [voll]},
                            index=pd.Index(["delestage"], name="filiere"))  # fmt: skip
    extended = pd.concat([shedding, options])
    extended.attrs = {**options.attrs, "voll": voll}
    return extended


def load_onshore_wind() -> pd.Series:
    """Éolien terrestre (CRE) : `investissement` (€/kW), `productible` (heures
    équivalentes pleine puissance par an), `prix_moyen_laureats` (€/MWh)."""
    data = pd.read_csv(DATA_DIR / "couts" / "eolien-terrestre.csv")
    return data.set_index("grandeur")["valeur"].astype(float)


@dataclass
class CaptureExample:
    """Prix moyen, prix capté et LCOE d'un parc éolien sur une semaine type.

    `table` : `jour`, `prix` (€/MWh), `facteur_charge_eolien` ; `lcoe` : prix moyen des
    lauréats des appels d'offres, prix de vente qui rend les projets rentables.
    """

    table: pd.DataFrame
    mean_price: float
    captured_price: float
    load_factor: float
    lcoe: float


def capture_price_example() -> CaptureExample:
    """Semaine illustrative : le vent fait baisser les prix des jours où il souffle.

    Prix moyen : moyenne simple des jours. Prix capté : moyenne pondérée par la
    production éolienne. LCOE : prix moyen des lauréats des appels d'offres (CRE).
    """
    table = pd.read_csv(DATA_DIR / "exemple" / "semaine-vent.csv")
    w = table["facteur_charge_eolien"]
    return CaptureExample(
        table=table,
        mean_price=float(table["prix"].mean()),
        captured_price=float((table["prix"] * w).sum() / w.sum()),
        load_factor=float(w.mean()),
        lcoe=float(load_onshore_wind()["prix_moyen_laureats"]),
    )


def total_cost(options: pd.DataFrame, hours) -> pd.DataFrame:
    """Coût total annuel d'un MW (€/MW/an) qui fonctionne `hours` heures : CF + CV × h."""
    h = np.atleast_1d(np.asarray(hours, float))
    return pd.DataFrame(
        {f: row.cout_fixe + row.cout_variable * h for f, row in options.iterrows()}, index=h
    )


def lcoe(options: pd.DataFrame, hours) -> pd.DataFrame:
    """Coût moyen du MWh (€/MWh) d'un MW qui fonctionne `hours` heures : CF / h + CV."""
    h = np.atleast_1d(np.asarray(hours, float))
    return total_cost(options, h).div(h, axis=0)


@dataclass
class Segment:
    """Filière la moins chère entre `start` et `end` heures de fonctionnement par an."""

    filiere: str
    start: float
    end: float


def envelope(options: pd.DataFrame, horizon: float = HOURS) -> list[Segment]:
    """Enveloppe inférieure des coûts totaux : filières retenues et durées d'équilibre.

    De 0 heure (coût fixe le plus bas) à `horizon`, on passe d'une filière à la
    suivante au croisement le plus proche avec une filière au coût variable plus bas.
    Les filières jamais les moins chères n'apparaissent pas.
    """
    current = options.sort_values(["cout_fixe", "cout_variable"]).index[0]
    start, segments = 0.0, []
    while True:
        row = options.loc[current]
        cheaper = options[options["cout_variable"] < row.cout_variable]
        crossings = (cheaper["cout_fixe"] - row.cout_fixe) / (
            row.cout_variable - cheaper["cout_variable"]
        )
        crossings = crossings[crossings > start]
        if crossings.empty or crossings.min() >= horizon:
            segments.append(Segment(current, start, horizon))
            return segments
        nxt = crossings.idxmin()
        segments.append(Segment(current, start, float(crossings[nxt])))
        current, start = nxt, float(crossings[nxt])


def load_curve() -> pd.Series:
    """Consommation horaire de la France en 2025 (GW), indexée par heure locale."""
    load = pd.read_csv(DATA_DIR / "consommation" / "courbe-charge-2025.csv")
    return load.set_index(pd.to_datetime(load["heure_locale"]))["consommation_gw"]


def duration_curve(load: pd.Series) -> np.ndarray:
    """Monotone de charge : consommations horaires classées par ordre décroissant."""
    return np.sort(np.asarray(load, float))[::-1]


def level(ldc: np.ndarray, hours: float) -> float:
    """Puissance dépassée pendant `hours` heures (interpolée sur la monotone)."""
    x = np.arange(len(ldc)) + 0.5
    return float(np.interp(hours, x, ldc))


def optimal_fleet(options: pd.DataFrame, ldc: np.ndarray) -> pd.DataFrame:
    """Parc optimal par les *screening curves*, indexé par filière retenue.

    Une tranche de consommation présente pendant h heures revient à la filière la
    moins chère pour h heures. Colonnes : `debut`, `fin` (durées d'équilibre, h),
    `bas`, `haut` (bornes de la tranche, GW), `capacite` (GW), `energie` (TWh),
    `heures` (durée de fonctionnement équivalente à pleine puissance, h).
    """
    segments = envelope(options, horizon=len(ldc))
    rows = []
    for s in segments:
        high = level(ldc, s.start) if s.start > 0 else float(ldc[0])
        low = level(ldc, s.end) if s.end < len(ldc) else 0.0
        energy = float(np.clip(ldc, low, high).sum() - low * len(ldc)) / 1000
        capacity = high - low
        rows.append(
            {
                "filiere": s.filiere,
                "debut": s.start,
                "fin": s.end,
                "bas": low,
                "haut": high,
                "capacite": capacity,
                "energie": energy,
                "heures": energy * 1000 / capacity if capacity > 0 else 0.0,
            }
        )
    return pd.DataFrame(rows).set_index("filiere")


# ---------------------------------------------------------------------------
# Figures


def _axes(ax: plt.Axes, xlabel: str | None, ylabel: str | None) -> None:
    ax.grid(axis="y", alpha=0.3)
    ax.grid(axis="x", visible=False)
    if xlabel:
        ax.set_xlabel(xlabel, color=TEXT, fontsize=12)
    if ylabel:
        ax.set_ylabel(ylabel, color=TEXT, fontsize=12)
    ax.tick_params(colors=TEXT_LIGHT, labelsize=11)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(TEXT)


def _hours_axis(ax: plt.Axes, xlabel: str | None = "Heures de fonctionnement par an") -> None:
    ax.set_xlim(0, HOURS)
    ax.set_xticks(range(0, HOURS + 1, 2000), [_num(x) for x in range(0, HOURS + 1, 2000)])
    _axes(ax, xlabel, None)


def annuity_schedule(ax: plt.Axes, options: pd.DataFrame, filiere: str) -> None:
    """Annuités constantes d'un MW sur sa durée de vie : remboursement et intérêts.

    Comme un crédit au taux d'actualisation : la part des intérêts décroît, celle du
    capital croît, leur somme reste constante.
    """
    row = options.loc[filiere]
    r, n, a = row.taux_actualisation, int(row.duree_vie), row.annuite / 1000
    remaining, interest, principal = row.investissement, [], []
    for _ in range(n):
        i = remaining * r
        interest.append(i)
        principal.append(a - i)
        remaining -= a - i
    years = np.arange(1, n + 1)
    c = color(filiere)
    ax.bar(years, principal, color=c, width=0.8, lw=0, label="remboursement du capital")
    ax.bar(years, interest, bottom=principal, color=INTEREST, width=0.8, lw=0,
           label="rémunération du capital")  # fmt: skip
    ax.axhline(a, color=TEXT, lw=1.2, ls="--")
    ax.text(n + 0.8, a, f"annuité\n{_num(a)} k€/MW/an", ha="left", va="center", color=TEXT,
            fontsize=12, fontweight="bold")  # fmt: skip
    ax.set_xlim(0, n + 1)
    ax.set_ylim(0, a * 1.45)
    ax.legend(loc="upper left", fontsize=11, ncol=2, handlelength=1)
    _axes(ax, "Année", "k€/MW/an")


def screening_curves(
    ax: plt.Axes,
    options: pd.DataFrame,
    lower: bool = False,
    breakeven: bool = False,
    xlabel: str | None = "Heures de fonctionnement par an",
) -> None:
    """Coût total annuel d'un MW selon sa durée de fonctionnement (k€/MW/an).

    `lower` : droites estompées et enveloppe inférieure mise en avant (trait épais,
    aire grisée, nom de la filière la moins chère sous chaque tronçon) ;
    `breakeven` : durées d'équilibre repérées (étiquette omise sous 150 h).
    """
    h = np.array([0, HOURS])
    costs = total_cost(options, h) / 1000
    segments = envelope(options)
    # Échelle calée sur l'enveloppe : les droites les plus pentues sortent par le haut.
    base = options.loc[segments[-1].filiere]
    ymax = (base.cout_fixe + base.cout_variable * HOURS) / 1000 * 1.7
    for f in options.index:
        c = color(f)
        if lower:
            ax.plot(h, costs[f], color=c, lw=1.5, alpha=0.45, ls=(0, (5, 3)))
        else:
            ax.plot(h, costs[f], color=c, lw=3)
        r = options.loc[f]
        if costs[f].iloc[-1] <= ymax * 0.95:
            x, y, va = HOURS * 1.01, costs[f].iloc[-1], "center"
        else:  # étiquette là où la droite sort du cadre
            y = ymax * 0.95
            x, va = (y * 1000 - r.cout_fixe) / r.cout_variable + 150, "top"
        ax.text(x, y, label(f), ha="left", va=va, color=_shade(c, -0.3), fontsize=12,
                fontweight="bold")  # fmt: skip
    if lower:
        x = np.unique(np.concatenate([[0, HOURS], [s.start for s in segments]]))
        y = total_cost(options, x).min(axis=1).to_numpy() / 1000
        ax.fill_between(x, 0, y, color=ENVELOPE, lw=0, zorder=0)
        for s in segments:
            xs = np.array([s.start, s.end])
            r = options.loc[s.filiere]
            c = color(s.filiere)
            ax.plot(xs, (r.cout_fixe + r.cout_variable * xs) / 1000, color=c, lw=6,
                    solid_capstyle="round", zorder=4)  # fmt: skip
            if s.end - s.start > 1200:
                ax.text((s.start + s.end) / 2, ymax * 0.04, label(s.filiere), ha="center",
                        va="bottom", color=_shade(c, -0.35), fontsize=12,
                        fontweight="bold")  # fmt: skip
    if breakeven:
        for s in segments[1:]:
            r = options.loc[s.filiere]
            y = (r.cout_fixe + r.cout_variable * s.start) / 1000
            ax.vlines(s.start, 0, y, color=TEXT, lw=1.2, ls=":")
            ax.plot(s.start, y, "o", color="white", mec=TEXT, mew=2, ms=8, zorder=5)
            if s.start >= 150:
                ax.text(s.start, ymax, f"{_num(s.start)} h", ha="center", va="bottom",
                        color=TEXT, fontsize=12, fontweight="bold")  # fmt: skip
    ax.set_ylim(0, ymax)
    _hours_axis(ax, xlabel)
    ax.set_ylabel("Coût total (k€/MW/an)", color=TEXT, fontsize=12)


def shedding_zoom(ax: plt.Axes, options: pd.DataFrame, factor: float = 3.0) -> None:
    """Coût total sur les premières heures : la droite du délestage y devient lisible.

    Fenêtre de 0 à `factor` fois la durée d'équilibre entre le délestage et la
    première filière construite. Le nucléaire, hors d'échelle, n'apparaît pas.
    """
    segments = envelope(options)
    cut = next(s.end for s in segments if s.filiere == "delestage")
    hmax = cut * factor
    h = np.array([0, hmax])
    costs = total_cost(options, h) / 1000
    nxt = options.loc[segments[1].filiere]  # première filière construite
    ymax = (nxt.cout_fixe + nxt.cout_variable * hmax) / 1000 * 2.2
    for f in options.index:
        ax.plot(h, costs[f], color=color(f), lw=3)
        y = costs[f].iloc[-1]
        if y < ymax:
            ax.text(hmax * 1.01, y, label(f), color=_shade(color(f), -0.3), fontsize=12,
                    fontweight="bold", va="center")  # fmt: skip
    r = options.loc["delestage"]
    y_label = ymax * 0.6  # au-dessus de la droite de la pointe
    ax.text(y_label * 1000 / r.cout_variable + hmax * 0.04, y_label, label("delestage"),
            ha="left", va="center", color=_shade(color("delestage"), -0.3), fontsize=12,
            fontweight="bold")  # fmt: skip
    y = r.cout_variable * cut / 1000
    ax.vlines(cut, 0, y, color=TEXT, lw=1.2, ls=":")
    ax.plot(cut, y, "o", color="white", mec=TEXT, mew=2, ms=8, zorder=5)
    ax.set_xlim(0, hmax)
    ax.set_ylim(0, ymax)
    ax.set_xticks([0, cut, hmax], ["0", f"{_num(cut)} h", f"{_num(hmax)} h"])
    ax.set_title("Zoom sur les premières heures", fontsize=12, color=TEXT, loc="left")
    _axes(ax, None, "k€/MW/an")


def lcoe_curves(ax: plt.Axes, options: pd.DataFrame, hours_min: float = 500) -> None:
    """Coût moyen du MWh selon la durée de fonctionnement : le classement s'inverse."""
    h = np.linspace(hours_min, HOURS, 400)
    costs = lcoe(options, h)
    for f in options.index:
        ax.plot(h, costs[f], color=color(f), lw=3)
        ax.text(HOURS * 1.01, costs[f].iloc[-1], label(f), color=_shade(color(f), -0.3),
                fontsize=12, fontweight="bold", va="center")  # fmt: skip
    ax.set_ylim(0, float(costs.iloc[-1].max()) * 2.6)
    _hours_axis(ax)
    ax.set_ylabel("Coût moyen (€/MWh)", color=TEXT, fontsize=12)


def lcoe_discount(ax: plt.Axes, hours: dict[str, float], rates=None, year: int | None = None):
    """Coût moyen du MWh selon le taux d'actualisation, à durée de fonctionnement donnée.

    `hours` : filière → heures de fonctionnement par an. Renvoie les valeurs (€/MWh),
    une colonne par filière, indexées par taux.
    """
    rates = np.linspace(0.01, 0.12, 45) if rates is None else np.asarray(rates)
    values = pd.DataFrame(
        {
            f: [lcoe(load_options(year, r).loc[[f]], h)[f].iloc[0] for r in rates]
            for f, h in hours.items()
        },
        index=rates,
    )
    for f, h in hours.items():
        ax.plot(rates * 100, values[f], color=color(f), lw=3)
        ax.text(rates[-1] * 100 + 0.2, values[f].iloc[-1],
                f"{label(f)}\n({_num(h)} h)", color=_shade(color(f), -0.3),
                fontsize=12, fontweight="bold", va="center")  # fmt: skip
    ax.set_xlim(0, rates[-1] * 100)
    ax.set_ylim(0, values.to_numpy().max() * 1.1)
    _axes(ax, "Taux d'actualisation (%)", "Coût moyen (€/MWh)")
    return values


def chronological_load(ax: plt.Axes, load: pd.Series) -> None:
    """Courbe de charge horaire d'une année, dans l'ordre chronologique."""
    hours = np.arange(len(load))
    # Remplissages de 8 760 points en image dans les SVG (poids), bord couvert par la courbe
    ax.fill_between(hours, 0, load.to_numpy(), color=_shade(DEMAND, 0.8), lw=0, rasterized=True)
    ax.plot(hours, load.to_numpy(), color=DEMAND, lw=0.5)
    starts = [hours[load.index.month == m][0] for m in range(1, 13)]
    ax.set_xticks(starts, list("JFMAMJJASOND"))
    ax.set_xlim(0, HOURS)
    ax.set_ylim(0, load.max() * 1.1)
    _axes(ax, "Heures de l'année, dans l'ordre", "GW")


def load_duration(ax: plt.Axes, ldc: np.ndarray, marks: tuple[float, ...] = ()) -> None:
    """Monotone de charge. `marks` : durées (h) dont on lit la puissance dépassée."""
    hours = np.arange(len(ldc)) + 0.5
    ax.fill_between(hours, 0, ldc, color=_shade(DEMAND, 0.8), lw=0, rasterized=True)
    ax.plot(hours, ldc, color=DEMAND, lw=3)
    for h in marks:
        p = level(ldc, h)
        ax.vlines(h, 0, p, color=TEXT, lw=1.2, ls=":")
        ax.hlines(p, 0, h, color=TEXT, lw=1.2, ls=":")
        ax.plot(h, p, "o", color=TEXT, ms=7, zorder=5)
        ax.annotate(f"{_num(p)} GW dépassés\npendant {_num(h)} h", xy=(h, p),
                    xytext=(12, 12), textcoords="offset points", color=TEXT,
                    fontsize=12)  # fmt: skip
    ax.set_ylim(0, ldc[0] * 1.1)
    _hours_axis(ax, "Heures de l'année, classées par consommation décroissante")
    ax.set_ylabel("GW", color=TEXT, fontsize=12)


def screening_method(fig: plt.Figure, options: pd.DataFrame, ldc: np.ndarray) -> pd.DataFrame:
    """*Screening curves* au-dessus de la monotone : durées d'équilibre → capacités.

    Renvoie le parc optimal (`optimal_fleet`).
    """
    fleet = optimal_fleet(options, ldc)
    top, bottom = fig.subplots(2, 1, sharex=True, gridspec_kw={"hspace": 0.12,
                                                               "height_ratios": [1, 1.25]})  # fmt: skip
    screening_curves(top, options, lower=True, breakeven=True, xlabel=None)
    hours = np.arange(len(ldc)) + 0.5
    gap, label_y = ldc[0] * 0.13, np.inf  # écart minimal entre étiquettes, de haut en bas
    for f, r in fleet.iterrows():
        c = color(f)
        bottom.fill_between(hours, r.bas, np.clip(ldc, r.bas, r.haut), color=_shade(c, 0.35),
                            lw=0, rasterized=True)  # fmt: skip
        small = r.capacite < 0.05 * ldc[0]
        text = f"{label(f)} {_num(r.capacite, 1 if small else 0)} GW"
        if not small:
            text = text.replace(" ", "\n", 1)
        label_y = min((r.bas + r.haut) / 2, label_y - gap)
        bottom.text(HOURS * 1.01, label_y, text, color=_shade(c, -0.3), fontsize=12,
                    fontweight="bold", va="center")  # fmt: skip
        if r.debut > 0:
            if r.debut >= 150:
                for ax in (top, bottom):
                    ax.axvline(r.debut, color=TEXT, lw=1.2, ls=":")
            bottom.hlines(r.haut, r.debut, HOURS, color=TEXT, lw=1.2, ls=":")
            bottom.plot(r.debut, r.haut, "o", color=TEXT, ms=7, zorder=5)
    bottom.plot(hours, ldc, color=DEMAND, lw=2.5)
    bottom.set_ylim(0, ldc[0] * 1.08)
    _hours_axis(bottom, "Heures de l'année, classées par consommation décroissante")
    bottom.set_ylabel("Consommation (GW)", color=TEXT, fontsize=12)
    return fleet


# ---------------------------------------------------------------------------
# Couverture des coûts du parc optimal


def hourly_prices(options: pd.DataFrame, load: pd.Series) -> pd.Series:
    """Prix horaire (€/MWh) quand le parc optimal sert `load` : coût variable du moyen
    marginal, VOLL aux heures de délestage.

    `options` doit contenir le délestage (`with_load_shedding`). La filière marginale
    d'une heure est celle dont la tranche de la monotone contient la consommation.
    """
    fleet = optimal_fleet(options, duration_curve(load))
    values = np.asarray(load, float)
    price = np.full(len(values), np.nan)
    marginal = np.empty(len(values), dtype=object)
    for f, r in fleet.iloc[::-1].iterrows():  # de la base vers la pointe
        hit = values > r.bas if r.bas > 0 else np.ones(len(values), bool)
        price[hit] = options.loc[f, "cout_variable"]
        marginal[hit] = f
    prices = pd.Series(price, index=load.index, name="prix")
    prices.attrs["marginale"] = pd.Series(marginal, index=load.index)
    return prices


def inframarginal_rents(options: pd.DataFrame, prices: pd.Series) -> pd.DataFrame:
    """Rente annuelle d'un MW de chaque filière (€/MW/an), par filière marginale.

    Un MW de la filière i gagne p − CV_i à chaque heure où le prix p dépasse son coût
    variable. Lignes : filières construites ; colonnes : filière marginale aux heures
    où la rente est gagnée, puis `rente` (total) et `cout_fixe`.
    """
    marginal = prices.attrs["marginale"]
    built = [f for f in options.index if f != "delestage"]
    rows = {}
    for f in built:
        gain = (prices - options.loc[f, "cout_variable"]).clip(lower=0)
        rows[f] = gain.groupby(marginal).sum()
    rents = pd.DataFrame(rows).T.fillna(0.0)
    order = [f for f in options.index if f in rents.columns]
    rents = rents[order].loc[:, lambda d: d.sum() > 0]
    rents["rente"] = rents.sum(axis=1)
    rents["cout_fixe"] = options.loc[built, "cout_fixe"]
    return rents


def capture_price(ax: plt.Axes, example: CaptureExample) -> None:
    """Semaine type : production éolienne en barres, prix en paliers, prix moyen, prix
    capté et LCOE en lignes horizontales."""
    tab = example.table
    c = color("eolien")
    x = np.arange(len(tab))
    wind = ax.twinx()
    wind.bar(x, tab["facteur_charge_eolien"] * 100, width=0.8, color=_shade(c, 0.55), lw=0)
    wind.set_ylim(0, 100)
    wind.set_ylabel("Éolien (% de la puissance)", color=_shade(c, -0.3), fontsize=11)
    wind.tick_params(colors=_shade(c, -0.3), labelsize=10)
    wind.spines["right"].set_visible(True)
    wind.spines["right"].set_color(_shade(c, -0.1))
    wind.grid(False)
    ax.set_zorder(wind.get_zorder() + 1)
    ax.patch.set_visible(False)
    xs = np.append(x - 0.5, x[-1] + 0.5)
    ys = np.append(tab["prix"].to_numpy(), tab["prix"].iloc[-1])
    ax.step(xs, ys, where="post", color=TEXT, lw=2.5, label="prix du jour")
    lines = [
        (example.mean_price, "prix moyen", TEXT_LIGHT, (0, (2, 2))),
        (example.lcoe, "LCOE", TEXT, (0, (6, 3))),
        (example.captured_price, "prix capté", _shade(c, -0.35), "-"),
    ]
    for value, name, col, ls in lines:
        ax.axhline(value, color=col, lw=2.2, ls=ls, label=f"{name} : {_num(value)} €/MWh")
    handles, names = ax.get_legend_handles_labels()
    handles.append(plt.Rectangle((0, 0), 1, 1, color=_shade(c, 0.55)))
    names.append("production éolienne")
    ax.legend(handles, names, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=5,
              fontsize=11, handlelength=2.2, columnspacing=1.4)  # fmt: skip
    ax.set_xlim(-0.5, len(tab) - 0.5)
    ax.set_ylim(0, tab["prix"].max() * 1.2)
    ax.set_xticks(x, [j.capitalize() for j in tab["jour"]])
    _axes(ax, None, "Prix (€/MWh)")
    ax.grid(axis="y", alpha=0.25)


def price_duration(ax: plt.Axes, prices: pd.Series, options: pd.DataFrame,
                   cap: float = 200.0) -> None:  # fmt: skip
    """Monotone des prix horaires, en paliers colorés par filière marginale.

    Les heures à la VOLL, hors d'échelle, sont signalées par une flèche.
    """
    order = np.argsort(-prices.to_numpy(), kind="stable")
    p = prices.to_numpy()[order]
    marginal = prices.attrs["marginale"].to_numpy()[order]
    hours = np.arange(len(p)) + 0.5
    for f in dict.fromkeys(marginal):
        m = marginal == f
        c = color(f)
        x0, x1 = hours[m][0] - 0.5, hours[m][-1] + 0.5
        y = min(p[m][0], cap)
        ax.fill_between([x0, x1], 0, y, color=_shade(c, 0.6), lw=0)
        ax.hlines(y, x0, x1, color=c, lw=4)
        if f == "delestage":
            ax.annotate(f"VOLL : {_num(p[m][0])} €/MWh pendant {_num(m.sum())} h",
                        xy=(x1, cap * 0.99), xytext=(1500, cap * 0.93), va="center",
                        color=TEXT, fontsize=12, fontweight="bold",
                        arrowprops={"arrowstyle": "->", "color": TEXT})  # fmt: skip
        elif x1 - x0 > 600:
            ax.text((x0 + x1) / 2, y + cap * 0.02, label(f), ha="center", va="bottom",
                    color=_shade(c, -0.35), fontsize=12, fontweight="bold")  # fmt: skip
    ax.set_ylim(0, cap * 1.02)
    _hours_axis(ax, "Heures de l'année, classées par prix décroissant")
    ax.set_ylabel("Prix (€/MWh)", color=TEXT, fontsize=12)


def rent_of(fig: plt.Figure, prices: pd.Series, options: pd.DataFrame, rents: pd.DataFrame,
            filiere: str, cap: float = 200.0) -> None:  # fmt: skip
    """Rente d'un MW de `filiere` : aire entre la monotone des prix et son coût variable,
    puis la même rente en barre, découpée par filière marginale, face au coût fixe.

    Les heures à la VOLL, hors d'échelle, sont signalées par une flèche et leur rente
    chiffrée. Mêmes couleurs dans les deux panneaux.
    """
    left, right = fig.subplots(1, 2, gridspec_kw={"width_ratios": [2.6, 1], "wspace": 0.35})
    fig.subplots_adjust(bottom=0.2)  # place pour la légende de l'axe et la source
    cv = options.loc[filiere, "cout_variable"]
    order = np.argsort(-prices.to_numpy(), kind="stable")
    p = prices.to_numpy()[order]
    marginal = prices.attrs["marginale"].to_numpy()[order]
    hours = np.arange(len(p)) + 0.5
    for f in dict.fromkeys(marginal):
        m = marginal == f
        x0, x1 = hours[m][0] - 0.5, hours[m][-1] + 0.5
        y = min(p[m][0], cap)
        left.fill_between([x0, x1], 0, y, color="#eef1f5", lw=0)
        left.hlines(y, x0, x1, color=color(f), lw=3)
        if p[m][0] > cv and f != "delestage":
            left.fill_between([x0, x1], cv, y, color=color(f), alpha=0.55, lw=0)
            left.text((x0 + x1) / 2, (cv + y) / 2, _num(rents.loc[filiere, f] / 1000, 1),
                      ha="center", va="center", color="white", fontsize=12,
                      fontweight="bold")  # fmt: skip
    left.axhline(cv, color=color(filiere), lw=2, ls=(0, (5, 3)))
    left.text(HOURS * 0.98, cv + cap * 0.02, f"coût variable {label(filiere)}", ha="right",
              va="bottom", color=_shade(color(filiere), -0.3), fontsize=12,
              fontweight="bold")  # fmt: skip
    shed = marginal == "delestage"
    if shed.any() and p[shed][0] > cv:
        left.annotate(f"+ {_num(rents.loc[filiere, 'delestage'] / 1000, 1)} en {_num(shed.sum())} h"
                      f" à la VOLL ({_num(p[shed][0])} €/MWh)",
                      xy=(shed.sum(), cap * 0.99), xytext=(1400, cap * 0.93), va="center",
                      color=color("delestage"), fontsize=12, fontweight="bold",
                      arrowprops={"arrowstyle": "->", "color": TEXT})  # fmt: skip
    left.set_ylim(0, cap * 1.02)
    _hours_axis(left, "Heures, classées par prix décroissant")
    left.set_ylabel("Prix (€/MWh)", color=TEXT, fontsize=12)
    left.set_title(f"Rente d'un MW de {label(filiere)} (k€/an)", color=TEXT, fontsize=13)

    sources = [c for c in rents.columns if c not in ("rente", "cout_fixe")]
    bottom = 0.0
    for s in sources:
        v = rents.loc[filiere, s] / 1000
        if v <= 0:
            continue
        right.bar(0, v, bottom=bottom, width=0.7, color=color(s),
                  alpha=1 if s == "delestage" else 0.55, lw=0)  # fmt: skip
        name = "VOLL" if s == "delestage" else label(s)
        right.text(0, bottom + v / 2, f"{_num(v, 1)}\n{name}", ha="center", va="center",
                   color="white", fontsize=11.5, fontweight="bold")  # fmt: skip
        bottom += v
    cf = rents.loc[filiere, "cout_fixe"] / 1000
    right.bar(1, cf, width=0.7, color="white", ec=TEXT, lw=1.5, hatch="//")
    right.text(0, bottom, _num(bottom, 1), ha="center", va="bottom", color=TEXT, fontsize=12,
               fontweight="bold")  # fmt: skip
    right.text(1, cf, _num(cf, 1), ha="center", va="bottom", color=TEXT, fontsize=12,
               fontweight="bold")  # fmt: skip
    right.set_xticks([0, 1], ["rente", "coût\nfixe"], fontsize=12)
    right.set_xlim(-0.6, 1.6)
    right.set_ylim(0, cf * 1.2)
    right.set_title("k€/MW/an", color=TEXT, fontsize=13)
    _axes(right, None, None)
    right.grid(axis="x", visible=False)


def investment_loop(ax: plt.Axes) -> None:
    """Boucle de l'investissement : profit positif, entrée, baisse des prix, profit nul."""
    ax.set_xlim(-0.5, 10.5)
    ax.set_ylim(0, 6)
    ax.axis("off")
    accent = ACCENTS["production"]
    w, h = 3.7, 1.3
    nodes = [
        (5.0, 5.2, "prix élevés\n(rareté fréquente)"),
        (8.5, 3.0, "profit > 0"),
        (5.0, 0.8, "investissement :\nnouvelles centrales"),
        (1.5, 3.0, "prix plus bas,\nrareté plus rare"),
    ]
    for x, y, text in nodes:
        ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, fc=_shade(accent, 0.82),
                                    ec=accent, lw=2,
                                    boxstyle="round,pad=0,rounding_size=0.15"))  # fmt: skip
        ax.text(x, y, text, ha="center", va="center", color=TEXT, fontsize=12.5,
                fontweight="bold", linespacing=1.3)  # fmt: skip
    # Sens horaire, d'un bord de boîte au bord de la suivante.
    (xt, yt, _), (xr, yr, _), (xb, yb, _), (xl, yl, _) = nodes
    arrows = [
        ((xt + w / 2, yt), (xr, yr + h / 2)),
        ((xr, yr - h / 2), (xb + w / 2, yb)),
        ((xb - w / 2, yb), (xl, yl - h / 2)),
        ((xl, yl + h / 2), (xt - w / 2, yt)),
    ]
    for start, end in arrows:
        ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=20,
                                     color=TEXT, lw=2, shrinkA=4, shrinkB=4,
                                     connectionstyle="arc3,rad=-0.35"))  # fmt: skip
    ax.text(5.0, 3.0, "jusqu'à\nprofit nul", ha="center", va="center", color=accent,
            fontsize=14, fontweight="bold")  # fmt: skip
