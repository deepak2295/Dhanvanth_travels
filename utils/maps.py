# utils/maps.py

import requests
import os
# Your OpenRouteService API key
API_KEY = os.getenv("ORS_API_KEY")

def get_route_details(pickup, drop):
    """
    Uses OpenRouteService to get distance, duration, and tracking URL between pickup and drop.
    """
    geocode_url = "https://api.openrouteservice.org/geocode/search"
    directions_url = "https://api.openrouteservice.org/v2/directions/driving-car"

    # Geocode addresses
    pickup_coords = get_coordinates(pickup, geocode_url)
    drop_coords = get_coordinates(drop, geocode_url)

    if not pickup_coords or not drop_coords:
        return None

    # Directions
    headers = {
        "Authorization": API_KEY,
        "Content-Type": "application/json"
    }
    body = {
        "coordinates": [pickup_coords, drop_coords]
    }
    response = requests.post(directions_url, json=body, headers=headers)
    data = response.json()

    try:
        summary = data["features"][0]["properties"]["summary"]
        distance_km = round(summary["distance"] / 1000, 2)
        duration_min = round(summary["duration"] / 60, 2)
        fare = calculate_fare(distance_km)

        return {
            "distance": f"{distance_km} km",
            "duration": f"{duration_min} mins",
            "fare": fare,
            "tracking_url": f"https://www.openstreetmap.org/directions?engine=graphhopper_car&route={pickup_coords[1]},{pickup_coords[0]};{drop_coords[1]},{drop_coords[0]}"
        }
    except Exception as e:
        print("Error parsing directions:", e)
        return None

def get_coordinates(location, geocode_url):
    """Get lat/lon from place name"""
    params = {
        "api_key": API_KEY,
        "text": location,
        "size": 1
    }
    response = requests.get(geocode_url, params=params)
    try:
        coords = response.json()["features"][0]["geometry"]["coordinates"]
        return coords  # [lon, lat]
    except:
        return None

def calculate_fare(km):
    base = 50
    per_km = 15
    return round(base + max(0, km - 3) * per_km, 2)
