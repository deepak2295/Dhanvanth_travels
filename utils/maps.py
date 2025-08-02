# utils/maps.py

import os
import requests
from dotenv import load_dotenv

# This automatically finds and loads your .env file
load_dotenv()

# Reads the API key from your environment
Maps_API_KEY = os.getenv("MAPS_API_KEY")
print("✅ Loaded Google Maps Key from .env")

if not Maps_API_KEY:
    raise ValueError("Maps_API_KEY not found in environment variables. Please check your .env file.")

def is_in_bengaluru(geocode_results):
    """Checks if a geocoded address from Google Maps is within Bengaluru."""
    if not geocode_results:
        return False

    # Valid names for Bengaluru in Google Maps address components
    valid_localities = ["Bengaluru", "Bangalore Urban"]
    
    # Check the address components for a match
    for component in geocode_results[0].get('address_components', []):
        if any(t in component['types'] for t in ['locality', 'administrative_area_level_2']):
            if component.get('long_name') in valid_localities:
                return True
    return False

def get_route_details(pickup, drop):
    """
    Gets route details, biasing the search to and restricting the results to the Bengaluru area.
    """
    geocode_base_url = "https://maps.googleapis.com/maps/api/geocode/json"
    directions_base_url = "https://maps.googleapis.com/maps/api/directions/json"
    
    # This tells Google to strongly prefer results within Bengaluru, India
    components_filter = "locality:Bengaluru|country:IN"

    # 1. Geocode and validate the PICKUP location
    origin_params = {'address': pickup, 'key': Maps_API_KEY, 'components': components_filter}
    origin_res = requests.get(geocode_base_url, params=origin_params).json()
    
    if not origin_res.get('results') or not is_in_bengaluru(origin_res.get('results')):
        return {"error": f"Sorry, the pickup location '{pickup}' is outside our service area (Bengaluru)."}
    origin_place_id = origin_res['results'][0]['place_id']

    # 2. Geocode and validate the DROP-OFF location
    dest_params = {'address': drop, 'key': Maps_API_KEY, 'components': components_filter}
    dest_res = requests.get(geocode_base_url, params=dest_params).json()

    if not dest_res.get('results') or not is_in_bengaluru(dest_res.get('results')):
        return {"error": f"Sorry, the drop-off location '{drop}' is outside our service area (Bengaluru)."}
    destination_place_id = dest_res['results'][0]['place_id']

    # 3. Get directions using the validated place_ids for accuracy
    directions_params = {
        'origin': f'place_id:{origin_place_id}',
        'destination': f'place_id:{destination_place_id}',
        'key': Maps_API_KEY
    }
    directions_res = requests.get(directions_base_url, params=directions_params).json()

    if directions_res.get('status') == 'OK':
        leg = directions_res['routes'][0]['legs'][0]
        return {
            "distance": leg["distance"]["text"],
            "duration": leg["duration"]["text"]
        }
    else:
        print(f"❌ Error getting route details: {directions_res.get('status')}")
        return {"error": "A route could not be found between the specified locations."}

def get_readable_address(lat, lng):
    """Converts latitude and longitude to a human-readable address."""
    geocode_url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {'latlng': f'{lat},{lng}', 'key': Maps_API_KEY}
    response = requests.get(geocode_url, params=params).json()
    
    if response.get('status') == 'OK':
        return response['results'][0]['formatted_address']
    return "Unknown Address"