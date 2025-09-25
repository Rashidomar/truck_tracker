from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator


class Trip(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="trips", null=True, blank=True)
    
    # Required inputs from assessment
    current_location = models.CharField(max_length=255)
    pickup_location = models.CharField(max_length=255)
    dropoff_location = models.CharField(max_length=255)
    current_cycle_used = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(70)],
        default=0.00,
        help_text="Hours already used in current 8-day cycle (max 70)"
    )
    
    # Calculated fields
    total_distance = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_duration = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    fuel_stops = models.IntegerField(default=0)
    required_rest_stops = models.IntegerField(default=0)
    
    # Trip metadata
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Trip {self.id}: {self.pickup_location} → {self.dropoff_location}"


class TripSegment(models.Model):
    SEGMENT_TYPES = [
        ("driving", "Driving"),
        ("rest_break", "30-min Rest Break"),
        ("sleeper_berth", "Sleeper Berth"),
        ("fuel", "Fueling"),
        ("pickup", "Pickup"),
        ("dropoff", "Dropoff"),
    ]
    
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="segments")
    segment_type = models.CharField(max_length=20, choices=SEGMENT_TYPES)
    sequence_number = models.IntegerField()
    
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    duration_hours = models.DecimalField(max_digits=4, decimal_places=2)
    distance_miles = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True, default=0)
    location = models.CharField(max_length=255)
    
    class Meta:
        ordering = ["trip", "sequence_number"]
    
    def __str__(self):
        return f"{self.segment_type} - {self.duration_hours}h"


class DailyLog(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="daily_logs")
    log_date = models.DateField()
    day_number = models.IntegerField()
    
    # Daily totals for ELD log
    total_miles = models.DecimalField(max_digits=6, decimal_places=1, default=0)
    off_duty_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    sleeper_berth_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    driving_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    on_duty_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    
    class Meta:
        ordering = ["trip", "day_number"]
        unique_together = ["trip", "day_number"]
    
    def __str__(self):
        return f"Day {self.day_number} - {self.log_date}"


class LogEntry(models.Model):
    DUTY_STATUS_CHOICES = [
        ('off_duty', 'Off Duty'),
        ('sleeper_berth', 'Sleeper Berth'), 
        ('driving', 'Driving'),
        ('on_duty_not_driving', 'On Duty (Not Driving)'),
    ]
    
    daily_log = models.ForeignKey(DailyLog, on_delete=models.CASCADE, related_name="entries")
    duty_status = models.CharField(max_length=20, choices=DUTY_STATUS_CHOICES)
    
    start_hour = models.DecimalField(max_digits=4, decimal_places=2)
    end_hour = models.DecimalField(max_digits=4, decimal_places=2)
    location = models.CharField(max_length=100)
    
    class Meta:
        ordering = ["daily_log", "start_hour"]
    
    def __str__(self):
        return f"{self.duty_status} {self.start_hour}-{self.end_hour}"