"""Tests du court terme illustratif (pyelec.dispatch)."""

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
import pytest

from pyelec import dispatch

FLEET = pd.DataFrame(
    {
        "filiere": ["ccg", "renouvelable", "nucleaire"],
        "capacite": [10, 20, 40],
        "cout_variable": [90.0, 0.0, 30.0],
    }
)


def test_gas_plant_costs_formula():
    costs = dispatch.gas_plant_costs()
    plants = dispatch.load_gas_plants()
    p_gas, p_co2 = costs.attrs["prix_gaz"], costs.attrs["prix_co2"]
    for plant, row in plants.iterrows():
        expected = (p_gas + row.facteur_emission * p_co2) / row.rendement + row.vom
        assert costs.loc[plant, "total"] == pytest.approx(expected)
    assert costs.loc["tac", "total"] > costs.loc["ccg", "total"]


def test_merit_order_sorted():
    ordered = dispatch.merit_order(FLEET)
    assert list(ordered["filiere"]) == ["renouvelable", "nucleaire", "ccg"]
    assert list(ordered["fin"]) == [20, 60, 70]


def test_equilibrium_marginal_plant():
    _, ax = plt.subplots()
    eq = dispatch.equilibrium(ax, FLEET, pd.Series({"non_flexible": 60, "flexible": 8}))
    assert eq.marginal == "ccg" and eq.price == 90.0 and eq.unserved == 0
    assert 60 < eq.quantity < 70


def test_equilibrium_scarcity():
    _, ax = plt.subplots()
    eq = dispatch.equilibrium(ax, FLEET, pd.Series({"non_flexible": 75, "flexible": 8}))
    assert eq.scarcity and eq.marginal is None
    assert eq.quantity == 70 and eq.unserved == 5


def test_fleet_files_consistent():
    fleet = dispatch.load_fleet()
    assert fleet["cout_variable"].notna().all()
    assert dispatch.load_demand().loc["tendue", "non_flexible"] > fleet["capacite"].sum()


def test_gas_plants_consistent_basis():
    """Émissions par MWh électrique identiques en base PCS et en base PCI."""
    plants = dispatch.load_gas_plants()
    gas = dispatch.load_natural_gas()
    per_mwh_e = plants["facteur_emission"] / plants["rendement"]
    expected = gas["facteur_emission_pci"] / plants["rendement_pci"]
    assert per_mwh_e.to_numpy() == pytest.approx(expected.to_numpy())
