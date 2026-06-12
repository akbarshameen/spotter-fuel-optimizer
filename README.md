# Fuel Route Optimizer API

A Django REST API that finds the cheapest fuel stops along any US driving route.

## Live Demo

**API:** https://web-production-bffe9.up.railway.app/api/route/  
**Swagger UI:** https://web-production-bffe9.up.railway.app/api/schema/swagger-ui/

## What it does

Given a start and finish location within the USA, the API returns:
- Total driving distance in miles
- Optimal fuel stops (cheapest prices along the route)
- Total fuel cost
- Google Maps link with all stops as waypoints

**Vehicle assumptions:** 500-mile tank range, 10 MPG

## How it works

1. **Geocoding** — Converts city names to coordinates using Nominatim (run in parallel)
2. **Routing** — Gets the driving route and road geometry from OSRM
3. **Optimization** — Greedy algorithm picks the cheapest station within each 500-mile window
4. **Cost calculation** — Each route leg is priced at the station fueled before it

Only 3 external API calls per request (2 geocoding + 1 routing). All fuel optimization runs locally against the provided CSV dataset.

## API Usage

**POST** `/api/route/`

```json
{
  "start": "New York, NY",
  "finish": "Los Angeles, CA"
}
```

**Response:**
```json
{
  "start": "New York, NY",
  "finish": "Los Angeles, CA",
  "route": {
    "distance_miles": 2798.2,
    "map_url": "https://www.google.com/maps/dir/..."
  },
  "fuel_stops": [
    {
      "name": "SHEETZ #770",
      "city": "London",
      "state": "OH",
      "price_per_gallon": 2.999,
      "miles_from_start": 556.8,
      "lat": 41.59984,
      "lon": -83.902443
    }
  ],
  "total_gallons": 279.82,
  "total_fuel_cost_usd": 848.67
}
```

## Tech Stack

- Python 3.13
- Django 5.2 + Django REST Framework
- drf-spectacular (Swagger UI)
- OSRM (free routing, no API key)
- Nominatim / OpenStreetMap (free geocoding, no API key)
- Deployed on Railway

## Running Locally

```bash
git clone https://github.com/akbarshameen/spotter-fuel-optimizer.git
cd spotter-fuel-optimizer
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
python manage.py runserver
```

API available at `http://localhost:8000/api/route/`  
Swagger UI at `http://localhost:8000/api/schema/swagger-ui/`
