import requests
import polyline

OSRM_URL = "https://router.project-osrm.org/route/v1/driving"


def get_route(start: tuple[float, float], finish: tuple[float, float]) -> dict:
    """
    Call OSRM once and return:
      {
        "distance_miles": float,
        "geometry": [[lat, lon], ...],   # decoded polyline
      }
    """
    coords = f"{start[1]},{start[0]};{finish[1]},{finish[0]}"
    resp = requests.get(
        f"{OSRM_URL}/{coords}",
        params={"overview": "full", "geometries": "polyline"},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != "Ok":
        raise ValueError("OSRM could not find a route between those locations.")

    route = data["routes"][0]
    distance_miles = route["distance"] / 1609.344
    geometry = polyline.decode(route["geometry"])  # list of (lat, lon)
    return {"distance_miles": distance_miles, "geometry": geometry}
