"""Étude de cas « EnR et investissement » : un parc thermique et du solaire, heure par heure.

Modèle de référence de l'outil interactif du module `cas-enr-investissement` (l'outil
en JavaScript doit retrouver les mêmes résultats).

Données :

- `data/exemple/parc-long-terme.csv` et `data/couts/` : TAC, CCG, nucléaire
  (`pyelec.investment.load_options`) ;
- `data/exemple/parc-solaire.csv` : coûts du solaire au sol ;
- `data/production/solaire-2025.csv` : production solaire horaire de la France ;
- `data/mix/mix-france.csv` : capacité solaire installée en fin d'année ;
- `data/consommation/courbe-charge-2025.csv` : consommation horaire.

Fonctions :

- `load_case` : filières, profil solaire, consommation et VOLL du cas ;
- `thermal_options` : TAC, CCG, nucléaire avec un prix du CO₂ choisi ;
- `solar_option`, `load_solar_profile` : coûts du solaire, facteur de charge horaire ;
- `dispatch` : fonctionnement heure par heure d'un parc donné (merit order) ;
- `summary` : indicateurs annuels (énergie, coûts, rentes inframarginales, profits,
  prix, valeur du solaire) ;
- `tool_data` : données de l'outil interactif (JavaScript) ;
- `optimal_fleet` : parc optimal, avec une capacité solaire imposée ou choisie ;
- figures : `solar_profile`, `residual_duration`, `dispatch_week`.

Unités : GW, GWh par heure, €/MWh, coûts fixes en €/MW/an, résultats annuels en M€.
"""

from dataclasses import dataclass, field

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from pyelec import investment
from pyelec.dispatch import gas_plant_costs, load_gas_plants
from pyelec.palette import color, label
from pyelec.paths import DATA_DIR

SOLAR = "solaire"
THERMAL = ["nucleaire", "ccg", "tac"]
YEAR = 2025

# Paramètres des questions, communs aux slides, à l'outil et au corrigé.
NUCLEAR_CUT = 0.10  # question 2 : part du nucléaire retirée au parc optimal
CO2_PRICES = (0.0, 150.0)  # question 3 : prix du CO₂ étudiés (€/t)
SOLAR_MAX_LEVEL = 100.0  # question 4 : plus forte capacité solaire hors marché (GW)
SOLAR_COST_CUT = 0.30  # question 5 : baisse du coût fixe du solaire


# ---------------------------------------------------------------------------
# Données


def thermal_options(co2_price: float | None = None, year: int | None = None) -> pd.DataFrame:
    """Options thermiques (`pyelec.investment.load_options`), coût variable des CCG et
    des TAC recalculé avec `co2_price` (€/t) au lieu du prix de l'année."""
    options = investment.load_options(year)
    if co2_price is not None:
        costs = gas_plant_costs(year)
        plants = load_gas_plants()
        co2 = plants["facteur_emission"] * co2_price / plants["rendement"]
        for f in ("ccg", "tac"):
            options.loc[f, "cout_variable"] = costs.loc[f, "gaz"] + co2[f] + costs.loc[f, "vom"]
    options.attrs["prix_co2"] = (
        float(gas_plant_costs(year).attrs["prix_co2"]) if co2_price is None else co2_price
    )
    return options


def solar_option(rate: float | None = None) -> pd.Series:
    """Coûts du solaire au sol : mêmes colonnes que `investment.load_options`."""
    data = pd.read_csv(DATA_DIR / "exemple" / "parc-solaire.csv").set_index("filiere")
    row = data.loc[SOLAR].astype(float)
    if rate is not None:
        row["taux_actualisation"] = rate
    row["annuite"] = (
        row["investissement"]
        * 1000
        * investment.annuity_factor(row["taux_actualisation"], row["duree_vie"])
    )
    row["cout_fixe"] = row["annuite"] + row["exploitation_fixe"] * 1000
    return row


