"""Figures et schémas de pyelec : dessin sans erreur, calculs affichés sur les slides."""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from pyelec.schema import FADED, TAGS, _Ctx, grid_diagram


def test_dessin_toutes_options():
    for kwargs in [{}, {"labels": True}, {"highlight": {tag: "#123456" for tag in TAGS}}]:
        fig, ax = plt.subplots()
        grid_diagram(ax, **kwargs)
        assert ax.patches and ax.lines
        plt.close(fig)


def test_mise_en_evidence():
    ctx = _Ctx({"transport": "#123456", "nucleaire": None})
    assert ctx.color("#000000", "ligne-AB", ("transport", "lignes")) == "#123456"
    assert ctx.color("#e4a600", "nucleaire", ("production",)) == "#e4a600"
    assert ctx.color("#000000", "ligne-HTA", ("distribution",)) == FADED
    assert _Ctx(None).color("#abcdef", "x", ()) == "#abcdef"


def test_anneau_secteurs_regroupe_les_petits():
    import pandas as pd

    from pyelec.figures import sector_donut

    fig, ax = plt.subplots()
    conso = pd.Series(
        {"residentiel": 50.0, "industrie": 45.0, "agriculture": 3.0, "non-affecte": 2.0}
    )
    sector_donut(ax, conso)
    labels = [t.get_text().split("\n")[0] for t in ax.texts if "\n" in t.get_text()]
    assert labels == ["Résidentiel", "Industrie", "Autres"]
    plt.close(fig)


def test_capacite_et_production_meme_ordre():
    import pandas as pd

    from pyelec.figures import capacity_and_production

    fig = plt.figure()
    mix = pd.DataFrame(
        {
            "filiere": ["solaire", "nucleaire", "gaz"],
            "capacite_gw": [30.0, 63.0, 12.0],
            "production_twh": [33.0, 373.0, 16.0],
        }
    )
    capacity_and_production(fig, mix)
    left, right = fig.axes
    order = [t.get_text() for t in left.get_yticklabels()]
    assert order == ["Gaz", "Solaire", "Nucléaire"]  # production croissante, de bas en haut
    # même ordre à droite : axe des filières partagé ; barres = production croissante
    assert [round(p.get_width()) for p in right.patches] == [16, 33, 373]
    assert "105 GW" in left.get_title(loc="left") and "422 TWh" in right.get_title(loc="left")
    plt.close(fig)


def test_schemas_organisation():
    from pyelec.organisation import market_overview, new_figure, two_circuits

    fig, ax = new_figure()
    two_circuits(ax)
    texts = " ".join(t.get_text() for t in ax.texts)
    assert "Marché\nde gros" in texts and "Réseau de transport" in texts
    plt.close(fig)

    fig = plt.figure()
    market_overview(
        fig,
        [("Production", [("A", 0.7, "#000000"), ("B", 0.03, "#111111"), ("C", 0.27, "#222222")])],
        groups=[(0, "A et B", 0, 1)],
    )
    texts = {t.get_text() for ax in fig.axes for t in ax.texts}
    assert {"Fournisseurs", "Production", "A et B"} <= texts
    assert any(t.startswith("B\n3") for t in texts)  # segment étroit : libellé sous la barre
    plt.close(fig)


def test_flux_kirchhoff_triangle():
    from pyelec.lois import dc_flows

    flows = dc_flows([(0, 1), (0, 2), (2, 1)], [1.0, 1.0, 1.0], [300.0, -300.0, 0.0])
    assert [round(f) for f in flows] == [200, 100, 100]
    # une ligne deux fois plus impédante porte moins
    flows = dc_flows([(0, 1), (0, 2), (2, 1)], [2.0, 1.0, 1.0], [300.0, -300.0, 0.0])
    assert round(flows[0]) == 150 and round(flows[1]) == 150


def test_variabilite_pente_thermosensible():
    import numpy as np
    import pandas as pd

    from pyelec.figures import load_variability

    hours = pd.date_range("2025-01-01", "2025-12-31 23:00", freq="h")
    days = pd.date_range("2025-01-01", "2025-12-31", freq="D")
    temp = pd.Series(np.linspace(0, 25, len(days)), index=days)
    # 2 GW de plus par degré sous 15 °C, consommation plate au-dessus
    daily = 45 + 2 * np.clip(15 - temp, 0, None)
    load = pd.DataFrame(
        {
            "heure_locale": hours.strftime("%Y-%m-%d %H:%M"),
            "consommation_gw": daily.reindex(hours.normalize()).to_numpy(),
        }
    )
    temperature = pd.DataFrame({"date": days.strftime("%Y-%m-%d"), "temperature_c": temp.values})
    fig = plt.figure()
    assert abs(load_variability(fig, load, temperature) - 2) < 1e-6
    plt.close(fig)


def test_graphiques_economie():
    from pyelec import economie

    q, _ = economie.optimum_point()
    assert abs(economie.marginal_cost(q) - economie.marginal_utility_curve(q)) < 1e-9
    assert 0 < q < economie.Q_MAX
    # forme électrique : VOLL, puis partie affine sur laquelle tombe l'optimum
    qv, _ = economie.optimum_point(voll=True)
    assert abs(economie.marginal_cost(qv) - economie.marginal_utility_curve(qv, True)) < 1e-9
    assert economie.Q_RIGID < qv < economie.Q_SATED
    assert economie.marginal_utility_curve(0, voll=True) == economie.VOLL
    assert economie.marginal_utility_curve(economie.Q_MAX, voll=True) == 0
    for draw in [
        economie.fixed_and_variable_costs,
        economie.short_run_marginal_cost,
        economie.merit_order_steps,
        economie.long_run_marginal_cost,
        economie.marginal_utility,
        economie.welfare,
        economie.optimum,
        economie.market,
    ]:
        fig, ax = plt.subplots()
        draw(ax)
        assert ax.lines and not ax.get_xticks().size
        plt.close(fig)
    fig = plt.figure()
    economie.marginal_cost_zoom(fig)
    far, near = fig.axes
    assert near.get_xlim()[1] - near.get_xlim()[0] < far.get_xlim()[1] / 5  # vue rapprochée
    plt.close(fig)
    for voll in (False, True):
        fig, ax = plt.subplots()
        assert economie.optimum(ax, voll=voll) == economie.optimum_point(voll)
        economie.market(ax, voll=voll)
        economie.marginal_utility(ax, voll=voll)
        plt.close(fig)
