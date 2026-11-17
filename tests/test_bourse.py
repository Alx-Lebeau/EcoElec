"""Tests du carnet d'ordres (pyelec.bourse)."""

import pandas as pd
import pytest

from pyelec import bourse

ASSETS = pd.DataFrame(
    {
        "element": ["éolien", "ccg"],
        "filiere": ["eolien", "ccg"],
        "puissance": [300.0, 400.0],
        "cout_variable": [0.0, 100.0],
    }
)


def _orders(book, side):
    rows = book[book["sens"] == side]
    return sorted(zip(rows["quantite"], rows["prix"], strict=True))


def test_producer_sells_at_variable_cost():
    book = bourse.order_book(ASSETS)
    assert _orders(book, "achat") == []
    assert _orders(book, "vente") == [(300, 0), (400, 100)]


def test_supplier_offers_net_position():
    book = bourse.order_book(ASSETS, demand=500)
    assert _orders(book, "achat") == [(200, 100), (300, 0)]
    assert _orders(book, "vente") == [(200, 100)]


@pytest.mark.parametrize("price", [-10, 50, 150])
def test_net_position_matches_portfolio(price):
    """Le carnet net donne, à chaque prix, production moins demande."""
    demand = 500
    book = bourse.order_book(ASSETS, demand)
    sold = book[(book["sens"] == "vente") & (book["prix"] < price)]["quantite"].sum()
    bought = book[(book["sens"] == "achat") & (book["prix"] > price)]["quantite"].sum()
    production = ASSETS.loc[ASSETS["cout_variable"] < price, "puissance"].sum()
    assert sold - bought == production - demand


def test_html_has_one_row_per_order():
    table = bourse.order_book_html(bourse.order_book(ASSETS, 500))
    assert table.count("<tr>") == 2 + 2


def test_clear_partial_seller():
    orders = pd.DataFrame(
        {
            "ordre": ["A1", "A2", "V1", "V2"],
            "sens": ["achat", "achat", "vente", "vente"],
            "volume": [300, 200, 250, 300],
            "prix_limite": [200, 90, 0, 60],
        }
    )
    assert bourse.clear(orders) == (60, 500)