def solar_capacity(year: int = YEAR) -> pd.Series:
    """Capacité solaire installée (GW) en fin d'année `year - 1` et `year`."""
    mix = pd.read_csv(DATA_DIR / "mix" / "mix-france.csv")
    mix = mix[mix["filiere"] == SOLAR].set_index("annee")["capacite_gw"]
    return mix.loc[[year - 1, year]]


def solar_levels(year: int = YEAR) -> tuple[float, float, float]:
    """Capacités solaires de la question 4 (GW) : parc installé en fin d'année (arrondi),
    son double, et `SOLAR_MAX_LEVEL`."""
    installed = float(round(solar_capacity(year).iloc[-1]))
    return installed, 2 * installed, SOLAR_MAX_LEVEL


def load_solar_profile(year: int = YEAR) -> pd.Series:
    """Facteur de charge horaire du solaire (production / capacité moyenne de l'année).

    La capacité installée croît pendant l'année : la production est rapportée à la
    moyenne des capacités de début et de fin d'année.
    """
    data = pd.read_csv(DATA_DIR / "production" / f"solaire-{year}.csv")
    production = data.set_index(pd.to_datetime(data["heure_locale"]))["solaire_gw"]
    return production / solar_capacity(year).mean()


@dataclass
class Case:
    """Données du cas : coûts des filières, consommation et profil solaire horaires."""

    options: pd.DataFrame  # filières thermiques et solaire : cout_fixe, cout_variable
    load: pd.Series  # consommation horaire (GW)
    solar_cf: pd.Series  # facteur de charge horaire du solaire
    voll: float  # €/MWh
    attrs: dict = field(default_factory=dict)

    def with_co2(self, co2_price: float) -> "Case":
        """Même cas avec un autre prix du CO₂ (VOLL inchangée)."""
        options = self.options.copy()
        thermal = thermal_options(co2_price)
        options.loc[THERMAL, "cout_variable"] = thermal.loc[THERMAL, "cout_variable"]
        return Case(
            options, self.load, self.solar_cf, self.voll, {**self.attrs, "prix_co2": co2_price}
        )

    def with_costs(self, **fixed_costs: float) -> "Case":
        """Même cas avec d'autres coûts fixes (€/MW/an), par filière."""
        options = self.options.copy()
        for f, value in fixed_costs.items():
            options.loc[f, "cout_fixe"] = value
        return Case(options, self.load, self.solar_cf, self.voll, dict(self.attrs))

    def with_constant_solar(self) -> "Case":
        """Même cas avec un solaire hypothétique au facteur de charge constant."""
        flat = pd.Series(self.solar_cf.mean(), index=self.solar_cf.index)
        return Case(self.options, self.load, flat, self.voll, {**self.attrs, "profil": "constant"})


def load_case(co2_price: float | None = None) -> Case:
    """Cas de référence : coûts de 2025 (gaz et CO₂ de l'année sauf `co2_price`),
    consommation et profil solaire de 2025.

    VOLL stylisée comme dans le module long terme : délestage et TAC coûtent autant
    au critère de défaillance (3 h par an), avec les coûts de référence.
    """
    reference = thermal_options()
    hours = investment.load_reliability()["critere_defaillance"]
    voll = investment.with_load_shedding(reference, hours).attrs["voll"]
    options = thermal_options(co2_price)[["cout_fixe", "cout_variable"]]
    solar = solar_option()
    options.loc[SOLAR] = [solar["cout_fixe"], solar["cout_variable"]]
    case = Case(
        options,
        investment.load_curve(),
        load_solar_profile(),
        voll,
        {
            "annee": reference.attrs["annee"],
            "prix_co2": thermal_options(co2_price).attrs["prix_co2"],
        },
    )
    return case


# ---------------------------------------------------------------------------
# Fonctionnement d'un parc donné


