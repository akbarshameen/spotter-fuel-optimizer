"""
One-time script: geocode all unique city/state combos from the CSV
and save to fuel/data/city_coords.json.
Run once: venv\Scripts\python build_city_coords.py
"""
import csv, json, time, requests
from pathlib import Path
from collections import defaultdict

CSV = Path("fuel/data/fuel_prices.csv")
OUT = Path("fuel/data/city_coords.json")
HEADERS = {"User-Agent": "FuelRouteOptimizer/1.0"}

# Load existing cache if any
if OUT.exists():
    cache = json.loads(OUT.read_text())
else:
    cache = {}

# Collect unique city/state pairs
cities = set()
with open(CSV, newline="", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        city = row["City"].strip()
        state = row["State"].strip().upper()
        if city and state:
            cities.add((city, state))

todo = [(c, s) for c, s in cities if f"{c},{s}" not in cache]
print(f"Total unique cities: {len(cities)}, need to geocode: {len(todo)}")

for i, (city, state) in enumerate(todo):
    key = f"{city},{state}"
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": f"{city}, {state}, USA", "format": "json", "limit": 1, "countrycodes": "us"},
            headers=HEADERS,
            timeout=10,
        )
        results = r.json()
        if results:
            cache[key] = [float(results[0]["lat"]), float(results[0]["lon"])]
        else:
            cache[key] = None
    except Exception as e:
        print(f"  FAILED {key}: {e}")
        cache[key] = None

    if i % 50 == 0:
        OUT.write_text(json.dumps(cache, indent=2))
        print(f"  [{i+1}/{len(todo)}] saved checkpoint")

    time.sleep(1.1)  # Nominatim rate limit: 1 req/sec

OUT.write_text(json.dumps(cache, indent=2))
print(f"Done. {len(cache)} cities cached to {OUT}")
