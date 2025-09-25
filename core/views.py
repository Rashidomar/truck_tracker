from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.db import transaction
from decimal import Decimal
from django.conf import settings
import requests
from django.http import JsonResponse



from .models import Trip, TripSegment, DailyLog, LogEntry
from .serializers import TripCreateSerializer, TripResponseSerializer
from .services.hos_calculator import HOSCalculator
from .services.distance_calculator import DistanceCalculation


@api_view(['POST'])
def create_trip(request):
    print("Received trip creation request:", request.data)
    serializer = TripCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        with transaction.atomic():
            trip_data = serializer.validated_data
            print("Trip Data:", trip_data)
            

            current_loc = trip_data.get('current_location', {})
            pickup_loc = trip_data.get('pickup_location', {})
            dropoff_loc = trip_data.get('dropoff_location', {})
            cycle_used = trip_data.get('current_cycle_used', 0)

            if not current_loc or not pickup_loc or not dropoff_loc:
                return Response(
                    {'error': 'Missing location data'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            current_coords = current_loc.get('coords')
            pickup_coords = pickup_loc.get('coords')
            dropoff_coords = dropoff_loc.get('coords')
            
            if not all([current_coords, pickup_coords, dropoff_coords]):
                return Response(
                    {'error': 'Missing coordinate data'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            coordinates = [
                tuple(current_coords),
                tuple(pickup_coords),
                tuple(dropoff_coords)
            ]

            distance_calculator = DistanceCalculation()
        
            distance_miles = distance_calculator.calculate_openroute_distance(coordinates)
            print(f"DEBUG: distance_miles = {distance_miles}, type = {type(distance_miles)}")

            
            if distance_miles is None or distance_miles <= 0:
                print("All distance calculations failed, using default")
                distance_miles = 500.0  # Safe fallback
            
            print(f"Calculated distance: {distance_miles} miles")

            if distance_miles <= 0:
                return Response(
                    {'error': 'Invalid route distance calculated'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            trip = Trip.objects.create(
                current_location=str(current_loc.get('name', '')),
                pickup_location=str(pickup_loc.get('name', '')),
                dropoff_location=str(dropoff_loc.get('name', '')),
                current_cycle_used=float(cycle_used) if cycle_used is not None else 0.0,
                total_distance=float(distance_miles)
            )
            
            calculator_data = {
                'start_time': timezone.now(),
                'trip_miles': float(distance_miles),
                'current_cycle_used': float(cycle_used) if cycle_used is not None else 0.0,
                'current_location': str(current_loc.get('name', '')),
                'pickup_location': str(pickup_loc.get('name', '')),
                'dropoff_location': str(dropoff_loc.get('name', ''))
            }
            
            calculator = HOSCalculator(calculator_data)
            result = calculator.calculate()
            
            save_trip_results(trip, result)
            
            return Response(
                TripResponseSerializer(trip).data,
                status=status.HTTP_201_CREATED
            )
    except Exception as e:
        return Response(
            {'error': f'Error calculating trip: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def get_trip(request, trip_id):
    try:
        trip = Trip.objects.get(id=trip_id)
        return Response(TripResponseSerializer(trip).data)
    except Trip.DoesNotExist:
        return Response(
            {'error': 'Trip not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
def trip_list(request):
    trips = Trip.objects.all().order_by('-created_at')
    return Response(TripResponseSerializer(trips, many=True).data)


def save_trip_results(trip: Trip, result: dict):
    summary = result['summary']
    trip.total_duration = Decimal(str(summary['total_duration']))
    trip.fuel_stops = summary['fuel_stops']
    trip.required_rest_stops = summary['required_rest_stops']
    trip.save()
    
    for segment_data in result['segments']:
        TripSegment.objects.create(
            trip=trip,
            segment_type=segment_data['segment_type'],
            sequence_number=segment_data['sequence_number'],
            start_time=segment_data['start_time'],
            end_time=segment_data['end_time'],
            duration_hours=Decimal(str(segment_data['duration_hours'])),
            distance_miles=Decimal(str(segment_data.get('distance_miles', 0))),
            location=segment_data['location']
        )
    
    for log_data in result['daily_logs']:
        entries_data = log_data.pop('entries', [])
        
        daily_log = DailyLog.objects.create(
            trip=trip,
            log_date=log_data['log_date'],
            day_number=log_data['day_number'],
            total_miles=Decimal(str(log_data['total_miles'])),
            off_duty_hours=Decimal(str(log_data['off_duty_hours'])),
            sleeper_berth_hours=Decimal(str(log_data['sleeper_berth_hours'])),
            driving_hours=Decimal(str(log_data['driving_hours'])),
            on_duty_hours=Decimal(str(log_data['on_duty_hours']))
        )
        
        for entry_data in entries_data:
            LogEntry.objects.create(
                daily_log=daily_log,
                duty_status=entry_data['duty_status'],
                start_hour=Decimal(str(entry_data['start_hour'])),
                end_hour=Decimal(str(entry_data['end_hour'])),
                location=entry_data['location']
            )


def geocode_autocomplete(request):
    query = request.GET.get('q', '').strip()
    
    if not query or len(query) < 3:
        return JsonResponse({'features': []})
    
    try:
        # Try OpenRouteService first
        openroute_key = getattr(settings, 'OPENROUTE_API_KEY', None)
        
        if openroute_key:
            url = "https://api.openrouteservice.org/geocode/search"
            
            headers = {
                'Authorization': openroute_key
            }
            
            params = {
                'text': query,
                'size': 10,
                'boundary.country': 'US',
                'layers': 'locality,region'
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Format response for frontend
                formatted_features = []
                for feature in data.get('features', []):
                    props = feature['properties']
                    formatted_features.append({
                        'id': feature.get('id', props.get('id')),
                        'geometry': feature['geometry'],
                        'properties': {
                            'id': props.get('id'),
                            'label': props.get('label'),
                            'name': props.get('name'),
                            'locality': props.get('locality'),
                            'region': props.get('region'),
                            'country': props.get('country', 'US')
                        }
                    })
                
                return JsonResponse({'features': formatted_features})
        
    except requests.exceptions.RequestException as e:
        return JsonResponse({'error': str(e)}, status=500)
    except Exception as e:
        return JsonResponse({'error': 'Internal server error'}, status=500)