def dispatch(case: Case, capacities: dict[str, float]) -> pd.DataFrame:
    """Fonctionnement heure par heure d'un parc (GW par filière).

    Le solaire produit d'abord (coût variable nul), puis les filières thermiques par
    coût variable croissant, puis le délestage. Colonnes : `consommation`, `solaire_dispo`,
    une colonne de production par filière, `ecretement`, `delestage`, `residuelle`
    (consommation moins solaire produit), `prix` (coût variable de la dernière
    filière appelée, VOLL en cas de délestage, coût du solaire s'il est écrêté).
    """
    load = case.load.to_numpy(float)
    available = case.solar_cf.to_numpy(float) * capacities.get(SOLAR, 0.0)
    solar = np.minimum(available, load)
    residual = load - solar
    out = {"consommation": load, "solaire_dispo": available, SOLAR: solar}
    price = np.where(solar < available, case.options.loc[SOLAR, "cout_variable"], np.nan)
    remaining = residual.copy()
    thermal = case.options.loc[THERMAL].sort_values("cout_variable")
    for f, row in thermal.iterrows():
        cap = capacities.get(f, 0.0)
        produced = np.minimum(remaining, cap)
        remaining = remaining - produced
        out[f] = produced
        marginal = np.isnan(price) & (produced > 0) & (remaining <= 1e-9) & (produced < cap)
        price = np.where(marginal, row.cout_variable, price)
    out["ecretement"] = available - solar
    out["delestage"] = remaining
    price = np.where(remaining > 1e-9, case.voll, price)
    # Production pile égale à une capacité : prix de la filière suivante, approché par
    # celui de la dernière filière en production.
    last = np.full(len(load), np.nan)
    for f, row in thermal.iterrows():
        last = np.where(out[f] > 0, row.cout_variable, last)
    price = np.where(np.isnan(price), np.where(np.isnan(last), 0.0, last), price)
    out["residuelle"] = residual
    out["prix"] = price
    return pd.DataFrame(out, index=case.load.index)


def summary(case: Case, capacities: dict[str, float], hourly: pd.DataFrame | None = None) -> dict:
    """Indicateurs annuels d'un parc : énergies (TWh), coûts (M€), rente inframarginale
    et profit de long terme par MW (k€/MW/an), prix moyen et valeur de marché du solaire
    (€/MWh), subvention du solaire (M€/an).

    Rente inframarginale d'un MW : somme sur l'année de (prix − coût variable) ×
    production. Profit (de long terme) : rente inframarginale moins coût fixe."""
    hourly = dispatch(case, capacities) if hourly is None else hourly
    techs = [SOLAR, *THERMAL]
    caps = {f: capacities.get(f, 0.0) for f in techs}
    o = case.options
    energy = {f: hourly[f].sum() / 1000 for f in techs}  # TWh
    variable = {f: energy[f] * o.loc[f, "cout_variable"] for f in techs}  # M€
    fixed = {f: caps[f] * o.loc[f, "cout_fixe"] / 1000 for f in techs}  # GW × €/MW/an → M€
    shed = hourly["delestage"].sum() / 1000
    margin = {
        f: ((hourly["prix"] - o.loc[f, "cout_variable"]) * hourly[f]).sum() / 1000 for f in techs
    }
    profit = {
        f: (margin[f] - fixed[f]) / caps[f] if caps[f] > 0 else np.nan for f in techs
    }  # M€/GW = k€/MW
    total = sum(variable.values()) + sum(fixed.values()) + shed * case.voll
    solar_value = (
        (hourly["prix"] * hourly[SOLAR]).sum() / hourly[SOLAR].sum()
        if energy[SOLAR] > 0
        else np.nan
    )
    return {
        "capacite": caps,
        "energie": energy,
        "facteur_charge": {
            f: energy[f] * 1000 / (caps[f] * 8760) if caps[f] else np.nan for f in techs
        },
        "ecretement": hourly["ecretement"].sum() / 1000,
        "delestage": shed,
        "heures_delestage": int((hourly["delestage"] > 1e-9).sum()),
        "cout_variable": variable,
        "cout_fixe": fixed,
        "cout_delestage": shed * case.voll,
        "cout_total": total,
        "rente_inframarginale": {f: margin[f] / caps[f] if caps[f] > 0 else np.nan for f in techs},
        "profit": profit,
        "prix_moyen": float(hourly["prix"].mean()),
        "valeur_solaire": float(solar_value),
        "subvention_solaire": -profit[SOLAR] * caps[SOLAR] if caps[SOLAR] > 0 else 0.0,  # M€/an
    }


