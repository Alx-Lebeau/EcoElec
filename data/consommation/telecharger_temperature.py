"""Température moyenne quotidienne de la France métropolitaine, pondérée par la consommation.

Sources (Licence Ouverte v2.0) :
- Météo-France, « Données climatologiques de base - quotidiennes » (data.gouv.fr) :
  fichiers départementaux, champ TNTXM, moyenne (TN + TX) / 2 en °C ;
- ODRÉ, « Consommation départementale annuelle » (SDES) : consommation électrique
  résidentielle et tertiaire de chaque département, qui sert de pondération
  (ces secteurs portent la thermosensibilité).

Traitement : moyenne des stations de chaque département (stations de plus de
800 m exclues, peu représentatives des lieux de consommation), puis moyenne des
départements pondérée par leur consommation résidentielle et tertiaire.

    uv run python data/consommation/telecharger_temperature.py 2025
"""

import csv
import gzip
import json
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

HERE = Path(__file__).parent
CACHE = HERE.parent / "telechargements" / "meteo-france"
METEO = "https://meteofrance.s3.sbg.io.cloud.ovh.net/data/synchro_ftp/BASE/QUOT/Q_{}_latest-{}-{}_RR-T-Vent.csv.gz"
ODRE = "https://odre.opendatasoft.com/api/explore/v2.1/catalog/datasets/conso-departement-annuelle/records"
DEPARTMENTS = [f"{d:02d}" for d in range(1, 96)]  # métropole ; Corse : « 20 » chez Météo-France
MAX_ALTITUDE = 800


def _weights() -> dict[str, float]:
    """Consommation résidentielle et tertiaire (MWh) par département, dernière année publiée."""
    query = urlencode(
        {
            "select": "annee, code_departement, e_consor, e_consot",
            "order_by": "annee desc",
            "limit": 100,
        }
    )
    with urlopen(f"{ODRE}?{query}") as response:
        records = json.load(response)["results"]
    latest = records[0]["annee"]
    weights = defaultdict(float)
    for r in records:
        if r["annee"] != latest:
            continue
        code = "20" if r["code_departement"] in ("2A", "2B") else r["code_departement"]
        weights[code] += (r["e_consor"] or 0) + (r["e_consot"] or 0)
    return weights


def _department(code: str, year: int) -> dict[str, float]:
    """Température moyenne quotidienne des stations du département (date AAAAMMJJ → °C)."""
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"Q_{code}_{year}.csv.gz"
    if not path.exists():
        with urlopen(METEO.format(code, year, year + 1)) as response:
            path.write_bytes(response.read())
    values = defaultdict(list)
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter=";"):
            day = r["AAAAMMJJ"]
            if not day.startswith(str(year)) or not r["TNTXM"].strip():
                continue
            if r["ALTI"].strip() and float(r["ALTI"]) > MAX_ALTITUDE:
                continue
            values[day].append(float(r["TNTXM"]))
    return {day: sum(v) / len(v) for day, v in values.items()}


def main(year: int) -> None:
    weights = _weights()
    total = defaultdict(float)
    weight_sum = defaultdict(float)
    for code in DEPARTMENTS:
        if code not in weights:
            continue
        for day, temperature in _department(code, year).items():
            total[day] += weights[code] * temperature
            weight_sum[day] += weights[code]
    with (HERE / f"temperature-{year}.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "temperature_c"])
        for day in sorted(total):
            date = f"{day[:4]}-{day[4:6]}-{day[6:]}"
            writer.writerow([date, round(total[day] / weight_sum[day], 2)])
    print(f"{year} : {len(total)} jours")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 2025)
