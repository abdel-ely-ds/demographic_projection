"""Fetch and cache country demographic data from public APIs.

Data sources:
    - Age pyramid: PopulationPyramid.net (UN WPP 2024)
    - TFR, life expectancy, net migration: World Bank API
"""

from __future__ import annotations

import csv
import io
import json
import urllib.request
from pathlib import Path
from typing import Any

from demoproj.countries import resolve

CACHE_DIR = Path.home() / ".demoproj" / "data"

_WB_BASE = "https://api.worldbank.org/v2/country"
_PP_BASE = "https://www.populationpyramid.net/api/pp"

# World Bank indicator IDs
_TFR = "SP.DYN.TFRT.IN"
_LE = "SP.DYN.LE00.IN"
_NET_MIG = "SM.POP.NETM"
_POP = "SP.POP.TOTL"


def _request(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "demoproj/0.2"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read()


def _get_json(url: str) -> Any:
    return json.loads(_request(url).decode())


def _get_text(url: str) -> str:
    return _request(url).decode()


def _wb_latest(iso2: str, indicator: str, years: str = "2024:2018") -> float | None:
    """Fetch most recent non-null value from the World Bank API."""
    url = f"{_WB_BASE}/{iso2}/indicator/{indicator}?date={years}&format=json&per_page=10"
    data = _get_json(url)
    if len(data) < 2 or not data[1]:
        return None
    for entry in data[1]:
        if entry.get("value") is not None:
            return float(entry["value"])
    return None


def _iso3_to_iso2(iso3: str) -> str:
    """Quick ISO3 -> ISO2 via World Bank country endpoint."""
    url = f"{_WB_BASE}/{iso3}?format=json"
    data = _get_json(url)
    if len(data) < 2 or not data[1]:
        return iso3[:2]
    return data[1][0].get("iso2Code", iso3[:2])


def _fetch_pyramid(m49: int, year: int = 2024) -> list[tuple[int, int, int]]:
    """Fetch age pyramid (5-year groups, both sexes) from PopulationPyramid.net."""
    url = f"{_PP_BASE}/{m49}/{year}/?csv=true"
    text = _get_text(url)
    if not text.strip():
        raise RuntimeError(f"No pyramid data for M49={m49}, year={year}")

    groups: list[tuple[int, int, int]] = []
    reader = csv.reader(io.StringIO(text))
    next(reader)  # skip header
    for row in reader:
        age_str, male, female = row[0], int(row[1]), int(row[2])
        if age_str == "100+":
            groups.append((100, 100, male + female))
        else:
            low, high = age_str.split("-")
            groups.append((int(low), int(high), male + female))
    return groups


def _estimate_fertility_peak(iso3: str) -> tuple[float, float]:
    """Rough fertility-age pattern based on region."""
    late_peak = {"KOR", "JPN", "ITA", "ESP", "CHE", "DEU", "AUT", "NLD", "DNK", "SWE", "NOR", "FIN", "SGP", "HKG", "TWN"}
    early_peak = {"NGA", "NER", "TCD", "MLI", "SOM", "COD", "MOZ", "AGO", "BFA", "ETH", "AFG", "YEM"}
    if iso3 in late_peak:
        return 33.0, 5.5
    if iso3 in early_peak:
        return 25.0, 7.5
    return 29.0, 6.5


def fetch_country(query: str) -> dict[str, Any]:
    """Fetch all demographic data for a country and return as a dict.

    Args:
        query: ISO3 code, country name, or alias (e.g. "KOR", "Japan", "South Korea").

    Returns:
        Dict with keys: iso3, name, groups, tfr, life_expectancy,
        net_migration_rate, fertility_peak, fertility_spread, total_pop.
    """
    iso3, m49, display_name = resolve(query)
    iso2 = _iso3_to_iso2(iso3)

    print(f"  Fetching {display_name} ({iso3})...")
    print(f"    Age pyramid (UN WPP 2024)...", end=" ", flush=True)
    groups = _fetch_pyramid(m49)
    total_pop = sum(c for _, _, c in groups)
    print(f"OK ({total_pop:,} people)")

    print(f"    TFR...", end=" ", flush=True)
    tfr = _wb_latest(iso2, _TFR)
    print(f"{tfr:.2f}" if tfr else "N/A")

    print(f"    Life expectancy...", end=" ", flush=True)
    le = _wb_latest(iso2, _LE)
    print(f"{le:.1f}" if le else "N/A")

    print(f"    Net migration...", end=" ", flush=True)
    net_mig_abs = _wb_latest(iso2, _NET_MIG)
    net_mig_rate = (net_mig_abs / total_pop) if (net_mig_abs is not None and total_pop > 0) else 0.0
    print(f"{net_mig_rate * 1000:+.2f} per 1000" if net_mig_abs else "0 (default)")

    peak, spread = _estimate_fertility_peak(iso3)

    return {
        "iso3": iso3,
        "name": display_name,
        "groups": groups,
        "tfr": tfr or 1.5,
        "life_expectancy": le or 75.0,
        "net_migration_rate": net_mig_rate,
        "fertility_peak": peak,
        "fertility_spread": spread,
        "total_pop": total_pop,
    }


def save_country(data: dict[str, Any]) -> Path:
    """Save fetched country data to the local cache."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / f"{data['iso3'].lower()}.json"
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    return path


def load_country(iso3: str) -> dict[str, Any] | None:
    """Load country data from cache. Returns None if not cached."""
    path = CACHE_DIR / f"{iso3.lower()}.json"
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def list_cached() -> list[str]:
    """Return ISO3 codes of all cached countries."""
    if not CACHE_DIR.exists():
        return []
    return sorted(p.stem.upper() for p in CACHE_DIR.glob("*.json"))


def get_or_fetch(query: str) -> dict[str, Any]:
    """Load from cache if available, otherwise fetch and cache."""
    try:
        iso3, _, _ = resolve(query)
    except ValueError:
        iso3 = query.strip().upper()

    cached = load_country(iso3)
    if cached:
        return cached

    data = fetch_country(query)
    save_country(data)
    return data


_WB_REGIONS: dict[str, tuple[str, str]] = {
    "EU": ("EUU", "European Union"),
    "EUU": ("EUU", "European Union"),
    "EUROPE": ("ECS", "Europe & Central Asia"),
    "ECS": ("ECS", "Europe & Central Asia"),
    "WORLD": ("WLD", "World"),
    "WLD": ("WLD", "World"),
    "AFRICA": ("SSF", "Sub-Saharan Africa"),
    "SSF": ("SSF", "Sub-Saharan Africa"),
    "MENA": ("MEA", "Middle East & North Africa"),
    "MEA": ("MEA", "Middle East & North Africa"),
    "LATAM": ("LCN", "Latin America & Caribbean"),
    "LCN": ("LCN", "Latin America & Caribbean"),
    "ASIA": ("EAS", "East Asia & Pacific"),
    "EAS": ("EAS", "East Asia & Pacific"),
    "SAS": ("SAS", "South Asia"),
    "NAC": ("NAC", "North America"),
}


def fetch_tfr_history(query: str, start: int = 1960, end: int = 2023) -> tuple[str, list[int], list[float]]:
    """Fetch historical TFR time series from the World Bank API.

    Supports both country codes/names and aggregate regions (EU, World, Africa, etc.).
    Returns (display_name, years, tfr_values).
    """
    region = _WB_REGIONS.get(query.strip().upper())
    if region:
        wb_code, display_name = region
    else:
        iso3, _, display_name = resolve(query)
        wb_code = _iso3_to_iso2(iso3)

    url = (
        f"{_WB_BASE}/{wb_code}/indicator/{_TFR}"
        f"?date={start}:{end}&format=json&per_page=200"
    )
    data = _get_json(url)
    if len(data) < 2 or not data[1]:
        raise RuntimeError(f"No TFR history for {display_name}")

    years, values = [], []
    for entry in sorted(data[1], key=lambda e: int(e["date"])):
        if entry.get("value") is not None:
            years.append(int(entry["date"]))
            values.append(float(entry["value"]))

    return display_name, years, values
