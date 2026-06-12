from concurrent.futures import ThreadPoolExecutor

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiExample

from .services.geocoding import geocode
from .services.routing import get_route
from .services.optimizer import find_optimal_stops


class FuelRouteView(APIView):

    @extend_schema(
        summary="Find optimal fuel stops along a US driving route",
        description=(
            "Provide a start and finish location within the USA. "
            "Returns the driving route, cheapest fuel stops (500-mile max range, 10 MPG), "
            "route geometry for map rendering, and total fuel cost."
        ),
        request={
            "application/json": {
                "type": "object",
                "required": ["start", "finish"],
                "properties": {
                    "start": {"type": "string", "example": "New York, NY"},
                    "finish": {"type": "string", "example": "Los Angeles, CA"},
                },
            }
        },
        responses={
            200: {
                "type": "object",
                "properties": {
                    "start": {"type": "string"},
                    "finish": {"type": "string"},
                    "route": {
                        "type": "object",
                        "properties": {
                            "distance_miles": {"type": "number"},
                            "map_url": {"type": "string", "description": "Google Maps link with all stops as waypoints"},
                        },
                    },
                    "fuel_stops": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "city": {"type": "string"},
                                "state": {"type": "string"},
                                "price_per_gallon": {"type": "number"},
                                "miles_from_start": {"type": "number"},
                                "lat": {"type": "number"},
                                "lon": {"type": "number"},
                            },
                        },
                    },
                    "total_gallons": {"type": "number"},
                    "total_fuel_cost_usd": {"type": "number"},
                },
            },
            400: {"description": "Missing or invalid input"},
            404: {"description": "Location could not be geocoded"},
            502: {"description": "Routing service unavailable"},
        },
        examples=[
            OpenApiExample(
                "New York to Los Angeles",
                value={"start": "New York, NY", "finish": "Los Angeles, CA"},
                request_only=True,
            )
        ],
    )
    def post(self, request):
        start_str = request.data.get("start", "").strip()
        finish_str = request.data.get("finish", "").strip()

        if not start_str or not finish_str:
            return Response(
                {"error": "Both 'start' and 'finish' fields are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        #nominatim, parallel(max 1 req/sec)
        with ThreadPoolExecutor(max_workers=2) as executor:
            fut_start = executor.submit(geocode, start_str)
            fut_finish = executor.submit(geocode, finish_str)
            try:
                start_coords = fut_start.result()
            except ValueError as e:
                return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
            except Exception:
                return Response({"error": "Geocoding service unavailable."}, status=status.HTTP_502_BAD_GATEWAY)
            try:
                finish_coords = fut_finish.result()
            except ValueError as e:
                return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
            except Exception:
                return Response({"error": "Geocoding service unavailable."}, status=status.HTTP_502_BAD_GATEWAY)

        #osrm, distance+polyline
        try:
            route = get_route(start_coords, finish_coords)
        except Exception as e:
            return Response(
                {"error": f"Routing failed: {str(e)}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        #all fuel stop logic(optimizer) runs locally
        try:
            fuel_result = find_optimal_stops(route["geometry"], route["distance_miles"])
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        stops = fuel_result["stops"]
        map_url = _build_google_maps_url(start_coords, finish_coords, stops)

        return Response({
            "start": start_str,
            "finish": finish_str,
            "route": {
                "distance_miles": round(route["distance_miles"], 1),
                "map_url": map_url,
            },
            "fuel_stops": stops,
            "total_gallons": fuel_result["total_gallons"],
            "total_fuel_cost_usd": fuel_result["total_fuel_cost"],
        })


def _build_google_maps_url(start, finish, stops) -> str:
    
    MAX_WAYPOINTS = 10

    waypoint_stops = stops
    if len(stops) > MAX_WAYPOINTS:
        #picks evenly spaced stops to stay within the limit
        step = len(stops) / MAX_WAYPOINTS
        waypoint_stops = [stops[int(i * step)] for i in range(MAX_WAYPOINTS)]

    base = "https://www.google.com/maps/dir/"
    points = (
        [f"{start[0]},{start[1]}"]
        + [f"{s['lat']},{s['lon']}" for s in waypoint_stops]
        + [f"{finish[0]},{finish[1]}"]
    )
    return base + "/".join(points)