# ---------------------------------------------------------------------------
# Parc optimal


def _thermal_fleet(case: Case, residual: np.ndarray) -> dict[str, float]:
    """Parc thermique optimal face à une consommation résiduelle (screening curves)."""
    options = case.options.loc[THERMAL]
    shedding = pd.DataFrame(
        {"cout_fixe": [0.0], "cout_variable": [case.voll]},
        index=pd.Index(["delestage"], name="filiere"),
    )
    fleet = investment.optimal_fleet(
        pd.concat([shedding, options]), investment.duration_curve(residual)
    )
    return {f: float(fleet.loc[f, "capacite"]) if f in fleet.index else 0.0 for f in THERMAL}


def optimal_fleet(
    case: Case, solar: float | None = 0.0, solar_max: float = 1000.0
) -> dict[str, float]:
    """Parc optimal. `solar` fixe la capacité solaire (GW, hors marché) ; `None` la
    laisse choisir : le coût total est convexe en capacité solaire, d'où une recherche
    par section dorée, avec le parc thermique optimal pour chaque valeur."""

    def fleet(s: float) -> dict[str, float]:
        residual = np.maximum(case.load.to_numpy(float) - case.solar_cf.to_numpy(float) * s, 0.0)
        return {SOLAR: s, **_thermal_fleet(case, residual)}

    if solar is not None:
        return fleet(solar)

    def cost(s: float) -> float:
        return summary(case, fleet(s))["cout_total"]

    a, b = 0.0, solar_max
    ratio = (np.sqrt(5) - 1) / 2
    c, d = b - ratio * (b - a), a + ratio * (b - a)
    fc, fd = cost(c), cost(d)
    while b - a > 0.05:
        if fc < fd:
            b, d, fd = d, c, fc
            c = b - ratio * (b - a)
            fc = cost(c)
        else:
            a, c, fc = c, d, fd
            d = a + ratio * (b - a)
            fd = cost(d)
    best = (a + b) / 2
    return fleet(best if cost(best) < cost(0.0) else 0.0)


# ---------------------------------------------------------------------------
# Figures


def solar_profile(fig: plt.Figure, solar_cf: pd.Series) -> None:
    """Facteur de charge du solaire : moyenne journalière sur l'année, et deux journées
    types (moyenne horaire de janvier et de juillet)."""
    ax1, ax2 = fig.subplots(1, 2, gridspec_kw={"width_ratios": [1.6, 1]})
    c = color(SOLAR)
    daily = solar_cf.resample("D").mean()
    ax1.fill_between(daily.index, daily.to_numpy() * 100, color=c, alpha=0.35, lw=0)
    ax1.plot(daily.index, daily.to_numpy() * 100, color=c, lw=1)
    ax1.axhline(solar_cf.mean() * 100, color="#374151", lw=1, ls="--")
    ax1.text(
        daily.index[5], solar_cf.mean() * 100 + 2.5, "moyenne annuelle", fontsize=9, color="#374151"
    )
    ax1.set_ylabel("Facteur de charge (%)")
    ax1.set_title("Moyenne de chaque jour", fontsize=11)
    ax1.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter("%b"))
    ax1.set_ylim(0, None)
    for month, ls, name in ((1, ":", "janvier"), (7, "-", "juillet")):
        part = solar_cf[solar_cf.index.month == month]
        profile = part.groupby(part.index.hour).mean() * 100
        ax2.plot(profile.index, profile.to_numpy(), color=c, ls=ls, lw=2, label=name)
    ax2.set_xlabel("Heure")
    ax2.set_xticks([0, 6, 12, 18, 23])
    ax2.set_title("Journée moyenne", fontsize=11)
    ax2.legend(frameon=False, fontsize=9)
    ax2.set_ylim(0, None)


