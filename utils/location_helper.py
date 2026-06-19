"""Location helpers — thin wrappers around the haversine distance calc."""
from utils.fare_calculator import haversine_distance


def distance_km(lat1, lng1, lat2, lng2):
    """Distance between two coordinates in km."""
    return haversine_distance(lat1, lng1, lat2, lng2)


def is_within_radius(lat1, lng1, lat2, lng2, radius_km):
    """True if the second point lies within `radius_km` of the first."""
    return haversine_distance(lat1, lng1, lat2, lng2) <= radius_km
