# /// script
# dependencies = ["pandas>=2.2", "openpyxl>=3.1", "certifi"]
# ///
"""Télécharge le prix mensuel du gaz naturel en Europe (TTF), converti en €/MWh.

Sources :

- Banque mondiale, *Commodity Price Data* (« Pink Sheet »), prix mensuels
  « Natural gas, Europe » en $/mmbtu : TTF néerlandais depuis avril 2015
  (licence CC BY 4.0). L'adresse du classeur change à chaque début d'année :
  la reprendre sur https://www.worldbank.org/en/research/commodity-markets.
- Banque centrale européenne, taux de change mensuel moyen EUR/USD (série
  EXR.M.USD.EUR.SP00.A), pour la conversion en euros.

Sortie : une ligne par mois depuis avril 2015 : prix en $/mmbtu, taux de change
(dollars pour un euro) et prix en €/MWh (1 mmbtu = 0,293071 MWh).

    uv run data/couts/telecharger.py
"""

import io
import ssl
from pathlib import Path
from urllib.request import Request, urlopen

import certifi
import pandas as pd

PINK_SHEET = (
    "https://thedocs.worldbank.org/en/doc/74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/"
    "related/CMO-Historical-Data-Monthly.xlsx"
)
ECB = (
    "https://data-api.ecb.europa.eu/service/data/EXR/M.USD.EUR.SP00.A"
    "?format=csvdata&startPeriod=2015-04"
)
OUTPUT = Path(__file__).with_name("prix-gaz-ttf-mensuel.csv")
MWH_PER_MMBTU = 0.293071
START = "2015-04"  # début de la série TTF dans la Pink Sheet
# Certificats de certifi : la chaîne du serveur de la BCE manque au magasin par défaut.
SSL = ssl.create_default_context(cafile=certifi.where())


def _gas() -> pd.Series:
    # Le serveur de la Banque mondiale refuse l'identifiant par défaut de urllib.
    request = Request(PINK_SHEET, headers={"User-Agent": "EcoElec-telecharger/1.0"})
    with urlopen(request, context=SSL) as response:
        sheet = pd.read_excel(io.BytesIO(response.read()), sheet_name="Monthly Prices", header=4)
    sheet = sheet.rename(columns={sheet.columns[0]: "mois"}).dropna(subset=["mois"])
    sheet["mois"] = sheet["mois"].str.replace("M", "-")
    gas = pd.to_numeric(sheet.set_index("mois")["Natural gas, Europe"], errors="coerce")
    return gas[gas.index >= START].dropna()


def _exchange_rate() -> pd.Series:
    with urlopen(ECB, context=SSL) as response:
        rates = pd.read_csv(response)
    return rates.set_index("TIME_PERIOD")["OBS_VALUE"]


def main() -> None:
    gas = _gas()
    rate = _exchange_rate()
    data = pd.DataFrame({"gaz_usd_mmbtu": gas, "usd_par_eur": rate}).dropna()
    data["gaz_eur_mwh"] = (data["gaz_usd_mmbtu"] / MWH_PER_MMBTU / data["usd_par_eur"]).round(2)
    data["usd_par_eur"] = data["usd_par_eur"].round(4)
    data.index.name = "mois"
    data.to_csv(OUTPUT)
    print(f"{OUTPUT.name} : {data.index[0]} à {data.index[-1]}")


if __name__ == "__main__":
    main()
