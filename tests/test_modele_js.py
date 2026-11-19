"""Le modèle JavaScript de l'outil retrouve les résultats de pyelec.case_study.

Exécute `modules/cas-enr-investissement/modele.js` avec Node (ignoré si Node est
absent, sauf en CI) sur les scénarios des questions et compare les indicateurs à ceux du Python.
"""

import json
import math
import os
import shutil
import subprocess

import pytest

from pyelec import ROOT
from pyelec import case_study as cs

NODE = shutil.which("node")
MODEL = ROOT / "modules" / "cas-enr-investissement" / "modele.js"

SCRIPT = """
import { readFileSync } from "node:fs";
import * as m from "./modele.mjs";
const data = JSON.parse(readFileSync("donnees.json", "utf8"));
const out = {};
for (const [name, sc] of Object.entries(JSON.parse(readFileSync("scenarios.json", "utf8")))) {
  const c = m.buildCase(data, sc.params);
  const caps = sc.caps ?? m.optimalFleet(c, sc.solar === undefined ? 0 : sc.solar);
  out[name] = { caps, summary: m.summary(c, caps) };
}
console.log(JSON.stringify(out));
"""


def _scenarios(case: cs.Case) -> dict:
    """Scénarios des questions : (cas Python, paramètres JS, capacités ou solaire)."""
    ref = cs.optimal_fleet(case)
    _, mid, high = cs.solar_levels()
    solar_cf = case.options.loc[cs.SOLAR, "cout_fixe"] * (1 - cs.SOLAR_COST_CUT)
    return {
        "q1": (case, {}, None, 0.0),
        "q2": (case, {}, {**ref, "nucleaire": ref["nucleaire"] * (1 - cs.NUCLEAR_CUT)}, None),
        "q3_court": (case.with_co2(cs.CO2_PRICES[0]), {"co2": cs.CO2_PRICES[0]}, ref, None),
        "q3_long": (case.with_co2(cs.CO2_PRICES[1]), {"co2": cs.CO2_PRICES[1]}, None, 0.0),
        "q4_court": (case, {}, {**ref, cs.SOLAR: high}, None),
        "q4_long": (case, {}, None, mid),
        "q5_reel": (case, {}, None, "libre"),
        "q5_constant": (case.with_constant_solar(), {"profil": "constant"}, None, "libre"),
        "q5_cout": (
            case.with_costs(solaire=solar_cf),
            {"coutFixe": {cs.SOLAR: solar_cf}},
            None,
            "libre",
        ),
    }


def _close(a: float, b: float, rel: float = 1e-6, abs_: float = 1e-6) -> bool:
    if isinstance(a, float) and math.isnan(a):
        return b is None or (isinstance(b, float) and math.isnan(b))
    return b is not None and math.isclose(a, b, rel_tol=rel, abs_tol=abs_)


# Ignoré sans Node en local, jamais en CI (variable CI posée par GitHub Actions).
@pytest.mark.skipif(NODE is None and not os.environ.get("CI"), reason="Node absent")
def test_js_matches_python(tmp_path):
    assert NODE is not None, "Node introuvable : installer Node pour tester les outils"
    case = cs.load_case()
    scenarios = _scenarios(case)
    js_input = {}
    for name, (_, params, caps, solar) in scenarios.items():
        entry = {"params": params}
        if caps is not None:
            entry["caps"] = caps
        else:
            entry["solar"] = None if solar == "libre" else solar
        js_input[name] = entry
    (tmp_path / "donnees.json").write_text(json.dumps(cs.tool_data()))
    (tmp_path / "scenarios.json").write_text(json.dumps(js_input))
    shutil.copy(MODEL, tmp_path / "modele.mjs")
    (tmp_path / "test.mjs").write_text(SCRIPT)
    run = subprocess.run(
        [NODE, "test.mjs"], cwd=tmp_path, capture_output=True, text=True, check=True
    )
    results = json.loads(run.stdout)

    for name, (py_case, _, caps, solar) in scenarios.items():
        if caps is None:
            caps = cs.optimal_fleet(py_case, None if solar == "libre" else solar)
        js = results[name]
        # Données arrondies à l'export (facteur de charge à 5 décimales) ; recherche par
        # section dorée : même algorithme, tolérance plus large.
        tol = 1e-3 if solar == "libre" else 1e-4
        for f, v in caps.items():
            assert _close(float(v), js["caps"][f], rel=tol, abs_=tol), (name, f)
        py = cs.summary(py_case, caps)
        for key in (
            "cout_total",
            "prix_moyen",
            "delestage",
            "ecretement",
            "subvention_solaire",
            "emissions_totales",
        ):
            # Subvention en M€/an, proche de zéro quand le solaire est choisi : écart absolu.
            abs_ = 1.0 if key == "subvention_solaire" else 1e-6
            assert _close(float(py[key]), js["summary"][key], rel=tol, abs_=abs_), (name, key)
        assert py["heures_delestage"] == js["summary"]["heures_delestage"], name
        for key in ("energie", "rente_inframarginale", "profit", "emissions"):
            for f in py[key]:
                assert _close(float(py[key][f]), js["summary"][key][f], rel=tol, abs_=1e-3), (
                    name,
                    key,
                    f,
                )
