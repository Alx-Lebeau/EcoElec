"""Graphiques ECharts des slides : figures de données interactives dans reveal.js.

Usage dans un `slides.qmd`, cellule `#| output: asis` :

    from pyelec import echarts
    print(echarts.chart(echarts.mix_option(mix), height=440,
                        source="RTE (via ODRÉ)", date="2025"))

Le graphique est rendu par le navigateur (SVG) : texte à la police du deck,
infobulles, transitions. Les données sont calculées ici depuis `data/` et
transmises en JSON. La bibliothèque est chargée depuis un CDN dans le site et
embarquée dans les decks autonomes (`embed-resources`). Les PDF (decktape)
capturent les graphiques sans animation.

Chargement : `ecoelec generer` ajoute `loader_html()` en fin de page (clé
`include-after-body`) aux decks dont un module appelle `echarts.chart(`, et non
la cellule du premier graphique, que les marques peuvent retirer du deck.

Les fonctions JavaScript (mise en forme des nombres en français) ne passent pas
par le JSON : une chaîne "fn:<nom>" désigne une fonction de `FORMATTERS`
(`pyelec/echarts.js`).

Les figures matplotlib (`pyelec.figures`) restent la version statique (poly, TP).
"""

import html
import json

import numpy as np
import pandas as pd

from pyelec.figures import load_views
from pyelec.palette import SECTOR_COLORS, SECTOR_LABELS, color, label
from pyelec.paths import ROOT

VERSION = "5.6.0"
CDN = f"https://cdn.jsdelivr.net/npm/echarts@{VERSION}"

FONT = '"Helvetica Neue", Helvetica, Arial, sans-serif'
TEXT = "#334155"
TEXT_LIGHT = "#64748b"
GRID_LINE = "#e2e8f0"
AXIS_LINE = "#cbd5e1"
NBSP = " "  # avant : ; ! ?
NNBSP = " "  # avant %, dans les nombres


def fr(value: float, digits: int = 0) -> str:
    """Nombre au format français (virgule décimale, espace fine des milliers)."""
    return f"{value:,.{digits}f}".replace(",", NNBSP).replace(".", ",")


