"""Tests du long terme (pyelec.investment) : annuités, enveloppe, parc optimal."""

import numpy as np
import pandas as pd
import pytest

from pyelec import investment

OPTIONS = pd.DataFrame(
    {"cout_fixe": [50.0, 100.0, 300.0], "cout_variable": [10.0, 5.0, 1.0]},
    index=pd.Index(["pointe", "semi-base", "base"], name="filiere"),
)


def test_annuity_factor():
    assert investment.annuity_factor(0, 20) == pytest.approx(1 / 20)
    # Valeur de référence : 7 % sur 30 ans.
    assert investment.annuity_factor(0.07, 30) == pytest.approx(0.080586, abs=1e-6)


def test_annuity_repays_investment():
    """La valeur actualisée des annuités égale l'investissement."""
    r, n = 0.05, 25
    a = investment.annuity_factor(r, n)
    assert sum(a / (1 + r) ** t for t in range(1, n + 1)) == pytest.approx(1)


def test_envelope_breakeven_hours():
    segments = investment.envelope(OPTIONS, horizon=100)
    assert [s.filiere for s in segments] == ["pointe", "semi-base", "base"]
    assert segments[1].start == pytest.approx(10)  # (100 - 50) / (10 - 5)
    assert segments[2].start == pytest.approx(50)  # (300 - 100) / (5 - 1)


def test_envelope_skips_dominated_option():
    options = pd.concat(
        [OPTIONS, pd.DataFrame({"cout_fixe": [400.0], "cout_variable": [6.0]}, index=["inutile"])]
    )
    assert "inutile" not in [s.filiere for s in investment.envelope(options, horizon=100)]


def test_optimal_fleet_covers_load():
    ldc = np.linspace(100, 0, 100, endpoint=False)
    fleet = investment.optimal_fleet(OPTIONS, ldc)
    assert fleet["capacite"].sum() == pytest.approx(ldc[0])
    assert fleet["energie"].sum() == pytest.approx(ldc.sum() / 1000)
    # Monotone linéaire : la tranche de base vaut la puissance dépassée pendant 50 h.
    assert fleet.loc["base", "capacite"] == pytest.approx(investment.level(ldc, 50))


def test_load_shedding_comes_first():
    """Le délestage, sans coût fixe, sert les toutes premières heures."""
    options = investment.with_load_shedding(OPTIONS)
    first = investment.envelope(options, horizon=100)[0]
    assert first.filiere == "delestage"
    assert first.end == pytest.approx(50 / (investment.load_voll() - 10))
    stylized = investment.with_load_shedding(OPTIONS, hours=3)
    assert investment.envelope(stylized, horizon=100)[0].end == pytest.approx(3)


def test_captured_price_is_weighted_by_production():
    table, mean, captured = investment.capture_price_example()
    assert mean == pytest.approx(table["prix"].mean())
    peak_only = table.loc[table["pointe"] > 0, "prix"]
    assert captured["pointe"] == pytest.approx(peak_only.mean())


def test_rents_cover_fixed_costs():
    """Parc optimal, prix marginal horaire : la rente de chaque filière égale son coût fixe."""
    options = investment.with_load_shedding(investment.load_options(), hours=3)
    prices = investment.hourly_prices(options, investment.load_curve())
    rents = investment.inframarginal_rents(options, prices)
    assert np.allclose(rents["rente"], rents["cout_fixe"], rtol=0.01)