def residual_duration(ax: plt.Axes, case: Case, solar_levels: tuple[float, ...]) -> None:
    """Monotone de la consommation et des consommations résiduelles (consommation moins
    production solaire) pour plusieurs capacités solaires (GW)."""
    load = case.load.to_numpy(float)
    x = np.arange(1, len(load) + 1)
    ax.plot(x, investment.duration_curve(load), color="#374151", lw=2, label="Consommation")
    shades = np.linspace(0.45, 1.0, len(solar_levels))
    for s, alpha in zip(solar_levels, shades, strict=True):
        residual = load - case.solar_cf.to_numpy(float) * s
        ax.plot(x, np.sort(residual)[::-1], color=color(SOLAR), alpha=alpha, lw=1.6,
                label=f"Résiduelle, {s:.0f} GW de solaire".replace(".", ","))  # fmt: skip
    ax.axhline(0, color="#9ca3af", lw=0.8)
    ax.set_xlim(0, len(load))
    ax.set_xlabel("Heures de l'année, classées")
    ax.set_ylabel("GW")
    ax.legend(frameon=False, fontsize=9, loc="lower left")


def dispatch_week(ax: plt.Axes, hourly: pd.DataFrame, start: str, days: int = 7) -> None:
    """Production empilée d'une semaine : solaire, nucléaire, CCG, TAC, délestage,
    écrêtement au-dessus, consommation en trait."""
    week = hourly.loc[start : pd.Timestamp(start) + pd.Timedelta(days=days) - pd.Timedelta(hours=1)]
    techs = [SOLAR, "nucleaire", "ccg", "tac", "delestage"]
    ax.stackplot(week.index, *[week[f].to_numpy() for f in techs],
                 colors=[color(f) for f in techs], labels=[label(f) for f in techs], lw=0)  # fmt: skip
    top = week[techs].sum(axis=1)
    ax.fill_between(week.index, top, top + week["ecretement"], color=color(SOLAR), alpha=0.3,
                    lw=0, label="Solaire écrêté")  # fmt: skip
    ax.plot(week.index, week["consommation"], color="#111827", lw=1.5, label="Consommation")
    ax.set_ylabel("GW")
    ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter("%d/%m"))
    ax.set_ylim(0, None)


def price_duration(
    ax: plt.Axes, case: Case, hourly: pd.DataFrame, tech: str, cap: float = 300.0
) -> None:
    """Monotone de prix (prix horaires classés), écrêtée à `cap` €/MWh, et coût variable
    de `tech` : l'aire entre les deux, pendant les heures où `tech` produit, est son
    rente inframarginale par MW."""
    prices = np.sort(hourly["prix"].to_numpy(float))[::-1]
    x = np.arange(1, len(prices) + 1)
    cv = case.options.loc[tech, "cout_variable"]
    shown = np.minimum(prices, cap)
    ax.fill_between(x, cv, shown, where=shown > cv, color=color(tech), alpha=0.35, lw=0,
                    label=f"Rente inframarginale d'un MW de {label(tech).lower()}")  # fmt: skip
    ax.step(x, shown, where="post", color="#111827", lw=1.6, label="Prix")
    ax.axhline(cv, color=color(tech), lw=1.6, ls="--", label=f"Coût variable {label(tech).lower()}")
    shed = int((prices >= case.voll).sum())
    if shed:
        ax.annotate(f"{shed} h au prix de la VOLL", xy=(shed, cap), xytext=(shed + 600, cap * 0.92),
                    fontsize=9, arrowprops={"arrowstyle": "->", "color": "#374151"})  # fmt: skip
    ax.set_xlim(0, len(prices))
    ax.set_ylim(0, cap * 1.02)
    ax.set_xlabel("Heures de l'année, classées")
    ax.set_ylabel("€/MWh")
    ax.legend(frameon=False, fontsize=9, loc="upper right", bbox_to_anchor=(1, 0.85))


def _breakeven(options: pd.DataFrame, a: str, b: str) -> float:
    """Durée de fonctionnement (h/an) où les filières `a` et `b` coûtent autant."""
    ra, rb = options.loc[a], options.loc[b]
    return float((rb.cout_fixe - ra.cout_fixe) / (ra.cout_variable - rb.cout_variable))


