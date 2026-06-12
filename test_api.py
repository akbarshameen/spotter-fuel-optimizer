import requests, json

routes = [
    ("New York, NY", "Los Angeles, CA"),
    ("Chicago, IL", "Houston, TX"),
    ("Seattle, WA", "Miami, FL"),
    ("Boston, MA", "Denver, CO"),
]

for start, finish in routes:
    r = requests.post(
        "http://localhost:8000/api/route/",
        json={"start": start, "finish": finish},
        timeout=60,
    )
    data = r.json()
    if "error" in data:
        print(f"{start} → {finish}: ERROR — {data['error']}")
    else:
        print(f"{start} → {finish}: {data['route']['distance_miles']} miles, "
              f"{len(data['fuel_stops'])} stops, ${data['total_fuel_cost_usd']}")
