"""Télécharge la courbe de charge nationale d'une année.

Source : RTE, « Données éCO2mix nationales consolidées et définitives » (ODRÉ,
Licence Ouverte v2.0) : consommation au pas de 15 ou 30 minutes, moyennée ici
par heure (GW). La température est téléchargée par `telecharger_temperature.py`.

    uv run python data/consommation/telecharger_courbe.py 2025
"""

import csv
import io
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
from zoneinfo import ZoneInfo

API = "https://odre.opendatasoft.com/api/explore/v2.1/catalog/datasets/{}/exports/csv"
HERE = Path(__file__).parent
PARIS = ZoneInfo("Europe/Paris")


def _export(dataset: str, select: str, where: str) -> list[dict]:
    query = urlencode({"select": select, "where": where, "delimiter": ";", "timezone": "UTC"})
    with urlopen(f"{API.format(dataset)}?{query}") as response:
        return list(csv.DictReader(io.StringIO(response.read().decode("utf-8-sig")), delimiter=";"))


def main(year: int) -> None:
    where = (
        f"date_heure >= '{year - 1}-12-31T00:00:00' and date_heure < '{year + 1}-01-02T00:00:00'"
    )
    rows = _export("eco2mix-national-cons-def", "date_heure, consommation", where)
    hourly = defaultdict(list)
    for r in rows:
        if not r["consommation"]:
            continue
        t = datetime.fromisoformat(r["date_heure"]).astimezone(PARIS)
        if t.year == year:
            hourly[t.replace(minute=0)].append(float(r["consommation"]))
    with (HERE / f"courbe-charge-{year}.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["heure_locale", "consommation_gw"])
        for t in sorted(hourly):
            values = hourly[t]
            writer.writerow(
                [t.strftime("%Y-%m-%d %H:%M"), round(sum(values) / len(values) / 1000, 2)]
            )

    print(f"{year} : {len(hourly)} heures")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 2025)
