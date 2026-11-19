"""Figures réutilisées d'un module à l'autre (poly, slides, TP)."""

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from pyelec.palette import SECTOR_COLORS, SECTOR_LABELS, color, label


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


def sector_donut(ax: plt.Axes, consumption: pd.Series, small: float = 0.06) -> None:
    """Anneau de la consommation par secteur, secteurs nommés sur l'anneau.

    `consumption` : TWh indexés par identifiant de secteur (voir SECTOR_COLORS).
    Les secteurs de part inférieure à `small` sont regroupés en « Autres ».
    """
    shares = consumption / consumption.sum()
    big = shares[shares >= small].sort_values(ascending=False)
    rest = shares[shares < small]
    values = list(big.values) + ([rest.sum()] if not rest.empty else [])
    names = [SECTOR_LABELS[s] for s in big.index] + (["Autres"] if not rest.empty else [])
    colors = [SECTOR_COLORS[s] for s in big.index] + (["#a7b0be"] if not rest.empty else [])
    wedges, _ = ax.pie(
        values,
        colors=colors,
        startangle=90,
        counterclock=False,
        wedgeprops={"width": 0.38, "edgecolor": "white", "linewidth": 2},
    )
    for wedge, name, share in zip(wedges, names, values):
        angle = np.deg2rad((wedge.theta1 + wedge.theta2) / 2)
        x, y = np.cos(angle), np.sin(angle)
        ax.annotate(
            f"{name}\n{share:.0%}".replace("%", "\u202f%"),
            xy=(1.0 * x, 1.0 * y),
            xytext=(1.22 * x, 1.12 * y),
            ha="left" if x >= 0 else "right",
            va="center",
            fontsize=13,
            color="#334155",
            arrowprops={"arrowstyle": "-", "color": "#94a3b8", "lw": 1},
        )
    total = consumption.sum()
    ax.text(0, 0.06, f"{total:.0f}", ha="center", va="center", fontsize=24,
            fontweight="bold", color="#334155")  # fmt: skip
    ax.text(0, -0.16, "TWh", ha="center", va="center", fontsize=13, color="#64748b")
    ax.set_aspect("equal")


def capacity_and_production(fig: plt.Figure, mix: pd.DataFrame) -> None:
    """Deux panneaux côte à côte : capacité installée (GW) et production (TWh).

    `mix` : une ligne par filière, colonnes `filiere`, `capacite_gw`,
    `production_twh`. Filières triées par production décroissante, même ordre
    dans les deux panneaux pour comparer puissance et énergie.
    """
    mix = mix.sort_values("production_twh", ascending=True)
    names = [label(f) for f in mix["filiere"]]
    colors = [color(f) for f in mix["filiere"]]
    axes = fig.subplots(1, 2, sharey=True)
    panels = [
        ("capacite_gw", "Capacité installée", "GW"),
        ("production_twh", "Production", "TWh"),
    ]
    for ax, (column, title, unit) in zip(axes, panels):
        values = mix[column].to_numpy()
        ax.barh(names, values, color=colors, height=0.62)
        for y, v in enumerate(values):
            ax.text(v, y, f"  {v:.0f}", va="center", ha="left", fontsize=11, color="#334155")
        total = values.sum()
        ax.set_title(f"{title} : {total:.0f} {unit}", loc="left", fontsize=13, color="#334155")
        ax.set_xlim(0, values.max() * 1.18)
        ax.xaxis.set_visible(False)
        ax.grid(False)
        for side in ("top", "right", "bottom"):
            ax.spines[side].set_visible(False)
        ax.spines["left"].set_color("#cbd5e1")
        ax.tick_params(axis="y", length=0, labelsize=12, labelcolor="#334155")


def _clean(ax: plt.Axes) -> None:
    ax.grid(axis="y", alpha=0.3)
    ax.grid(axis="x", visible=False)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.spines["left"].set_color("#cbd5e1")
    ax.spines["bottom"].set_color("#cbd5e1")
    ax.tick_params(colors="#475569", labelsize=10.5)


