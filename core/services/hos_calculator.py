from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple
import math


class HOSCalculator:
    """
    Simplified HOS calculator for assessment requirements.
    Follows FMCSA rules: 11-hour driving, 14-hour window, 10-hour rest, 70-hour/8-day cycle
    """
    
    # HOS Constants per FMCSA regulations
    MAX_DAILY_DRIVING = 11.0
    MAX_DAILY_ON_DUTY = 14.0
    MAX_CYCLE_HOURS = 70.0
    REQUIRED_OFF_DUTY = 10.0
    BREAK_REQUIREMENT_HOURS = 8.0  
    
    # Assessment assumptions
    DEFAULT_AVG_SPEED = 55.0
    FUEL_RANGE = 1000.0  
    FUEL_STOP_DURATION = 0.5  
    PICKUP_DROPOFF_DURATION = 1.0  
    
    def __init__(self, trip_data: Dict[str, Any]):
        self.start_time = trip_data.get("start_time")
        trip_miles_raw = trip_data.get("trip_miles", 0)
        current_cycle_used_raw = trip_data.get("current_cycle_used", 0)
        print(f"DEBUG HOS: trip_miles_raw = {trip_miles_raw}, type = {type(trip_miles_raw)}")
        print(f"DEBUG HOS: current_cycle_used_raw = {current_cycle_used_raw}, type = {type(current_cycle_used_raw)}")
        self.trip_miles = float(trip_miles_raw)
        self.current_cycle_used = float(current_cycle_used_raw)
        self.current_location = trip_data.get("current_location", "")
        self.pickup_location = trip_data.get("pickup_location", "")
        self.dropoff_location = trip_data.get("dropoff_location", "")
    
    def calculate(self) -> Dict[str, Any]:
        """Calculate HOS-compliant trip segments and daily logs"""
        segments = []
        current_time = self.start_time
        miles_remaining = self.trip_miles
        sequence = 1
        
        # Add pickup segment
        pickup_segment = {
            "segment_type": "pickup",
            "sequence_number": sequence,
            "start_time": current_time,
            "end_time": current_time + timedelta(hours=self.PICKUP_DROPOFF_DURATION),
            "duration_hours": self.PICKUP_DROPOFF_DURATION,
            "distance_miles": 0,
            "location": self.pickup_location
        }
        segments.append(pickup_segment)
        sequence += 1
        current_time = pickup_segment["end_time"]
        
        # Track daily hours
        daily_driving_hours = 0
        daily_on_duty_hours = self.PICKUP_DROPOFF_DURATION
        time_since_break = 0
        
        while miles_remaining > 0:
            if self._needs_fuel_stop(segments):
                fuel_segment = {
                    "segment_type": "fuel",
                    "sequence_number": sequence,
                    "start_time": current_time,
                    "end_time": current_time + timedelta(hours=self.FUEL_STOP_DURATION),
                    "duration_hours": self.FUEL_STOP_DURATION,
                    "distance_miles": 0,
                    "location": "Fuel Station"
                }
                segments.append(fuel_segment)
                sequence += 1
                current_time = fuel_segment["end_time"]
                daily_on_duty_hours += self.FUEL_STOP_DURATION
                time_since_break += self.FUEL_STOP_DURATION
                continue
            
            if time_since_break >= self.BREAK_REQUIREMENT_HOURS:
                break_segment = {
                    "segment_type": "rest_break",
                    "sequence_number": sequence,
                    "start_time": current_time,
                    "end_time": current_time + timedelta(hours=0.5),
                    "duration_hours": 0.5,
                    "distance_miles": 0,
                    "location": "Rest Stop"
                }
                segments.append(break_segment)
                sequence += 1
                current_time = break_segment["end_time"]
                time_since_break = 0
                continue
            
            remaining_daily_driving = self.MAX_DAILY_DRIVING - daily_driving_hours
            remaining_daily_on_duty = self.MAX_DAILY_ON_DUTY - daily_on_duty_hours
            
            if remaining_daily_driving <= 0 or remaining_daily_on_duty <= 0:
                rest_segment = {
                    "segment_type": "sleeper_berth",
                    "sequence_number": sequence,
                    "start_time": current_time,
                    "end_time": current_time + timedelta(hours=self.REQUIRED_OFF_DUTY),
                    "duration_hours": self.REQUIRED_OFF_DUTY,
                    "distance_miles": 0,
                    "location": "Rest Area"
                }
                segments.append(rest_segment)
                sequence += 1
                current_time = rest_segment["end_time"]
                daily_driving_hours = 0
                daily_on_duty_hours = 0
                time_since_break = 0
                continue
            
            hours_for_remaining_miles = miles_remaining / self.DEFAULT_AVG_SPEED
            max_driving_hours = min(
                remaining_daily_driving,
                remaining_daily_on_duty,
                hours_for_remaining_miles,
                4.0 
            )
            
            segment_miles = max_driving_hours * self.DEFAULT_AVG_SPEED
            
            driving_segment = {
                "segment_type": "driving",
                "sequence_number": sequence,
                "start_time": current_time,
                "end_time": current_time + timedelta(hours=max_driving_hours),
                "duration_hours": round(max_driving_hours, 2),
                "distance_miles": round(segment_miles, 1),
                "location": "On Route"
            }
            segments.append(driving_segment)
            sequence += 1
            
            current_time = driving_segment["end_time"]
            daily_driving_hours += max_driving_hours
            daily_on_duty_hours += max_driving_hours
            time_since_break += max_driving_hours
            miles_remaining -= segment_miles
        
        dropoff_segment = {
            "segment_type": "dropoff",
            "sequence_number": sequence,
            "start_time": current_time,
            "end_time": current_time + timedelta(hours=self.PICKUP_DROPOFF_DURATION),
            "duration_hours": self.PICKUP_DROPOFF_DURATION,
            "distance_miles": 0,
            "location": self.dropoff_location
        }
        segments.append(dropoff_segment)
        
        daily_logs = self._generate_daily_logs(segments)
        
        summary = {
            "total_distance": self.trip_miles,
            "total_duration": sum(s["duration_hours"] for s in segments if s["segment_type"] == "driving"),
            "fuel_stops": len([s for s in segments if s["segment_type"] == "fuel"]),
            "required_rest_stops": len([s for s in segments if s["segment_type"] == "sleeper_berth"]),
            "total_trip_time": sum(s["duration_hours"] for s in segments),
            "estimated_arrival": segments[-1]["end_time"]
        }
        
        return {
            "segments": segments,
            "summary": summary,
            "daily_logs": daily_logs
        }
    
    def _needs_fuel_stop(self, segments: List[Dict]) -> bool:
        miles_since_fuel = 0
        for segment in reversed(segments):
            if segment["segment_type"] == "fuel":
                break
            miles_since_fuel += segment.get("distance_miles", 0)
        else:
            miles_since_fuel = sum(s.get("distance_miles", 0) for s in segments)
        
        return miles_since_fuel >= self.FUEL_RANGE
    
    def _generate_daily_logs(self, segments: List[Dict]) -> List[Dict]:
        if not segments:
            return []
        
        daily_logs = {}
        day_number = 1
        
        for segment in segments:
            day = segment["start_time"].date()
            
            if day not in daily_logs:
                daily_logs[day] = {
                    "log_date": day,
                    "day_number": day_number,
                    "entries": [],
                    "driving_hours": 0,
                    "on_duty_hours": 0,
                    "sleeper_berth_hours": 0,
                    "off_duty_hours": 0,
                    "total_miles": 0
                }
                day_number += 1
            
            duration = segment["duration_hours"]
            segment_type = segment["segment_type"]
            
            if segment_type == "driving":
                daily_logs[day]["driving_hours"] += duration
                daily_logs[day]["total_miles"] += segment.get("distance_miles", 0)
            elif segment_type == "sleeper_berth":
                daily_logs[day]["sleeper_berth_hours"] += duration
            elif segment_type in ["fuel", "pickup", "dropoff"]:
                daily_logs[day]["on_duty_hours"] += duration
            else:
                daily_logs[day]["off_duty_hours"] += duration
            
            start_hour = segment["start_time"].hour + segment["start_time"].minute / 60
            end_hour = segment["end_time"].hour + segment["end_time"].minute / 60
            
            duty_status_map = {
                "driving": "driving",
                "sleeper_berth": "sleeper_berth", 
                "rest_break": "off_duty",
                "fuel": "on_duty_not_driving",
                "pickup": "on_duty_not_driving",
                "dropoff": "on_duty_not_driving"
            }
            
            daily_logs[day]["entries"].append({
                "duty_status": duty_status_map.get(segment_type, "on_duty_not_driving"),
                "start_hour": round(start_hour, 2),
                "end_hour": round(end_hour, 2),
                "location": segment["location"]
            })
        
        for day_data in daily_logs.values():
            total_hours = (
                day_data["driving_hours"] + 
                day_data["on_duty_hours"] + 
                day_data["sleeper_berth_hours"] + 
                day_data["off_duty_hours"]
            )
            if total_hours < 24:
                day_data["off_duty_hours"] += (24 - total_hours)
        
        return list(daily_logs.values())