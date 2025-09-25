import requests
from typing import Optional, List, Tuple
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class DistanceCalculation:
    @staticmethod
    def geocode_openroute( location: str, api_key: str):
        try:
            url = f"https://api.openrouteservice.org/geocode/search"
            
            headers = {
                'Authorization': api_key
            }
            
            params = {
                'text': location,
                'size': 1
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data['features']:
                    coords = data['features'][0]['geometry']['coordinates']
                    return [coords[0], coords[1]]  # [longitude, latitude]
                    
        except Exception as e:
            logger.error(f"Geocoding error for {location}: {e}")
            
        return None
    def calculate_openroute_distance(self, coordinates: List[Tuple[float, float]]) -> Optional[float]:
        """Calculate distance using OpenRouteService routing API"""
        api_key = settings.OPENROUTE_API_KEY
        try:
            url = "https://api.openrouteservice.org/v2/directions/driving-car"
            
            headers = {
                'Authorization': api_key,
                'Content-Type': 'application/json'
            }
            
            # Convert coordinates to the format OpenRouteService expects
            coord_array = [[lon, lat] for lon, lat in coordinates]
            
            body = {
                "coordinates": coord_array,
                "format": "json"
            }
            
            response = requests.post(url, json=body, headers=headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('routes'):
                    # Distance is in meters, convert to miles
                    distance_meters = data['routes'][0]['summary']['distance']
                    distance_miles = distance_meters * 0.000621371
                    return round(distance_miles, 1)
                
        except Exception as e:
            print(f"OpenRouteService API error: {e}")
            return None
        
    # def calculate_distance_openroute(self, origin: str, pickup: str, destination: str):
    
    #     # api_key = os.getenv('OPENROUTE_API_KEY')
    #     api_key = settings.OPENROUTE_API_KEY
    #     if not api_key:
    #         return None
            
    #     try:
    #         # Geocode locations first
    #         locations = [origin, pickup, destination]
    #         coordinates = []
            
    #         for location in locations:
    #             coord = self.geocode_openroute(location, api_key)
    #             if coord:
    #                 coordinates.append(coord)
    #             else:
    #                 return None
            
    #         # Calculate route distance
    #         url = "https://api.openrouteservice.org/v2/directions/driving-car"
            
    #         headers = {
    #             'Authorization': api_key,
    #             'Content-Type': 'application/json'
    #         }
            
    #         body = {
    #             "coordinates": coordinates,
    #             "format": "json",
    #             "units": "mi"
    #         }
            
    #         response = requests.post(url, json=body, headers=headers, timeout=10)
            
    #         if response.status_code == 200:
    #             data = response.json()
    #             # Distance is in meters, convert to miles
    #             distance_meters = data['routes'][0]['summary']['distance']
    #             distance_miles = distance_meters * 0.000621371  # meters to miles
    #             print("Distance Miles:", distance_miles)
    #             return round(distance_miles, 1)
                
    #     except Exception as e:
    #         print(f"OpenRouteService API error: {e}")
    #         return None
    

   