def load_views(load: pd.DataFrame, temperature: pd.DataFrame, threshold: float = 15.0) -> dict:
    """Calculs des trois vues de la courbe de charge (`load_variability`, graphique ECharts).

    `load` : colonnes `heure_locale`, `consommation_gw` (pas horaire) ;
    `temperature` : colonnes `date`, `temperature_c` (pas quotidien).
    Renvoie un dictionnaire : `hourly` et `daily` (séries indexées par le temps),
    `weeks` (nom → série d'une semaine indexée par les heures depuis le lundi 0 h),
    `both` (consommation quotidienne `gw` et `temperature_c`, indexées par jour),
    `weekday` (masque des jours ouvrés), `slope` et `intercept` de la droite ajustée
    sur les jours ouvrés de moins de `threshold` °C, `fit_x` (bornes de la droite).
    """
    hourly = load.assign(t=pd.to_datetime(load["heure_locale"])).set_index("t")["consommation_gw"]
    daily = hourly.resample("D").mean()
    weeks = {}
    for month, name in ((1, "hiver"), (7, "été")):
        mondays = hourly.index[
            (hourly.index.month == month)
            & (hourly.index.day_of_week == 0)
            & (hourly.index.hour == 0)
        ]
        start = mondays[1]  # deuxième lundi du mois : semaine sans jour férié de début de mois
        span = hourly[start : start + pd.Timedelta(hours=24 * 7 - 1)]
        weeks[name] = pd.Series(span.values, index=(span.index - start) / pd.Timedelta(hours=1))
    temp = temperature.assign(date=pd.to_datetime(temperature["date"])).set_index("date")
    both = pd.concat([daily.rename("gw"), temp["temperature_c"]], axis=1).dropna()
    weekday = both.index.day_of_week < 5
    cold = both[weekday & (both["temperature_c"] < threshold)]
    slope, intercept = np.polyfit(cold["temperature_c"], cold["gw"], 1)
    return {
        "hourly": hourly,
        "daily": daily,
        "weeks": weeks,
        "both": both,
        "weekday": weekday,
        "slope": float(slope),
        "intercept": float(intercept),
        "fit_x": (float(cold["temperature_c"].min()), threshold),
    }


def load_variability(
    fig: plt.Figure, load: pd.DataFrame, temperature: pd.DataFrame, threshold: float = 15.0
) -> float:
    """Trois vues de la courbe de charge d'une année. Renvoie la thermosensibilité (GW/°C).

    Données : voir `load_views`. En haut, l'année (horaire et moyenne quotidienne) ;
    en bas à gauche, une semaine d'hiver et une d'été ; en bas à droite, la
    consommation quotidienne moyenne selon la température, avec la pente sous
    `threshold` °C.
    """
    winter, summer, slope_color = "#3b5bdb", "#e8590c", "#334155"
    v = load_views(load, temperature, threshold)
    load, daily = v["hourly"], v["daily"]

    grid = fig.add_gridspec(2, 2, height_ratios=[1, 1.15], hspace=0.55, wspace=0.22)
    year = fig.add_subplot(grid[0, :])
    year.plot(load.index, load.values, color="#cbd5e1", lw=0.5)
    year.plot(daily.index, daily.values, color=slope_color, lw=1.6)
    year.set_title("Sur l'année : l'hiver consomme plus que l'été", loc="left", fontsize=12)
    year.set_ylabel("GW")
    year.xaxis.set_major_locator(mdates.MonthLocator())
    year.xaxis.set_major_formatter(
        plt.FuncFormatter(lambda x, _: "JFMAMJJASOND"[mdates.num2date(x).month - 1])
    )
    _clean(year)

    week = fig.add_subplot(grid[1, 0])
    for (name, span), c in zip(v["weeks"].items(), (winter, summer)):
        week.plot(span.index, span.values, color=c, lw=1.8)
        week.text(span.index[-1] + 2, span.values[-1], name, color=c, fontsize=11, va="center")
    week.set_xticks([12 + 24 * d for d in range(7)], list("LMMJVSD"))
    week.set_xlim(0, 24 * 7 + 18)
    week.set_title("Sur la semaine : jour, nuit, week-end", loc="left", fontsize=12)
    week.set_ylabel("GW")
    _clean(week)

    scatter = fig.add_subplot(grid[1, 1])
    both, weekday = v["both"], v["weekday"]
    scatter.scatter(both["temperature_c"][weekday], both["gw"][weekday], s=9, color=winter,
                    alpha=0.55, lw=0, label="jours ouvrés")  # fmt: skip
    scatter.scatter(both["temperature_c"][~weekday], both["gw"][~weekday], s=9, color="#94a3b8",
                    alpha=0.7, lw=0, label="week-ends")  # fmt: skip
    xs = np.array(v["fit_x"])
    scatter.plot(xs, v["slope"] * xs + v["intercept"], color=slope_color, lw=2)
    scatter.set_title("Selon la température : le chauffage", loc="left", fontsize=12)
    scatter.set_xlabel("température moyenne du jour (°C)")
    scatter.set_ylabel("GW")
    scatter.legend(loc="upper right", fontsize=10, markerscale=2, handletextpad=0.2)
    _clean(scatter)
    return -v["slope"]