def co2_screening(ax: plt.Axes, case: Case, co2_price: float) -> None:
    """*Screening curves* des filières thermiques (k€/MW/an) au prix du CO₂ du cas
    (trait plein) et à `co2_price` (tirets) : la durée d'équilibre entre CCG et
    nucléaire recule quand le CO₂ renchérit le gaz."""
    h = np.array([0, investment.HOURS])
    high = case.with_co2(co2_price).options
    for options, ls, alpha in ((case.options, "-", 1.0), (high, "--", 0.9)):
        for f in THERMAL:
            r = options.loc[f]
            ax.plot(h, (r.cout_fixe + r.cout_variable * h) / 1000, color=color(f), ls=ls,
                    lw=2.4, alpha=alpha)  # fmt: skip
        x = _breakeven(options, "ccg", "nucleaire")
        y = (
            options.loc["nucleaire", "cout_fixe"] + options.loc["nucleaire", "cout_variable"] * x
        ) / 1000
        ax.plot([x, x], [0, y], color="#374151", lw=1, ls=":")
        ax.plot(x, y, "o", color="#374151", ms=5)
    for f in THERMAL:
        r = case.options.loc[f]
        y_end = (r.cout_fixe + r.cout_variable * investment.HOURS) / 1000
        ax.text(investment.HOURS * 1.01, min(y_end, 1550), label(f), color=color(f), fontsize=11,
                fontweight="bold", va="center")  # fmt: skip
    ax.plot(
        [],
        [],
        color="#374151",
        lw=2,
        label=f"CO₂ à {case.attrs['prix_co2']:.1f} €/t".replace(".", ","),
    )
    ax.plot([], [], color="#374151", lw=2, ls="--", label=f"CO₂ à {co2_price:.0f} €/t")
    ax.set_xlim(0, investment.HOURS)
    ax.set_ylim(0, 1600)
    ax.set_xlabel("Heures de fonctionnement par an")
    ax.set_ylabel("k€/MW/an")
    ax.legend(frameon=False, fontsize=9, loc="upper left")


def residual_reading(ax: plt.Axes, case: Case, solar: float) -> None:
    """Monotones de la consommation et de la consommation résiduelle avec `solar` GW,
    et lecture de la capacité nucléaire optimale sur chacune (durée d'équilibre entre
    CCG et nucléaire) : l'écart est le nucléaire en moins."""
    hours = _breakeven(case.options, "ccg", "nucleaire")
    load = case.load.to_numpy(float)
    residual = load - case.solar_cf.to_numpy(float) * solar
    x = np.arange(1, len(load) + 1)
    levels = []
    for series, c, name in (
        (load, "#374151", "Consommation"),
        (residual, color(SOLAR), f"Résiduelle, {solar:.0f} GW de solaire"),
    ):
        ldc = np.sort(series)[::-1]
        ax.plot(x, ldc, color=c, lw=2, label=name)
        levels.append(investment.level(ldc, hours))
        ax.plot([0, hours], [levels[-1]] * 2, color=c, lw=1, ls=":")
    ax.axvline(hours, color=color("nucleaire"), lw=1.2, ls="--")
    ax.annotate("", xy=(hours * 0.5, levels[1]), xytext=(hours * 0.5, levels[0]),
                arrowprops={"arrowstyle": "<->", "color": color("nucleaire"), "lw": 1.5})  # fmt: skip
    ax.text(hours * 0.5 + 150, (levels[0] + levels[1]) / 2, "nucléaire\nen moins", fontsize=9,
            va="center", color="#374151")  # fmt: skip
    ax.text(hours + 120, 88, "durée d'équilibre\nCCG / nucléaire", fontsize=9, va="top",
            color="#374151")  # fmt: skip
    ax.set_xlim(0, len(load))
    ax.set_ylim(0, 92)
    ax.set_xlabel("Heures de l'année, classées")
    ax.set_ylabel("GW")
    ax.legend(frameon=False, fontsize=9, loc="lower left")


