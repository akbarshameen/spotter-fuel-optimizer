import sys, os
sys.path.insert(0, '.')
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
import django; django.setup()

from fuel.services.optimizer import _load_stations, _build_sampled_route, _route_states, _snap_to_route, CORRIDOR_MILES
from fuel.services.routing import get_route
from fuel.services.geocoding import geocode
import math

start_coords = geocode("Seattle, WA")
finish_coords = geocode("San Diego, CA")
print(f"Start: {start_coords}, Finish: {finish_coords}")

route = get_route(start_coords, finish_coords)
geometry = route["geometry"]
sampled, cum = _build_sampled_route(geometry)
total = route["distance_miles"]
print(f"Route: {total:.0f} miles, {len(geometry)} raw points, {len(sampled)} sampled")

states = _route_states(sampled)
print(f"Route states: {sorted(states)}")

# Show snapping for each state
stations = _load_stations()
by_state = {}
for s in stations:
    by_state.setdefault(s["state"], []).append(s)

for state in sorted(states):
    if state not in by_state:
        continue
    sample = by_state[state][0]
    pos = _snap_to_route(sample["lat"], sample["lon"], sampled, cum)
    # find nearest distance too
    from fuel.services.optimizer import _haversine
    min_d = min(_haversine(sample["lat"], sample["lon"], lat, lon) for lat, lon in sampled)
    print(f"  {state}: centroid ({sample['lat']:.2f}, {sample['lon']:.2f}), nearest_vertex_dist={min_d:.0f}mi, route_pos={pos}")
