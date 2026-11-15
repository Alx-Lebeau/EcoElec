"""Télécharge le parc installé et la production annuelle par filière en France.

Source : RTE, jeux ODRÉ « Parc national annuel de production par filière » et
« Production nationale annuelle par filière » (Licence Ouverte v2.0).
Sortie : une ligne par année et par filière, capacité au 31 décembre en GW et
production de l'année en TWh. Le fioul et le charbon, marginaux, sont regroupés.

    uv run python data/mix/telecharger.py
"""

import csv
import json
from pathlib import Path
from urllib.request import urlopen

API = "https://odre.opendatasoft.com/api/explore/v2.1/catalog/datasets/{}/records?limit=100"
OUTPUT = Path(__file__).with_name("mix-france.csv")

# filière → (champs du parc en MW, champs de la production en TWh)
FIELDS = {
    "nucleaire": (["parc_nucleaire"], ["production_nucleaire"]),
    "hydraulique": (["parc_hydraulique"], ["production_hydraulique"]),
    "eolien": (["parc_eolien"], ["production_eolienne"]),
    "solaire": (["parc_solaire"], ["production_solaire"]),
    "gaz": (["parc_gaz"], ["production_thermique_gaz"]),
    "charbon-fioul": (
        ["parc_charbon", "parc_fioul"],
        ["production_thermique_charbon", "production_thermique_fioul"],
    ),
    "bioenergies": (["parc_bioenergie"], ["production_bioenergies"]),
}


def _records(dataset: str) -> dict[str, dict]:
    with urlopen(API.format(dataset)) as response:
        return {r["annee"][:4]: r for r in json.load(response)["results"]}


def _number(value) -> float:
    # Certains champs du parc sont des chaînes à virgule décimale (« 2974,165 »).
    if value is None:
        return float("nan")
    return float(str(value).replace(",", "."))


def main() -> None:
    capacity = _records("parc-prod-par-filiere")
    production = _records("prod-national-annuel-filiere")
    years = sorted(set(capacity) & set(production))
    with OUTPUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["annee", "filiere", "capacite_gw", "production_twh"])
        for year in years:
            for tech, (cap_fields, prod_fields) in FIELDS.items():
                gw = sum(_number(capacity[year][k]) for k in cap_fields) / 1000
                twh = sum(_number(production[year][k]) for k in prod_fields)
                writer.writerow([year, tech, round(gw, 2), round(twh, 1)])
    print(f"{OUTPUT.name} : {years[0]} à {years[-1]}")


if __name__ == "__main__":
    main()
