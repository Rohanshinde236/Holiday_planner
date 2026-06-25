"""
Holiday calendar — search festivals and look up their dates across years.

Primary source: the `holidays` library (offline, handles moving lunar dates).
Supplement: a small CURATED table for festivals the library omits (e.g. Ganesh
Chaturthi) or regional ones. Curated dates are verified manually; extend as needed.

This is a lookup feature, not WFM math — no formula here.
"""

import holidays as _hol

# Queue-region -> representative countries (ISO codes), per DESIGN.md §5.1.
COUNTRY_REGIONS = {
    "APJ": ["IN", "AU", "JP", "SG"],
    "EMEA": ["GB", "DE", "AE", "ZA"],
    "AMER": ["US", "CA"],
    "LATAM": ["BR", "MX", "AR"],
}
COUNTRY_NAMES = {
    "IN": "India", "AU": "Australia", "JP": "Japan", "SG": "Singapore",
    "GB": "United Kingdom", "DE": "Germany", "AE": "UAE", "ZA": "South Africa",
    "US": "United States", "CA": "Canada", "BR": "Brazil", "MX": "Mexico", "AR": "Argentina",
}

# Curated supplement: festivals missing from the `holidays` library.
# Format: {country: {festival_name: {year: "YYYY-MM-DD"}}}
_CURATED = {
    "IN": {
        "Ganesh Chaturthi": {
            2021: "2021-09-10", 2022: "2022-08-31", 2023: "2023-09-19",
            2024: "2024-09-07", 2025: "2025-08-27", 2026: "2026-09-14",
        },
    },
}


def _lib_holidays(country: str, years):
    try:
        return _hol.country_holidays(country, years=years)
    except Exception:
        return {}


def list_countries() -> dict:
    """Supported countries grouped by queue region."""
    return {
        region: [{"code": c, "name": COUNTRY_NAMES.get(c, c)} for c in codes]
        for region, codes in COUNTRY_REGIONS.items()
    }


def search(query: str, country: str = "IN", base_year: int = 2025) -> list:
    """Typeahead: festival names (library + curated) matching the query."""
    years = [base_year - 1, base_year, base_year + 1]
    names = set()
    for n in _lib_holidays(country, years).values():
        for part in str(n).split(";"):
            names.add(part.strip())
    names.update(_CURATED.get(country, {}).keys())

    q = (query or "").lower().strip()
    matches = [n for n in names if q in n.lower()] if q else sorted(names)
    return sorted(matches)


def _date_for(name: str, country: str, year: int):
    """Date string for one festival in one year (curated first, then library)."""
    want = name.lower().strip()
    cur = _CURATED.get(country, {}).get(name)
    if cur and year in cur:
        return cur[year]
    for d, n in _lib_holidays(country, year).items():
        parts = [p.strip().lower() for p in str(n).split(";")]
        if want in parts or want in str(n).lower():
            return str(d)
    return None


def dates(name: str, country: str = "IN", base_year: int = 2025, years: int = 2) -> dict:
    """
    Date for the plan year + the previous `years` occurrences (Y1, Y2, ...).
    Handles moving lunar festivals correctly (each year looked up independently).
    """
    history = []
    for offset in range(1, years + 1):
        yr = base_year - offset
        history.append({"slot": f"Y{offset}", "year": yr, "date": _date_for(name, country, yr)})
    return {
        "name": name,
        "country": country,
        "plan_year": base_year,
        "plan_date": _date_for(name, country, base_year),
        "history": history,
    }
