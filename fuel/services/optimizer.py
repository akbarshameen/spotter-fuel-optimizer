import csv
import math
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "fuel_prices.csv"
MAX_RANGE_MILES = 500
MPG = 10
POLYLINE_STEP = 50


def _haversine(lat1, lon1, lat2, lon2) -> float:
    R = 3958.8
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    a = (math.sin((phi2 - phi1) / 2) ** 2
         + math.cos(phi1) * math.cos(phi2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


STATE_CENTROIDS = {
    "AL": (32.806671, -86.791130), "AK": (61.370716, -152.404419),
    "AZ": (33.729759, -111.431221), "AR": (34.969704, -92.373123),
    "CA": (36.116203, -119.681564), "CO": (39.059811, -105.311104),
    "CT": (41.597782, -72.755371), "DE": (39.318523, -75.507141),
    "FL": (27.766279, -81.686783), "GA": (33.040619, -83.643074),
    "HI": (21.094318, -157.498337), "ID": (44.240459, -114.478828),
    "IL": (40.349457, -88.986137), "IN": (39.849426, -86.258278),
    "IA": (42.011539, -93.210526), "KS": (38.526600, -96.726486),
    "KY": (37.668140, -84.670067), "LA": (31.169960, -91.867805),
    "ME": (44.693947, -69.381927), "MD": (39.063946, -76.802101),
    "MA": (42.230171, -71.530106), "MI": (43.326618, -84.536095),
    "MN": (45.694454, -93.900192), "MS": (32.741646, -89.678696),
    "MO": (38.456085, -92.288368), "MT": (46.921925, -110.454353),
    "NE": (41.125370, -98.268082), "NV": (38.313515, -117.055374),
    "NH": (43.452492, -71.563896), "NJ": (40.298904, -74.521011),
    "NM": (34.840515, -106.248482), "NY": (42.165726, -74.948051),
    "NC": (35.630066, -79.806419), "ND": (47.528912, -99.784012),
    "OH": (40.388783, -82.764915), "OK": (35.565342, -96.928917),
    "OR": (44.572021, -122.070938), "PA": (40.590752, -77.209755),
    "RI": (41.680893, -71.511780), "SC": (33.856892, -80.945007),
    "SD": (44.299782, -99.438828), "TN": (35.747845, -86.692345),
    "TX": (31.054487, -97.563461), "UT": (40.150032, -111.862434),
    "VT": (44.045876, -72.710686), "VA": (37.769337, -78.169968),
    "WA": (47.400902, -121.490494), "WV": (38.491226, -80.954453),
    "WI": (44.268543, -89.616508), "WY": (42.755966, -107.302490),
    "DC": (38.897438, -77.026817),
}


def _load_stations() -> list[dict]:
    stations = []
    with open(DATA_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            state = row["State"].strip().upper()
            if state not in STATE_CENTROIDS:
                continue
            try:
                price = float(row["Retail Price"])
            except (ValueError, KeyError):
                continue
            stations.append({
                "name": row["Truckstop Name"].strip(),
                "city": row["City"].strip(),
                "state": state,
                "price": price,
            })
    return stations
#only contains city and state

def _build_sampled_route(geometry: list) -> tuple[list, list]:
    sampled = geometry[::POLYLINE_STEP]
    if sampled[-1] != geometry[-1]:
        sampled.append(geometry[-1])
    cum = [0.0]
    for i in range(1, len(sampled)):
        cum.append(cum[-1] + _haversine(*sampled[i - 1], *sampled[i]))
    return sampled, cum


def _state_mile_ranges(sampled: list, cum: list) -> dict[str, tuple[float, float]]:
    #finds the nearest state centroid. tells me which miles each state occupies on the route, for eg Ohio covers miles 310 to 560
    #can't geocode 3,900 cities in real time, so you approximate by placing them on the route based on their state.
    ranges: dict[str, list] = {}
    for i, (rlat, rlon) in enumerate(sampled):
        best_state, best_d = None, float("inf")
        for state, (clat, clon) in STATE_CENTROIDS.items():
            d = (rlat - clat) ** 2 + (rlon - clon) ** 2
            if d < best_d:
                best_d = d
                best_state = state
        if best_state:
            if best_state not in ranges:
                ranges[best_state] = [cum[i], cum[i]]
            else:
                ranges[best_state][0] = min(ranges[best_state][0], cum[i])
                ranges[best_state][1] = max(ranges[best_state][1], cum[i])

    return {s: (r[0], r[1]) for s, r in ranges.items()}


def _coords_at_mile(target_miles: float, sampled: list, cum: list) -> tuple[float, float]:
    for i in range(len(cum) - 1):
        if cum[i] <= target_miles <= cum[i + 1]:
            seg = cum[i + 1] - cum[i]
            t = (target_miles - cum[i]) / seg if seg > 0 else 0
            lat = sampled[i][0] + t * (sampled[i + 1][0] - sampled[i][0])
            lon = sampled[i][1] + t * (sampled[i + 1][1] - sampled[i][1])
            return lat, lon
    return sampled[-1]


def find_optimal_stops(geometry: list, total_miles: float) -> dict:
   #i spread each state's stations evenly across the mile range so the greedy algo can find the station
   #from my current position, find all stations within the next 500 miles,that's the tank range at 10 MPG and pick the cheapest one. Repeat until I can reach the finish on a single tank
    all_stations = _load_stations()
    sampled, cum = _build_sampled_route(geometry)
    state_ranges = _state_mile_ranges(sampled, cum)

    by_state: dict[str, list] = {}
    for s in all_stations:
        if s["state"] in state_ranges:
            by_state.setdefault(s["state"], []).append(s)

    route_stations = []
    for state, stations in by_state.items():
        min_mile, max_mile = state_ranges[state]
        n = len(stations)
        for i, s in enumerate(stations):
            if n == 1:
                pos = (min_mile + max_mile) / 2
            else:
                pos = min_mile + (i / (n - 1)) * (max_mile - min_mile)
            route_stations.append({**s, "route_miles": pos})

    route_stations.sort(key=lambda s: s["route_miles"])

    stops = []
    current_pos = 0.0

    while current_pos < total_miles:
        if total_miles - current_pos <= MAX_RANGE_MILES:
            break

        reachable = [
            s for s in route_stations
            if current_pos + 50 < s["route_miles"] <= current_pos + MAX_RANGE_MILES
        ]

        if not reachable:
            raise ValueError(
                f"No fuel station found within {MAX_RANGE_MILES} miles of "
                f"mile marker {current_pos:.0f}. Cannot complete route."
            )

        best = min(reachable, key=lambda s: s["price"])
        lat, lon = _coords_at_mile(best["route_miles"], sampled, cum)
        stops.append({
            "name": best["name"],
            "city": best["city"],
            "state": best["state"],
            "price_per_gallon": round(best["price"], 4),
            "miles_from_start": round(best["route_miles"], 1),
            "lat": round(lat, 6),
            "lon": round(lon, 6),
        })
        current_pos = best["route_miles"]

#cost is calculated per leg
#each segment is priced at the station fueled before it. 
#leg miles/10 to give gallons, multiplied by price, to get toal cost. 
    positions = [0.0] + [s["miles_from_start"] for s in stops] + [total_miles]
    leg_prices = ([stops[0]["price_per_gallon"]] if stops else []) + [s["price_per_gallon"] for s in stops]

    total_cost = 0.0
    for i in range(len(positions) - 1):
        seg = positions[i + 1] - positions[i]
        price = leg_prices[min(i, len(leg_prices) - 1)] if leg_prices else 0.0
        total_cost += (seg / MPG) * price

    return {
        "stops": stops,
        "total_gallons": round(total_miles / MPG, 2),
        "total_fuel_cost": round(total_cost, 2),
    }
