"""Booking lifecycle APIs."""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from database import get_db
from utils.fare_calculator import haversine_distance, calculate_fare, estimate_time
from utils.otp_helper import generate_otp
import random
import string

booking_bp = Blueprint('booking', __name__)

# A new booking is offered exclusively to the nearest driver for this many
# seconds; after that it opens to all nearby drivers (fallback).
OFFER_WINDOW_SECONDS = 20


def generate_booking_code():
    return 'ER' + ''.join(random.choices(string.digits, k=6))


def find_nearest_driver(db, pickup_lat, pickup_lng, radius_km=5, exclude_ids=None):
    """Return (driver_id, distance_km) of the nearest available, verified,
    unblocked driver within radius_km — or (None, None)."""
    exclude_ids = set(exclude_ids or [])
    drivers = db.execute(
        """SELECT id, current_lat, current_lng FROM drivers
           WHERE is_available=1 AND is_verified=1 AND is_blocked=0
             AND current_lat IS NOT NULL AND current_lng IS NOT NULL"""
    ).fetchall()

    best_id, best_dist = None, None
    for d in drivers:
        if d['id'] in exclude_ids:
            continue
        dist = haversine_distance(pickup_lat, pickup_lng,
                                  d['current_lat'], d['current_lng'])
        if dist <= radius_km and (best_dist is None or dist < best_dist):
            best_id, best_dist = d['id'], dist
    return best_id, best_dist


@booking_bp.route('/create', methods=['POST'])
@jwt_required()
def create_booking():
    """Create a new booking request.
    POST Body: {pickup_lat, pickup_lng, pickup_address, drop_lat, drop_lng,
                drop_address, payment_method}"""
    identity = get_jwt_identity()
    user_id = int(identity.split('_')[1])
    data = request.json or {}

    db = get_db()

    distance = haversine_distance(
        float(data['pickup_lat']), float(data['pickup_lng']),
        float(data['drop_lat']), float(data['drop_lng']),
    )

    persons = data.get('persons', 1)
    fare_rule = db.execute("SELECT * FROM fare_rules WHERE is_active=1 LIMIT 1").fetchone()
    fare_info = calculate_fare(distance, dict(fare_rule) if fare_rule else None, persons)
    est_time = estimate_time(distance)

    otp_code = generate_otp(4)  # 4-digit ride-start OTP

    # Nearest-first dispatch: offer to the closest available driver first.
    pickup_lat = float(data['pickup_lat'])
    pickup_lng = float(data['pickup_lng'])
    nearest_id, _ = find_nearest_driver(db, pickup_lat, pickup_lng)

    cursor = db.execute(
        """INSERT INTO bookings (
               booking_code, user_id, pickup_lat, pickup_lng, pickup_address,
               drop_lat, drop_lng, drop_address, distance_km, estimated_time_min,
               persons, fare_amount, payment_method, otp_code, status,
               offered_driver_id, offer_expires_at
           ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'searching', ?,
                     datetime('now', ?))""",
        (
            generate_booking_code(), user_id,
            data['pickup_lat'], data['pickup_lng'], data['pickup_address'],
            data['drop_lat'], data['drop_lng'], data['drop_address'],
            distance, est_time, fare_info['persons'], fare_info['fare'],
            data.get('payment_method', 'cash'), otp_code,
            nearest_id, f'+{OFFER_WINDOW_SECONDS} seconds',
        ),
    )

    db.commit()
    booking_id = cursor.lastrowid

    return jsonify({
        "success": True,
        "booking_id": booking_id,
        "otp_code": otp_code,
        "fare": fare_info['fare'],
        "persons": fare_info['persons'],
        "distance_km": round(distance, 2),
        "estimated_time_min": est_time,
        "message": "रिक्शा ढूंढ रहे हैं... 🔍",
    })


@booking_bp.route('/status/<int:booking_id>', methods=['GET'])
@jwt_required()
def booking_status(booking_id):
    db = get_db()
    booking = db.execute(
        """SELECT b.*, d.name as driver_name, d.phone as driver_phone,
                  d.vehicle_number, d.vehicle_color, d.current_lat, d.current_lng,
                  d.rating as driver_rating, d.profile_photo as driver_photo
           FROM bookings b
           LEFT JOIN drivers d ON b.driver_id = d.id
           WHERE b.id=?""",
        (booking_id,),
    ).fetchone()

    if not booking:
        return jsonify({"success": False, "message": "बुकिंग नहीं मिली"}), 404

    return jsonify({"success": True, "booking": dict(booking)})


@booking_bp.route('/cancel/<int:booking_id>', methods=['POST'])
@jwt_required()
def cancel_booking(booking_id):
    data = request.json or {}
    db = get_db()

    db.execute(
        """UPDATE bookings
           SET status='cancelled', cancelled_at=datetime('now'),
               cancelled_by=?, cancelled_reason=?
           WHERE id=? AND status IN ('searching', 'accepted', 'driver_arrived')""",
        (data.get('cancelled_by', 'user'), data.get('reason', ''), booking_id),
    )

    # Make the driver available again.
    booking = db.execute(
        "SELECT driver_id FROM bookings WHERE id=?", (booking_id,)
    ).fetchone()
    if booking and booking['driver_id']:
        db.execute("UPDATE drivers SET is_available=1 WHERE id=?", (booking['driver_id'],))

    db.commit()
    return jsonify({"success": True, "message": "बुकिंग रद्द हो गई"})


@booking_bp.route('/pending-for-driver', methods=['GET'])
@jwt_required()
def pending_for_driver():
    """Searching bookings within 5km of the requesting driver."""
    identity = get_jwt_identity()
    driver_id = int(identity.split('_')[1])

    db = get_db()
    driver = db.execute(
        "SELECT current_lat, current_lng FROM drivers WHERE id=?", (driver_id,)
    ).fetchone()

    if not driver or driver['current_lat'] is None:
        return jsonify({"success": True, "bookings": []})

    # A booking is visible to this driver if either:
    #   - it is currently offered to them (offer not yet expired), or
    #   - the exclusive offer window has expired (open to all nearby drivers).
    bookings = db.execute(
        """SELECT b.*, u.name as user_name, u.phone as user_phone
           FROM bookings b
           LEFT JOIN users u ON b.user_id = u.id
           WHERE b.status='searching'
             AND (
                   b.offered_driver_id = ?
                   OR b.offered_driver_id IS NULL
                   OR b.offer_expires_at IS NULL
                   OR b.offer_expires_at <= datetime('now')
                 )
           ORDER BY b.requested_at ASC""",
        (driver_id,),
    ).fetchall()

    nearby = []
    for booking in bookings:
        if booking['pickup_lat'] is not None and booking['pickup_lng'] is not None:
            dist = haversine_distance(
                driver['current_lat'], driver['current_lng'],
                booking['pickup_lat'], booking['pickup_lng'],
            )
            if dist <= 5:
                b = dict(booking)
                b['driver_distance_km'] = round(dist, 2)
                # Don't leak the ride-start OTP to drivers in the list.
                b.pop('otp_code', None)
                nearby.append(b)

    return jsonify({"success": True, "bookings": nearby})