def _typography(node):
    """Espaces insécables des textes du graphique (comme `typographie.lua`)."""
    if isinstance(node, dict):
        return {k: _typography(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_typography(v) for v in node]
    if isinstance(node, str) and not node.startswith("fn:"):
        for mark in ":;!?":
            node = node.replace(f" {mark}", f"{NBSP}{mark}")
        return node.replace(" %", f"{NNBSP}%")
    return node


def loader_html() -> str:
    """Bibliothèque ECharts, langue française et initialisation dans reveal.js."""
    script = (ROOT / "pyelec" / "echarts.js").read_text(encoding="utf-8")
    return (
        f'<script src="{CDN}/dist/echarts.min.js"></script>\n'
        f'<script src="{CDN}/i18n/langFR.js"></script>\n'
        f"<script>\n{script}</script>\n"
    )


def chart(
    option: dict, height: int = 420, source: str | None = None, date: str | None = None
) -> str:
    """Bloc HTML brut d'un graphique (à imprimer dans une cellule `output: asis`).

    `height` : hauteur en pixels de la slide (1280 × 720). `source`, `date` :
    mention « Source : …, date » sous le graphique (règle du cours).
    """
    option = _typography(option)
    parts = ["```{=html}"]
    data = json.dumps(option, ensure_ascii=False, separators=(",", ":"))
    data = data.replace("</", "<\\/")  # pas de fin de balise dans le script
    parts.append(
        f'<div class="echart"><div class="echart-canvas" style="height:{height}px"></div>'
        f'<script type="application/json">{data}</script></div>'
    )
    if source:
        text = f"Source{NBSP}: {source}" + (f", {date}" if date else "")
        parts.append(f'<p class="source-figure">{html.escape(text)}</p>')
    parts.append("```")
    return "\n".join(parts)


def _base(**option) -> dict:
    """Réglages communs : police, couleurs du texte, infobulles."""
    return {
        "textStyle": {"fontFamily": FONT, "color": TEXT, "fontSize": 20},
        "animationDuration": 700,
        "animationDurationUpdate": 500,
        "tooltip": {
            "textStyle": {"fontFamily": FONT, "fontSize": 17, "color": TEXT},
            "borderColor": AXIS_LINE,
        },
        **option,
    }


def _title(text: str, left, top) -> dict:
    return {
        "text": text,
        "left": left,
        "top": top,
        "textStyle": {"fontFamily": FONT, "fontSize": 22, "fontWeight": "bold", "color": TEXT},
    }


# ---------------------------------------------------------------------------
# Mix : capacité et production par filière, frise des années


def mix_option(mix: pd.DataFrame) -> dict:
    """Capacité installée (GW) et production (TWh) par filière, une frise par année.

    `mix` : colonnes `annee`, `filiere`, `capacite_gw`, `production_twh` (toutes
    les années). Ordre des filières : production décroissante de la dernière année,
    fixe d'une année à l'autre. L'infobulle donne le facteur de charge.
    """
    years = sorted(mix["annee"].unique())
    last = mix[mix["annee"] == years[-1]].sort_values("production_twh")
    order = list(last["filiere"])
    names = [label(f) for f in order]
    xmax = {c: mix[c].max() * 1.15 for c in ("capacite_gw", "production_twh")}

    def year_option(year: int) -> dict:
        y = mix[mix["annee"] == year].set_index("filiere").reindex(order).fillna(0)
        series, titles = [], []
        for column, title, unit in (
            ("capacite_gw", "Capacité installée", "GW"),
            ("production_twh", "Production", "TWh"),
        ):
            data = []
            for f, row in y.iterrows():
                fc = (
                    row["production_twh"] / (row["capacite_gw"] * 8.76) if row["capacite_gw"] else 0
                )
                tip = (
                    f"<b>{label(f)}</b> ({year})<br>"
                    f"capacité{NBSP}: {fr(row['capacite_gw'], 1)}{NNBSP}GW<br>"
                    f"production{NBSP}: {fr(row['production_twh'], 1)}{NNBSP}TWh<br>"
                    f"facteur de charge{NBSP}: {fr(fc * 100)}{NNBSP}%"
                )
                data.append(
                    {
                        "value": round(float(row[column]), 2),
                        "tip": tip,
                        "itemStyle": {"color": color(f)},
                    }
                )
            series.append({"data": data})
            titles.append({"text": f"{title}{NBSP}: {fr(y[column].sum())}{NNBSP}{unit}"})
        return {"series": series, "title": titles}

    bar = {
        "type": "bar",
        "barWidth": "62%",
        "label": {"show": True, "position": "right", "formatter": "fn:entier", "fontSize": 19},
    }
    base = _base(
        title=[_title("", "19%", 0), _title("", "56%", 0)],
        grid=[
            {"left": "19%", "right": "50%", "top": 46, "bottom": 70},
            {"left": "56%", "right": "5%", "top": 46, "bottom": 70},
        ],
        xAxis=[
            {"type": "value", "gridIndex": i, "max": round(xmax[c]), "show": False}
            for i, c in enumerate(("capacite_gw", "production_twh"))
        ],
        yAxis=[
            {
                "type": "category",
                "gridIndex": i,
                "data": names,
                "axisTick": {"show": False},
                "axisLine": {"lineStyle": {"color": AXIS_LINE}},
                "axisLabel": {"show": i == 0, "fontSize": 20, "color": TEXT},
            }
            for i in (0, 1)
        ],
        series=[{**bar, "xAxisIndex": i, "yAxisIndex": i} for i in (0, 1)],
        timeline={
            "axisType": "category",
            "data": [str(y) for y in years],
            "currentIndex": len(years) - 1,
            "autoPlay": False,
            "playInterval": 900,
            "bottom": 0,
            "left": "6%",
            "right": "6%",
            "height": 46,
            "symbolSize": 9,
            "label": {"fontSize": 16, "color": TEXT_LIGHT},
            "lineStyle": {"color": AXIS_LINE},
            "itemStyle": {"color": AXIS_LINE},
            "checkpointStyle": {"color": "#1f4e79", "borderWidth": 0, "symbolSize": 13},
            "controlStyle": {"color": TEXT_LIGHT, "borderColor": TEXT_LIGHT, "itemSize": 18},
            "progress": {"lineStyle": {"color": "#94a3b8"}, "itemStyle": {"color": "#94a3b8"}},
        },
    )
    base["tooltip"]["formatter"] = "fn:tip"
    return {"baseOption": base, "options": [year_option(y) for y in years]}


# ---------------------------------------------------------------------------
# Consommation par secteur


def sector_donut_option(consumption: pd.Series, small: float = 0.06) -> dict:
    """Anneau de la consommation par secteur (TWh indexés par identifiant de secteur).

    Mêmes règles que `pyelec.figures.sector_donut` : secteurs de part inférieure
    à `small` regroupés en « Autres ».
    """
    shares = consumption / consumption.sum()
    big = shares[shares >= small].sort_values(ascending=False)
    rest = consumption[shares < small]
    data = [
        {
            "name": SECTOR_LABELS[s],
            "value": round(float(consumption[s]), 1),
            "itemStyle": {"color": SECTOR_COLORS[s]},
        }
        for s in big.index
    ]
    if not rest.empty:
        detail = ", ".join(SECTOR_LABELS[s].lower() for s in rest.index)
        data.append(
            {
                "name": "Autres",
                "value": round(float(rest.sum()), 1),
                "itemStyle": {"color": "#a7b0be"},
                "detail": detail,
            }
        )
    total = consumption.sum()
    return _base(
        tooltip={
            "trigger": "item",
            "formatter": f"{{b}}{NBSP}: {{c}}{NNBSP}TWh ({{d}}{NNBSP}%)",
            "textStyle": {"fontFamily": FONT, "fontSize": 17, "color": TEXT},
        },
        title={
            "text": fr(total),
            "subtext": "TWh",
            "left": "center",
            "top": "41%",
            "itemGap": 2,
            "textStyle": {"fontFamily": FONT, "fontSize": 48, "fontWeight": "bold", "color": TEXT},
            "subtextStyle": {"fontFamily": FONT, "fontSize": 21, "color": TEXT_LIGHT},
        },
        series=[
            {
                "type": "pie",
                "radius": ["47%", "75%"],
                "center": ["50%", "52%"],
                "startAngle": 90,
                "clockwise": True,
                "percentPrecision": 0,
                "itemStyle": {"borderColor": "#fff", "borderWidth": 3},
                "label": {
                    "formatter": f"{{b}}\n{{d}}{NNBSP}%",
                    "fontSize": 22,
                    "lineHeight": 27,
                    "color": TEXT,
                },
                "labelLine": {"length": 12, "length2": 10, "lineStyle": {"color": "#94a3b8"}},
                "emphasis": {"scaleSize": 6, "label": {"fontWeight": "bold"}},
                "data": data,
            }
        ],
    )


# ---------------------------------------------------------------------------
# Courbe de charge : année, semaine, température


def load_variability_option(
    load: pd.DataFrame, temperature: pd.DataFrame, threshold: float = 15.0
) -> tuple[dict, float]:
    """Trois vues de la courbe de charge, comme `pyelec.figures.load_variability`.

    Renvoie l'option et la thermosensibilité (GW/°C). En haut, l'année au pas
    horaire et sa moyenne quotidienne, avec zoom (molette, glisser, curseur) ;
    en bas, une semaine d'hiver et une d'été, et la consommation quotidienne
    selon la température avec la droite ajustée.
    """
    winter, summer, dark, weekend = "#3b5bdb", "#e8590c", "#334155", "#94a3b8"
    v = load_views(load, temperature, threshold)
    hourly, daily = v["hourly"], v["daily"]

    def stamps(index):
        return index.strftime("%Y-%m-%d %H:%M").tolist()

    def values(series):
        return np.round(series.to_numpy(), 1).tolist()

    days = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
    hours = [f"{days[h // 24]} {h % 24}{NNBSP}h" for h in range(24 * 7)]
    both, weekday = v["both"], v["weekday"]

    def points(mask):
        sub = both[mask]
        return [
            [round(t, 1), round(g, 1), d.strftime("%d/%m")]
            for t, g, d in zip(sub["temperature_c"], sub["gw"], sub.index)
        ]

    x0, x1 = v["fit_x"]
    fit = [[round(x, 1), round(v["slope"] * x + v["intercept"], 1)] for x in (x0, x1)]

    axis = {
        "axisLine": {"lineStyle": {"color": AXIS_LINE}},
        "axisTick": {"show": False},
        "axisLabel": {"color": "#475569", "fontSize": 17},
        "splitLine": {"lineStyle": {"color": GRID_LINE}},
    }
    y_axis = {**axis, "type": "value", "scale": True}
    top, bottom = {"top": 40, "height": 150}, {"top": 272, "height": 140}
    option = _base(
        animation=False,  # 8 760 points : pas d'animation d'entrée
        title=[
            _title(f"Sur l'année{NBSP}: l'hiver consomme plus que l'été (GW)", 50, 0),
            _title(f"Sur la semaine{NBSP}: jour, nuit, week-end (GW)", 50, 232),
            _title(f"Selon la température{NBSP}: le chauffage (GW)", "53%", 232),
        ],
        grid=[
            {"left": 50, "right": 20, **top},
            {"left": 50, "right": "54%", **bottom},
            {"left": "57%", "right": 20, **bottom},
        ],
        xAxis=[
            {
                **axis,
                "type": "time",
                "gridIndex": 0,
                "splitLine": {"show": False},
                "axisLabel": {
                    **axis["axisLabel"],
                    "hideOverlap": True,
                    "formatter": {
                        "year": "{MMM}",
                        "month": "{MMM}",
                        "day": "{d} {MMM}",
                        "hour": "{HH}:{mm}",
                    },
                },
            },
            {
                **axis,
                "type": "category",
                "gridIndex": 1,
                "data": hours,
                "boundaryGap": False,
                "axisLabel": {
                    **axis["axisLabel"],
                    "interval": "fn:midi",
                    "formatter": "fn:initiale",
                },
            },
            {
                **axis,
                "type": "value",
                "gridIndex": 2,
                "name": "température moyenne du jour (°C)",
                "nameLocation": "middle",
                "nameGap": 30,
                "nameTextStyle": {"color": TEXT_LIGHT, "fontSize": 17},
                "splitLine": {"show": False},
            },
        ],
        yAxis=[{**y_axis, "gridIndex": i} for i in range(3)],
        dataZoom=[
            {"type": "inside", "xAxisIndex": 0, "filterMode": "none"},
        ],
        legend={
            "data": ["jours ouvrés", "week-ends"],
            "right": 20,
            "top": 272,
            "orient": "vertical",
            "itemWidth": 12,
            "textStyle": {"fontSize": 17, "color": TEXT},
        },
        tooltip={
            "trigger": "axis",
            "textStyle": {"fontFamily": FONT, "fontSize": 14, "color": TEXT},
            "borderColor": AXIS_LINE,
            "valueFormatter": "fn:gw-1",
        },
        series=[
            {
                "name": "heure par heure",
                "type": "line",
                "xAxisIndex": 0,
                "yAxisIndex": 0,
                "showSymbol": False,
                "sampling": "lttb",
                "lineStyle": {"color": AXIS_LINE, "width": 0.8},
                "itemStyle": {"color": "#94a3b8"},
                "data": [list(p) for p in zip(stamps(hourly.index), values(hourly))],
            },
            {
                "name": "moyenne du jour",
                "type": "line",
                "xAxisIndex": 0,
                "yAxisIndex": 0,
                "showSymbol": False,
                "lineStyle": {"color": dark, "width": 2},
                "itemStyle": {"color": dark},
                "data": [
                    list(p)
                    for p in zip(stamps(daily.index + pd.Timedelta(hours=12)), values(daily))
                ],
            },
            *[
                {
                    "name": name,
                    "type": "line",
                    "xAxisIndex": 1,
                    "yAxisIndex": 1,
                    "showSymbol": False,
                    "smooth": True,
                    "lineStyle": {"color": c, "width": 2.5},
                    "itemStyle": {"color": c},
                    "endLabel": {"show": True, "formatter": "{a}", "color": c, "fontSize": 18},
                    "data": values(span),
                }
                for (name, span), c in zip(v["weeks"].items(), (winter, summer))
            ],
            *[
                {
                    "name": name,
                    "type": "scatter",
                    "xAxisIndex": 2,
                    "yAxisIndex": 2,
                    "symbolSize": 6,
                    "itemStyle": {"color": c, "opacity": opacity},
                    "tooltip": {"trigger": "item", "formatter": "fn:point-temperature"},
                    "data": points(mask),
                }
                for name, mask, c, opacity in (
                    ("jours ouvrés", weekday, winter, 0.6),
                    ("week-ends", ~weekday, weekend, 0.75),
                )
            ],
            {
                "name": "droite ajustée",
                "type": "line",
                "xAxisIndex": 2,
                "yAxisIndex": 2,
                "showSymbol": False,
                "lineStyle": {"color": dark, "width": 2.5},
                "itemStyle": {"color": dark},
                "tooltip": {"show": False},
                "data": fit,
            },
        ],
    )
    return option, -v["slope"]


# ---------------------------------------------------------------------------
# Parts de marché : production et fourniture


def market_shares_option(rows, groups=()) -> dict:
    """Barres horizontales empilées à 100 %, une grille par ligne (titre au-dessus).

    Mêmes entrées que `pyelec.organisation.share_bars` : `rows` = (titre, segments),
    segment = (libellé, part entre 0 et 1, couleur) ; `groups` = (ligne, libellé,
    premier segment, dernier segment), trait au-dessus des segments regroupés.
    """
    bar_px = 84  # épaisseur des barres (px)
    grouped = {g[0]: g for g in groups}
    titles, grids, x_axes, y_axes, series = [], [], [], [], []
    top = 0
    for k, (title, segments) in enumerate(rows):
        bracket = k in grouped
        titles.append(_title(title, 6, top))
        top += 34 + (38 if bracket else 0)
        grids.append({"left": 8, "right": 8, "top": top, "height": bar_px})
        x_axes.append({"type": "value", "gridIndex": k, "min": 0, "max": 1, "show": False})
        y_axes.append({"type": "category", "gridIndex": k, "data": ["barre"], "show": False})
        for i, (name, share, c) in enumerate(segments):
            wide = share >= 0.06
            series.append(
                {
                    "name": name,
                    "type": "bar",
                    "stack": f"ligne-{k}",
                    "xAxisIndex": k,
                    "yAxisIndex": k,
                    "barWidth": bar_px,
                    "itemStyle": {"color": c, "borderColor": "#fff", "borderWidth": 2},
                    "label": {
                        "show": True,
                        "position": "inside" if wide else "bottom",
                        "distance": 6,
                        "formatter": "fn:serie-pourcent",
                        "color": "#fff" if wide else TEXT,
                        "fontWeight": "bold" if wide else "normal",
                        "fontSize": 21 if share >= 0.15 else 17,
                        "lineHeight": 25 if share >= 0.15 else 20,
                    },
                    "tooltip": {"formatter": "fn:serie-pourcent-ligne"},
                    "data": [round(float(share), 4)],
                }
            )
        if bracket:
            _, text, first, last = grouped[k]
            start = sum(s[1] for s in segments[:first])
            width = sum(s[1] for s in segments[first : last + 1])
            series.append(
                {
                    "name": text,  # libellé lu par le dessin de l'accolade
                    "type": "custom",
                    "xAxisIndex": k,
                    "yAxisIndex": k,
                    "silent": True,
                    "tooltip": {"show": False},
                    "renderItem": "fn:accolade",
                    "data": [[start, start + width, bar_px / 2]],
                    "z": 5,
                }
            )
        top += bar_px + 62
    return _base(
        title=titles,
        grid=grids,
        xAxis=x_axes,
        yAxis=y_axes,
        tooltip={
            "trigger": "item",
            "textStyle": {"fontFamily": FONT, "fontSize": 17, "color": TEXT},
            "borderColor": AXIS_LINE,
        },
        series=series,
    )
