"""Fare calculation / rules APIs."""
from flask import Blueprint, request, jsonify
from database import get_db
from utils.fare_calculator import haversine_distance, calculate_fare, estimate_time

fare_bp = Blueprint('fare', __name__)


@fare_bp.route('/current-rules', methods=['GET'])
def current_rules():
    """Public: the active fare rule, so apps can display rates."""
    db = get_db()
    rule = db.execute("SELECT * FROM fare_rules WHERE is_active=1 LIMIT 1").fetchone()
    if not rule:
        return jsonify({"success": False, "message": "No active fare rule"}), 404
    return jsonify({"success": True, "fare_rule": dict(rule)})


@fare_bp.route('/calculate', methods=['POST'])
def calculate():
    """Public fare calculator (no auth) for quick previews.
    Accepts either a distance or pickup/drop coordinates.
    POST Body: {"distance_km": 3.2}  OR  {pickup_lat, pickup_lng, drop_lat, drop_lng}"""
    data = request.json or {}
    db = get_db()
    rule = db.execute("SELECT * FROM fare_rules WHERE is_active=1 LIMIT 1").fetchone()

    if 'distance_km' in data:
        distance = float(data['distance_km'])
    else:
        distance = haversine_distance(
            float(data['pickup_lat']), float(data['pickup_lng']),
            float(data['drop_lat']), float(data['drop_lng']),
        )

    fare_info = calculate_fare(distance, dict(rule) if rule else None)
    fare_info['estimated_time'] = estimate_time(distance)
    return jsonify({"success": True, "fare_info": fare_info})
