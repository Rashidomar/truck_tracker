from django.contrib import admin
from .models import Trip, TripSegment, DailyLog, LogEntry


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = (
        "id", "user", "pickup_location", "dropoff_location",
        "current_cycle_used", "total_distance", "created_at"
    )
    # list_filter = ("created_at")
    search_fields = ("pickup_location", "dropoff_location", "user__username")


@admin.register(TripSegment)
class TripSegmentAdmin(admin.ModelAdmin):
    list_display = (
        "id", "trip", "segment_type", "sequence_number", "start_time", "end_time",
        "duration_hours", "distance_miles"
    )
    # list_filter = ("segment_type",)
    search_fields = ("trip__pickup_location", "trip__dropoff_location")


@admin.register(DailyLog)
class DailyLogAdmin(admin.ModelAdmin):
    list_display = (
        "id", "trip", "log_date", "day_number",
         "total_miles", "driving_hours", "off_duty_hours"
    )
    # list_filter = ("log_date")
    search_fields = ("trip__pickup_location", "trip__dropoff_location")


@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    list_display = (
        "id", "daily_log", "duty_status",
        "start_hour", "end_hour", "location"
    )
    # list_filter = ("duty_status",)
    search_fields = ("location", "daily_log__trip__pickup_location")
