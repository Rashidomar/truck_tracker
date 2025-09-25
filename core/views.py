# core/views.py
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
            # Get input data
            trip_data = serializer.validated_data
            print("Trip Data:", trip_data)
            
            distance_calculator = DistanceCalculation()

            current_loc = trip_data['current_location']
            pickup_loc = trip_data['pickup_location']
            dropoff_loc = trip_data['dropoff_location']
            
            # Prepare coordinates for distance calculation
            coordinates = [
                tuple(current_loc['coords']),  # (lon, lat)
                tuple(pickup_loc['coords']),   # (lon, lat)
                tuple(dropoff_loc['coords'])   # (lon, lat)
            ]
            
            # Calculate distance using coordinates
            distance_miles = distance_calculator.calculate_openroute_distance(coordinates)
            print(f"DEBUG: distance_miles = {distance_miles}, type = {type(distance_miles)}")

            if distance_miles <= 0:
                return Response(
                    {'error': 'Invalid route distance calculated'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            # distance_miles = distance_calculator.calculate_openroute_distance(
            #     origin=trip_data['current_location'],
            #     pickup=trip_data['pickup_location'], 
            #     destination=trip_data['dropoff_location']
            # )
            
            # Create trip record
            trip = Trip.objects.create(
                current_location=trip_data['current_location'],
                pickup_location=trip_data['pickup_location'],
                dropoff_location=trip_data['dropoff_location'], 
                current_cycle_used=trip_data['current_cycle_used'],
                total_distance=distance_miles
            )
            
            # Calculate HOS-compliant segments and logs
            calculator_data = {
                'start_time': timezone.now(),
                'trip_miles': distance_miles,
                'current_cycle_used': float(trip_data['current_cycle_used']),
                'current_location': trip_data['current_location'],
                'pickup_location': trip_data['pickup_location'],
                'dropoff_location': trip_data['dropoff_location']
            }
            
            calculator = HOSCalculator(calculator_data)
            result = calculator.calculate()
            
            # Save calculated data
            save_trip_results(trip, result)
            
            # Return response with route and ELD data
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
    """Get trip details with route and ELD logs"""
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
    """List all trips"""
    trips = Trip.objects.all().order_by('-created_at')
    return Response(TripResponseSerializer(trips, many=True).data)


def save_trip_results(trip: Trip, result: dict):
    """Save calculated HOS results to database"""
    
    # Update trip with summary data
    summary = result['summary']
    trip.total_duration = Decimal(str(summary['total_duration']))
    trip.fuel_stops = summary['fuel_stops']
    trip.required_rest_stops = summary['required_rest_stops']
    trip.save()
    
    # Save segments
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
    
    # Save daily logs
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
        
        # Save log entries for ELD grid
        for entry_data in entries_data:
            LogEntry.objects.create(
                daily_log=daily_log,
                duty_status=entry_data['duty_status'],
                start_hour=Decimal(str(entry_data['start_hour'])),
                end_hour=Decimal(str(entry_data['end_hour'])),
                location=entry_data['location']
            )


def geocode_autocomplete(request):
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    query = request.GET.get('q', '')
    if not query:
        return JsonResponse({'error': 'Query parameter required'}, status=400)
    
    try:
        api_key = settings.OPENROUTE_API_KEY
        url = f"https://api.openrouteservice.org/geocode/autocomplete"
        
        params = {
            'text': query,
            'boundary.country': 'US',
            'size': 6,
            'api_key': api_key
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        return JsonResponse(response.json())
        
    except requests.exceptions.RequestException as e:
        return JsonResponse({'error': str(e)}, status=500)
    except Exception as e:
        return JsonResponse({'error': 'Internal server error'}, status=500)