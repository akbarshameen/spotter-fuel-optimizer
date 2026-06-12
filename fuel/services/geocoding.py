import requests

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
HEADERS = {"User-Agent": "FuelRouteOptimizer/1.0"}


def geocode(location: str) -> tuple[float, float]:
    """Return (lat, lon) for a US location string, or raise ValueError."""
    resp = requests.get(
        NOMINATIM_URL,
        params={"q": location, "format": "json", "limit": 1, "countrycodes": "us"},
        headers=HEADERS,
        timeout=10,
    )
    resp.raise_for_status()
    results = resp.json()
    if not results:
        raise ValueError(f"Location not found: {location}")
    r = results[0]
    return float(r["lat"]), float(r["lon"])
