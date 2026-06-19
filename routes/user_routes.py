"""Passenger-facing APIs."""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from database import get_db
from utils.fare_calculator import haversine_distance, calculate_fare, estimate_time

user_bp = Blueprint('user', __name__)


def get_user_id():
    identity = get_jwt_identity()
    return int(identity.split('_')[1])


@user_bp.route('/nearby-drivers', methods=['POST'])
@jwt_required()
def nearby_drivers():
    """Find available drivers within a radius.
    POST Body: {"lat": 22.7196, "lng": 75.8577, "radius_km": 5}"""
    data = request.json or {}
    user_lat = float(data.get('lat'))
    user_lng = float(data.get('lng'))
    radius_km = float(data.get('radius_km', 5))

    db = get_db()
    all_drivers = db.execute(
        """SELECT id, name, vehicle_number, vehicle_color, rating, total_rides,
                  current_lat, current_lng, profile_photo
           FROM drivers
           WHERE is_available=1 AND is_verified=1 AND is_blocked=0
             AND current_lat IS NOT NULL AND current_lng IS NOT NULL"""
    ).fetchall()

    nearby = []
    for driver in all_drivers:
        dist = haversine_distance(user_lat, user_lng,
                                  driver['current_lat'], driver['current_lng'])
        if dist <= radius_km:
            driver_dict = dict(driver)
            driver_dict['distance_km'] = round(dist, 2)
            driver_dict['eta_minutes'] = estimate_time(dist)
            nearby.append(driver_dict)

    nearby.sort(key=lambda x: x['distance_km'])
    return jsonify({"success": True, "drivers": nearby[:10]})


@user_bp.route('/fare-estimate', methods=['POST'])
@jwt_required()
def fare_estimate():
    """Calculate fare before booking."""
    data = request.json or {}
    db = get_db()

    fare_rule = db.execute("SELECT * FROM fare_rules WHERE is_active=1 LIMIT 1").fetchone()
    distance = haversine_distance(
        float(data['pickup_lat']), float(data['pickup_lng']),
        float(data['drop_lat']), float(data['drop_lng']),
    )

    persons = data.get('persons', 1)
    fare_info = calculate_fare(distance, dict(fare_rule) if fare_rule else None, persons)
    fare_info['estimated_time'] = estimate_time(distance)

    return jsonify({"success": True, "fare_info": fare_info})


@user_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    user_id = get_user_id()
    data = request.json or {}
    db = get_db()

    db.execute(
        "UPDATE users SET name=?, emergency_contact=? WHERE id=?",
        (data.get('name'), data.get('emergency_contact'), user_id),
    )
    db.commit()
    return jsonify({"success": True, "message": "प्रोफाइल अपडेट हो गई"})


@user_bp.route('/booking-history', methods=['GET'])
@jwt_required()
def booking_history():
    user_id = get_user_id()
    db = get_db()

    bookings = db.execute(
        """SELECT b.*, d.name as driver_name, d.vehicle_number,
                  d.rating as driver_rating
           FROM bookings b
           LEFT JOIN drivers d ON b.driver_id = d.id
           WHERE b.user_id=?
           ORDER BY b.requested_at DESC
           LIMIT 20""",
        (user_id,),
    ).fetchall()

    return jsonify({"success": True, "bookings": [dict(b) for b in bookings]})


@user_bp.route('/rate-driver', methods=['POST'])
@jwt_required()
def rate_driver():
    user_id = get_user_id()
    data = request.json or {}
    booking_id = data.get('booking_id')
    rating = data.get('rating')  # 1-5
    feedback = data.get('feedback', '')

    db = get_db()
    db.execute(
        "UPDATE bookings SET user_rating=?, user_feedback=? WHERE id=? AND user_id=?",
        (rating, feedback, booking_id, user_id),
    )

    # Update driver average rating.
    booking = db.execute(
        "SELECT driver_id FROM bookings WHERE id=?", (booking_id,)
    ).fetchone()
    if booking and booking['driver_id']:
        db.execute(
            """UPDATE drivers SET
                   rating = (rating * rating_count + ?) / (rating_count + 1),
                   rating_count = rating_count + 1
               WHERE id=?""",
            (rating, booking['driver_id']),
        )

    db.commit()
    return jsonify({"success": True, "message": "रेटिंग दे दी! धन्यवाद 🙏"})
