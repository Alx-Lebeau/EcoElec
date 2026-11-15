"""Télécharge la courbe de charge nationale d'une année et la température quotidienne.

Sources (ODRÉ, Licence Ouverte v2.0) :
- RTE, « Données éCO2mix nationales consolidées et définitives » : consommation
  au pas de 15 ou 30 minutes, moyennée ici par heure (GW) ;
- « Température quotidienne régionale » (Weathernews France) : température
  moyenne des régions, moyennée ici sans pondération (°C).

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

    rows = _export(
        "temperature-quotidienne-regionale",
        "date, tmoy",
        f"date >= date'{year}-01-01' and date <= date'{year}-12-31'",
    )
    daily = defaultdict(list)
    for r in rows:
        if r["tmoy"]:
            daily[r["date"]].append(float(r["tmoy"]))
    with (HERE / f"temperature-{year}.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "temperature_c"])
        for d in sorted(daily):
            writer.writerow([d, round(sum(daily[d]) / len(daily[d]), 2)])
    print(f"{year} : {len(hourly)} heures, {len(daily)} jours")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 2025)
