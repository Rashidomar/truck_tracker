from rest_framework import serializers
from .models import Trip, TripSegment, DailyLog, LogEntry


class LocationCoordinateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    coords = serializers.ListField(
        child=serializers.FloatField(),
        min_length=2,
        max_length=2,
        help_text="[longitude, latitude] array"
    )
    
    def validate_coords(self, value):
        if len(value) != 2:
            raise serializers.ValidationError("Coordinates must be [longitude, latitude]")
        
        longitude, latitude = value
        
        # Validate longitude range
        if not (-180 <= longitude <= 180):
            raise serializers.ValidationError("Longitude must be between -180 and 180")
        
        # Validate latitude range  
        if not (-90 <= latitude <= 90):
            raise serializers.ValidationError("Latitude must be between -90 and 90")
            
        return value


class TripCreateSerializer(serializers.ModelSerializer):
    current_location = LocationCoordinateSerializer()
    pickup_location = LocationCoordinateSerializer()
    dropoff_location = LocationCoordinateSerializer()
    def validate_current_cycle_used(self, value):
        if value > 70:
            raise serializers.ValidationError("Current cycle cannot exceed 70 hours")
        return value

    class Meta:
        model = Trip
        fields = [
            "current_location",
            "pickup_location", 
            "dropoff_location",
            "current_cycle_used"
        ]
        
class LogEntrySerializer(serializers.ModelSerializer):
    duty_status_display = serializers.CharField(source='get_duty_status_display', read_only=True)
    
    class Meta:
        model = LogEntry
        fields = [
            'duty_status', 
            'duty_status_display',
            'start_hour', 
            'end_hour', 
            'location'
        ]


class DailyLogSerializer(serializers.ModelSerializer):
    entries = LogEntrySerializer(many=True, read_only=True)
    formatted_date = serializers.SerializerMethodField()
    
    class Meta:
        model = DailyLog
        fields = [
            'log_date',
            'formatted_date', 
            'day_number',
            'total_miles',
            'off_duty_hours',
            'sleeper_berth_hours', 
            'driving_hours',
            'on_duty_hours',
            'entries'
        ]
    
    def get_formatted_date(self, obj):
        return obj.log_date.strftime('%m/%d/%Y')


class TripSegmentSerializer(serializers.ModelSerializer):
    segment_type_display = serializers.CharField(source='get_segment_type_display', read_only=True)
    formatted_start_time = serializers.SerializerMethodField()
    formatted_end_time = serializers.SerializerMethodField()
    
    class Meta:
        model = TripSegment
        fields = [
            'segment_type',
            'segment_type_display',
            'sequence_number',
            'start_time',
            'end_time', 
            'formatted_start_time',
            'formatted_end_time',
            'duration_hours',
            'distance_miles',
            'location'
        ]
    
    def get_formatted_start_time(self, obj):
        return obj.start_time.strftime('%m/%d/%Y %H:%M')
    
    def get_formatted_end_time(self, obj):
        return obj.end_time.strftime('%m/%d/%Y %H:%M')


class TripResponseSerializer(serializers.ModelSerializer):
    segments = TripSegmentSerializer(many=True, read_only=True)
    daily_logs = DailyLogSerializer(many=True, read_only=True)
    
    # Route information for map display
    route_summary = serializers.SerializerMethodField()
    
    class Meta:
        model = Trip
        fields = [
            'id',
            'current_location',
            'pickup_location', 
            'dropoff_location',
            'current_cycle_used',
            'total_distance',
            'total_duration', 
            'fuel_stops',
            'required_rest_stops',
            'segments',
            'daily_logs',
            'route_summary',
            'created_at'
        ]
    
    def get_route_summary(self, obj):
        return {
            'origin': obj.current_location,
            'destination': obj.dropoff_location,
            'waypoints': [obj.pickup_location],
            'total_distance_miles': float(obj.total_distance) if obj.total_distance else 0,
            'estimated_duration_hours': float(obj.total_duration) if obj.total_duration else 0,
            'fuel_stops_needed': obj.fuel_stops,
            'rest_stops_needed': obj.required_rest_stops
        }