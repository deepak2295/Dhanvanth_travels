import os
import requests
from dotenv import load_dotenv
from urllib.parse import quote_plus
import requests

load_dotenv()

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

if not GOOGLE_MAPS_API_KEY:
    raise ValueError("GOOGLE_MAPS_API_KEY not found in environment variables. Please check your .env file.")
else:
    print("✅ Successfully loaded Google Maps API Key from .env")

def get_location_suggestions(query):
    """
    Searches for a location and returns up to 4 specific suggestions within Bengaluru.
    """
    geocode_base_url = "https://maps.googleapis.com/maps/api/geocode/json"
    components_filter = "locality:Bengaluru|country:IN"

    params = {
        'address': query,
        'key': GOOGLE_MAPS_API_KEY,
        'components': components_filter
    }
    response = requests.get(geocode_base_url, params=params).json()

    if response.get('status') == 'OK' and response.get('results'):
        suggestions = []
        for result in response['results'][:4]: # Limit to the top 4 results
            suggestions.append({
                "address": result['formatted_address'],
                "place_id": result['place_id']
            })
        return suggestions
    return []


def is_in_bengaluru(geocode_results):
    """Checks if a geocoded address from Google Maps is within Bengaluru."""
    if not geocode_results:
        return False
    valid_localities = ["Bengaluru", "Bangalore Urban"]
    for component in geocode_results[0].get('address_components', []):
        if any(t in component['types'] for t in ['locality', 'administrative_area_level_2']):
            if component.get('long_name') in valid_localities:
                return True
    return False

def get_route_details(origin_place_id, destination_place_id):
    import requests, os
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    
    url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        "origin": origin_place_id,
        "destination": destination_place_id,
        "key": api_key
    }
    
    response = requests.get(url, params=params).json()
    
    if response.get("status") != "OK":
        print(f"❌ Google Maps API error: {response.get('status')} - {response.get('error_message')}")
        return None  # Don't return empty dict

    route = response["routes"][0]["legs"][0]
    return {
        "distance": route["distance"]["text"],
        "duration": route["duration"]["text"]
    }



def get_readable_address(lat, lng):
    """Converts latitude and longitude to a human-readable address."""
    geocode_url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {'latlng': f'{lat},{lng}', 'key': GOOGLE_MAPS_API_KEY}
    response = requests.get(geocode_url, params=params).json()
    
    if response.get('status') == 'OK':
        return response['results'][0]['formatted_address']
    return "Unknown Address"
