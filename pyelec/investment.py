"""Équilibre de long terme : annuités, LCOE, *screening curves* et monotone de charge.

Données :

- `data/exemple/parc-long-terme.csv` : options d'investissement illustratives
  (coût d'investissement en €/kW, durée de vie, taux d'actualisation, coût variable
  en €/MWh des filières sans combustible acheté) ;
- `data/couts/` : coût variable des CCG et des TAC (`pyelec.dispatch.gas_plant_costs`) ;
- `data/couts/securite-approvisionnement.csv` : VOLL et critère de sécurité
  d'approvisionnement (RTE, CRE) ;
- `data/exemple/prix-capte.csv` : prix et productions illustratifs d'une journée ;
- `data/consommation/courbe-charge-2025.csv` : consommation horaire de la France.

Fonctions :

- `annuity_factor`, `load_options` : annualisation de l'investissement, coût fixe
  annuel (€/MW/an) et coût variable de chaque filière ;
- `load_reliability`, `load_voll`, `with_load_shedding` : le délestage comme moyen fictif (coût fixe nul,
  coût variable égal à la VOLL) ;
- `capture_price_example` : prix moyen et prix capté d'un exemple illustratif ;
- `total_cost`, `lcoe` : coût total d'un MW et coût moyen du MWh selon la durée de
  fonctionnement ;
- `envelope` : filières retenues et durées d'équilibre (enveloppe inférieure) ;
- `load_curve`, `duration_curve` : courbe de charge horaire et monotone ;
- `optimal_fleet` : parc optimal par la méthode des *screening curves* ;
- figures : `annuity_schedule`, `screening_curves`, `lcoe_curves`, `lcoe_discount`,
  `shedding_zoom`, `chronological_load`, `load_duration`, `screening_method`.

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

from pyelec.dispatch import gas_plant_costs, number
from pyelec.palette import color, label
from pyelec.paths import DATA_DIR
from pyelec.schema import ACCENTS, TEXT, TEXT_LIGHT, _shade

HOURS = 8760
DEMAND = ACCENTS["consommation"]
INTEREST = "#94a3b8"
ENVELOPE = "#eef1f5"  # aire sous l'enveloppe inférieure


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


def capture_price_example() -> tuple[pd.DataFrame, float, pd.Series]:
    """Exemple illustratif : prix par tranche horaire, prix moyen, prix capté par profil.

    Renvoie la table, le prix moyen (moyenne simple des tranches) et, pour chaque
    profil de production (`solaire`, `pointe`), le prix moyen pondéré par sa production.
    """
    table = pd.read_csv(DATA_DIR / "exemple" / "prix-capte.csv")
    profiles = [c for c in table.columns if c not in ("tranche", "prix")]
    captured = pd.Series(
        {p: float((table["prix"] * table[p]).sum() / table[p].sum()) for p in profiles}
    )
    return table, float(table["prix"].mean()), captured


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
    ax.set_xticks(range(0, HOURS + 1, 2000), [number(x) for x in range(0, HOURS + 1, 2000)])
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
    ax.text(n + 0.8, a, f"annuité\n{number(a)} k€/MW/an", ha="left", va="center", color=TEXT,
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
                ax.text(s.start, ymax, f"{number(s.start)} h", ha="center", va="bottom",
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
    ax.set_xticks([0, cut, hmax], ["0", f"{number(cut)} h", f"{number(hmax)} h"])
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
                f"{label(f)}\n({number(h)} h)", color=_shade(color(f), -0.3),
                fontsize=12, fontweight="bold", va="center")  # fmt: skip
    ax.set_xlim(0, rates[-1] * 100)
    ax.set_ylim(0, values.to_numpy().max() * 1.1)
    _axes(ax, "Taux d'actualisation (%)", "Coût moyen (€/MWh)")
    return values


def chronological_load(ax: plt.Axes, load: pd.Series) -> None:
    """Courbe de charge horaire d'une année, dans l'ordre chronologique."""
    hours = np.arange(len(load))
    ax.fill_between(hours, 0, load.to_numpy(), color=_shade(DEMAND, 0.8), lw=0)
    ax.plot(hours, load.to_numpy(), color=DEMAND, lw=0.5)
    starts = [hours[load.index.month == m][0] for m in range(1, 13)]
    ax.set_xticks(starts, list("JFMAMJJASOND"))
    ax.set_xlim(0, HOURS)
    ax.set_ylim(0, load.max() * 1.1)
    _axes(ax, "Heures de l'année, dans l'ordre", "GW")


def load_duration(ax: plt.Axes, ldc: np.ndarray, marks: tuple[float, ...] = ()) -> None:
    """Monotone de charge. `marks` : durées (h) dont on lit la puissance dépassée."""
    hours = np.arange(len(ldc)) + 0.5
    ax.fill_between(hours, 0, ldc, color=_shade(DEMAND, 0.8), lw=0)
    ax.plot(hours, ldc, color=DEMAND, lw=3)
    for h in marks:
        p = level(ldc, h)
        ax.vlines(h, 0, p, color=TEXT, lw=1.2, ls=":")
        ax.hlines(p, 0, h, color=TEXT, lw=1.2, ls=":")
        ax.plot(h, p, "o", color=TEXT, ms=7, zorder=5)
        ax.annotate(f"{number(p)} GW dépassés\npendant {number(h)} h", xy=(h, p),
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
                            lw=0)  # fmt: skip
        small = r.capacite < 0.05 * ldc[0]
        text = f"{label(f)} {number(r.capacite, 1 if small else 0)} GW"
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
