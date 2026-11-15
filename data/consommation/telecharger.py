"""Télécharge et agrège la consommation finale d'électricité par secteur.

Source : jeu « Consommation départementale annuelle » d'ODRÉ, construit à
partir des données locales de consommation du SDES (Licence Ouverte v2.0).
On somme les départements pour obtenir des totaux nationaux par année et par
secteur, en TWh.

    uv run python data/consommation/telecharger.py
"""

import csv
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

API = "https://odre.opendatasoft.com/api/explore/v2.1/catalog/datasets/conso-departement-annuelle/records"
SECTORS = {
    "residentiel": "e_consor",
    "tertiaire": "e_consot",
    "industrie": "e_consoi",
    "agriculture": "e_consoa",
    "non-affecte": "e_consona",
}
OUTPUT = Path(__file__).with_name("conso-electricite-secteur.csv")


def main() -> None:
    sums = ", ".join(
        f"sum({field}) as {sector.replace('-', '_')}" for sector, field in SECTORS.items()
    )
    query = urlencode(
        {"select": f"annee, {sums}", "group_by": "annee", "order_by": "annee", "limit": 100}
    )
    with urlopen(f"{API}?{query}") as response:
        records = json.load(response)["results"]
    with OUTPUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["annee", "secteur", "consommation_twh"])
        for record in records:
            year = record["annee"][:4]
            for sector in SECTORS:
                mwh = record[sector.replace("-", "_")] or 0.0
                writer.writerow([year, sector, round(mwh / 1e6, 2)])
    print(f"{OUTPUT.name} : {len(records)} années")


if __name__ == "__main__":
    main()