def solar_day_prices(
    fig: plt.Figure, case: Case, fleet: dict[str, float], levels, day: str
) -> None:
    """Prix heure par heure d'une journée, à parc pilotable donné, un panneau par
    capacité solaire (GW), avec la production solaire en fond : le solaire chasse les
    filières chères aux heures où il produit, et fait baisser le prix quand il vend."""
    axes = fig.subplots(len(levels), 1, sharex=True)
    cvs = case.options.loc[THERMAL, "cout_variable"].sort_values()
    top = float(cvs.iloc[-1]) * 1.15
    for ax, s in zip(axes, levels, strict=True):
        hourly = dispatch(case, {**fleet, SOLAR: s}).loc[day]
        h = hourly.index.hour
        twin = ax.twinx()
        twin.fill_between(h, hourly[SOLAR], step="mid", color=color(SOLAR), alpha=0.25, lw=0)
        twin.set_ylim(0, max(levels) * 0.8 if max(levels) else 1)
        twin.set_yticks([])
        twin.spines[["top", "right"]].set_visible(False)
        ax.step(h, np.minimum(hourly["prix"], top), where="mid", color="#111827", lw=2)
        ax.set_ylim(0, top)
        ax.set_yticks(cvs.to_numpy(), [label(f) for f in cvs.index], fontsize=8)
        ax.set_zorder(twin.get_zorder() + 1)
        ax.patch.set_visible(False)
        ax.text(0.01, 0.92, f"{s:.0f} GW de solaire", transform=ax.transAxes, fontsize=9,
                va="top", fontweight="bold")  # fmt: skip
    axes[-1].set_xlim(0, 23)
    axes[-1].set_xticks([0, 6, 12, 18, 23])
    axes[-1].set_xlabel("Heure")


# ---------------------------------------------------------------------------
# Outil interactif


def tool_data(year: int = YEAR) -> dict:
    """Données de l'outil interactif (`modules/cas-enr-investissement/modele.js`) :
    hypothèses brutes de chaque filière, pour que l'outil recalcule coûts fixes et
    coûts variables quand le public les modifie, séries horaires, VOLL, paramètres des
    questions, couleurs et libellés."""
    options = investment.load_options(year)
    costs = gas_plant_costs(year)
    plants = load_gas_plants()
    case = load_case()
    techs = {}
    for f in THERMAL:
        r = options.loc[f]
        entry = {
            "investissement": float(r.investissement),
            "exploitation_fixe": float(r.exploitation_fixe),
            "duree_vie": float(r.duree_vie),
            "taux_actualisation": float(r.taux_actualisation),
            "cout_variable": float(r.cout_variable),
        }
        if f in costs.index:  # coût variable = gaz + co2_par_tonne × prix du CO₂ + vom
            entry["gaz"] = float(costs.loc[f, "gaz"])
            entry["co2_par_tonne"] = float(
                plants.loc[f, "facteur_emission"] / plants.loc[f, "rendement"]
            )
            entry["vom"] = float(costs.loc[f, "vom"])
        techs[f] = entry
    s = solar_option()
    techs[SOLAR] = {k: float(s[k]) for k in ("investissement", "exploitation_fixe", "duree_vie",
                                              "taux_actualisation", "cout_variable")}  # fmt: skip
    return {
        "annee": int(case.attrs["annee"]),
        "prix_co2": float(case.attrs["prix_co2"]),
        "voll": float(case.voll),
        "heures": [t.strftime("%Y-%m-%d %H:%M") for t in case.load.index],
        "consommation": [round(float(x), 3) for x in case.load],
        "facteur_charge_solaire": [round(float(x), 5) for x in case.solar_cf],
        "capacite_solaire_installee": float(solar_capacity(year).iloc[-1]),
        "filieres": techs,
        "ordre": [SOLAR, *THERMAL],
        "couleurs": {f: color(f) for f in [SOLAR, *THERMAL, "delestage"]},
        "libelles": {f: label(f) for f in [SOLAR, *THERMAL, "delestage"]},
        "questions": {
            "baisse_nucleaire": NUCLEAR_CUT,
            "prix_co2": list(CO2_PRICES),
            "niveaux_solaire": list(solar_levels(year)),
            "baisse_cout_solaire": SOLAR_COST_CUT,
        },
    }
