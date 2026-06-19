"""Distance and fare calculation helpers."""
from datetime import datetime
import math


def haversine_distance(lat1, lng1, lat2, lng2):
    """Calculate distance between two GPS coordinates in km."""
    R = 6371  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlng / 2) ** 2)
    c = 2 * math.asin(math.sqrt(a))
    return R * c


def calculate_fare(distance_km, fare_rule=None, persons=1):
    """Calculate fare based on distance, time of day, and passenger count.

    Each passenger beyond the first adds `per_person_extra`.
    Returns a dict with the fare rounded to the nearest Rs.5.
    """
    if fare_rule is None:
        base_fare = 10.0
        per_km_rate = 5.0
        per_person_extra = 5.0
        night_multiplier = 1.5
        night_start = 22
        night_end = 6
    else:
        base_fare = float(fare_rule['base_fare'])
        per_km_rate = float(fare_rule['per_km_rate'])
        per_person_extra = float(fare_rule['per_person_extra']) \
            if 'per_person_extra' in fare_rule.keys() \
            and fare_rule['per_person_extra'] is not None else 5.0
        night_multiplier = float(fare_rule['night_multiplier'])
        night_start = int(fare_rule['night_start_hour'])
        night_end = int(fare_rule['night_end_hour'])

    try:
        persons = max(1, int(persons))
    except (TypeError, ValueError):
        persons = 1

    extra = (persons - 1) * per_person_extra
    total = base_fare + (distance_km * per_km_rate) + extra

    # Apply night charge
    current_hour = datetime.now().hour
    if current_hour >= night_start or current_hour < night_end:
        total *= night_multiplier
        is_night_charge = True
    else:
        is_night_charge = False

    # Round to nearest Rs.5
    total = round(total / 5) * 5
    total = max(total, base_fare)  # Never below minimum

    breakdown = (f"Rs.{base_fare} + ({round(distance_km, 1)}km x Rs.{per_km_rate})"
                 + (f" + {persons - 1} x Rs.{per_person_extra}" if persons > 1 else "")
                 + f" = Rs.{total}")

    return {
        'fare': total,
        'distance_km': round(distance_km, 2),
        'base_fare': base_fare,
        'per_km_rate': per_km_rate,
        'per_person_extra': per_person_extra,
        'persons': persons,
        'is_night_charge': is_night_charge,
        'breakdown': breakdown,
    }


def estimate_time(distance_km):
    """Estimate ride time (avg e-rickshaw speed: 25 km/h)."""
    avg_speed = 25
    time_hours = distance_km / avg_speed
    time_minutes = int(time_hours * 60)
    return max(time_minutes, 3)  # Minimum 3 minutes
