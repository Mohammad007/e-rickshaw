"""Driver-facing APIs."""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from database import get_db
from utils.fare_calculator import haversine_distance

driver_bp = Blueprint('driver', __name__)


def get_driver_id():
    identity = get_jwt_identity()
    return int(identity.split('_')[1])


@driver_bp.route('/me', methods=['GET'])
@jwt_required()
def me():
    """Return the driver's current profile, incl. fresh verification status."""
    driver_id = get_driver_id()
    db = get_db()
    d = db.execute("SELECT * FROM drivers WHERE id=?", (driver_id,)).fetchone()
    if not d:
        return jsonify({"success": False, "message": "Driver not found"}), 404
    return jsonify({
        "success": True,
        "driver": {
            "id": d['id'],
            "name": d['name'],
            "phone": d['phone'],
            "vehicle_number": d['vehicle_number'],
            "is_verified": bool(d['is_verified']),
            "is_blocked": bool(d['is_blocked']),
            "is_available": bool(d['is_available']),
            "rating": d['rating'],
            "total_rides": d['total_rides'],
        },
    })


@driver_bp.route('/toggle-availability', methods=['POST'])
@jwt_required()
def toggle_availability():
    """Driver goes Online/Offline."""
    driver_id = get_driver_id()
    data = request.json or {}
    is_available = 1 if data.get('is_available', False) else 0

    db = get_db()
    driver = db.execute("SELECT * FROM drivers WHERE id=?", (driver_id,)).fetchone()

    if not driver['is_verified']:
        return jsonify({
            "success": False,
            "message": "आपकी जांच अभी बाकी है। Admin से संपर्क करें।",
        }), 403

    db.execute("UPDATE drivers SET is_available=? WHERE id=?", (is_available, driver_id))
    db.commit()

    return jsonify({
        "success": True,
        "is_available": bool(is_available),
        "message": "काम शुरू हो गया! 🟢" if is_available else "काम बंद हो गया 🔴",
    })


@driver_bp.route('/update-location', methods=['POST'])
@jwt_required()
def update_location():
    """Driver GPS update (every ~10 seconds)."""
    driver_id = get_driver_id()
    data = request.json or {}
    lat = data.get('lat')
    lng = data.get('lng')

    db = get_db()
    db.execute(
        "UPDATE drivers SET current_lat=?, current_lng=?, "
        "last_location_update=datetime('now') WHERE id=?",
        (lat, lng, driver_id),
    )
    db.commit()
    return jsonify({"success": True})


@driver_bp.route('/accept-ride/<int:booking_id>', methods=['POST'])
@jwt_required()
def accept_ride(booking_id):
    driver_id = get_driver_id()
    db = get_db()

    booking = db.execute(
        "SELECT * FROM bookings WHERE id=? AND status='searching'", (booking_id,)
    ).fetchone()
    if not booking:
        return jsonify({"success": False, "message": "यह सवारी अब उपलब्ध नहीं है"}), 400

    db.execute(
        "UPDATE bookings SET driver_id=?, status='accepted', "
        "accepted_at=datetime('now') WHERE id=?",
        (driver_id, booking_id),
    )
    db.execute("UPDATE drivers SET is_available=0 WHERE id=?", (driver_id,))
    db.commit()

    return jsonify({"success": True, "message": "सवारी ली! यात्री के पास जाएं।"})


@driver_bp.route('/reject-ride/<int:booking_id>', methods=['POST'])
@jwt_required()
def reject_ride(booking_id):
    """The offered driver declines. Advance the exclusive offer to the next
    nearest available driver; if none, open the booking to all nearby drivers."""
    from routes.booking_routes import find_nearest_driver, OFFER_WINDOW_SECONDS

    driver_id = get_driver_id()
    db = get_db()
    booking = db.execute(
        "SELECT * FROM bookings WHERE id=? AND status='searching'", (booking_id,)
    ).fetchone()
    if not booking:
        return jsonify({"success": True})

    # Only the currently-offered driver advances the offer.
    if booking['offered_driver_id'] == driver_id:
        next_id, _ = find_nearest_driver(
            db, booking['pickup_lat'], booking['pickup_lng'],
            exclude_ids=[driver_id])
        if next_id:
            db.execute(
                "UPDATE bookings SET offered_driver_id=?, "
                "offer_expires_at=datetime('now', ?) WHERE id=?",
                (next_id, f'+{OFFER_WINDOW_SECONDS} seconds', booking_id),
            )
        else:
            # No other nearby driver — open it to everyone immediately.
            db.execute(
                "UPDATE bookings SET offered_driver_id=NULL, "
                "offer_expires_at=datetime('now') WHERE id=?",
                (booking_id,),
            )
        db.commit()

    return jsonify({"success": True})


@driver_bp.route('/arrived/<int:booking_id>', methods=['POST'])
@jwt_required()
def driver_arrived(booking_id):
    """Mark that the driver has reached the pickup point."""
    driver_id = get_driver_id()
    db = get_db()
    booking = db.execute(
        "SELECT * FROM bookings WHERE id=? AND driver_id=? AND status='accepted'",
        (booking_id, driver_id),
    ).fetchone()
    if not booking:
        return jsonify({"success": False, "message": "बुकिंग नहीं मिली"}), 400

    db.execute(
        "UPDATE bookings SET status='driver_arrived', "
        "driver_arrived_at=datetime('now') WHERE id=?",
        (booking_id,),
    )
    db.commit()
    return jsonify({"success": True, "message": "आप पहुंच गए। यात्री से OTP लें।"})


@driver_bp.route('/start-ride', methods=['POST'])
@jwt_required()
def start_ride():
    """Verify OTP and start the ride."""
    driver_id = get_driver_id()
    data = request.json or {}
    booking_id = data.get('booking_id')
    otp_entered = data.get('otp')

    db = get_db()
    booking = db.execute(
        "SELECT * FROM bookings WHERE id=? AND driver_id=? AND status='driver_arrived'",
        (booking_id, driver_id),
    ).fetchone()

    if not booking:
        return jsonify({"success": False, "message": "बुकिंग नहीं मिली"}), 400

    if booking['otp_code'] != otp_entered:
        return jsonify({"success": False, "message": "गलत OTP है"}), 400

    db.execute(
        "UPDATE bookings SET status='ride_started', started_at=datetime('now') WHERE id=?",
        (booking_id,),
    )
    db.commit()
    return jsonify({"success": True, "message": "सवारी शुरू! 🛺"})


@driver_bp.route('/complete-ride', methods=['POST'])
@jwt_required()
def complete_ride():
    driver_id = get_driver_id()
    data = request.json or {}
    booking_id = data.get('booking_id')

    db = get_db()
    booking = db.execute(
        "SELECT * FROM bookings WHERE id=? AND driver_id=?",
        (booking_id, driver_id),
    ).fetchone()

    if not booking:
        return jsonify({"success": False, "message": "बुकिंग नहीं मिली"}), 400

    db.execute(
        "UPDATE bookings SET status='completed', completed_at=datetime('now'), "
        "payment_status='paid' WHERE id=?",
        (booking_id,),
    )

    # Update driver lifetime stats and put them back online.
    db.execute(
        "UPDATE drivers SET total_rides=total_rides+1, "
        "total_earnings=total_earnings+?, is_available=1 WHERE id=?",
        (booking['fare_amount'], driver_id),
    )

    # Count the completed ride for the passenger too.
    if booking['user_id']:
        db.execute(
            "UPDATE users SET total_rides=total_rides+1 WHERE id=?",
            (booking['user_id'],),
        )

    # Update daily earnings (cash vs upi split).
    today = db.execute("SELECT date('now')").fetchone()[0]
    is_upi = booking['payment_method'] == 'upi'
    cash_amt = 0 if is_upi else booking['fare_amount']
    upi_amt = booking['fare_amount'] if is_upi else 0
    db.execute(
        """INSERT INTO driver_earnings
               (driver_id, date, total_rides, total_amount, cash_amount, upi_amount)
           VALUES (?, ?, 1, ?, ?, ?)
           ON CONFLICT(driver_id, date) DO UPDATE SET
               total_rides  = total_rides  + 1,
               total_amount = total_amount + excluded.total_amount,
               cash_amount  = cash_amount  + excluded.cash_amount,
               upi_amount   = upi_amount   + excluded.upi_amount""",
        (driver_id, today, booking['fare_amount'], cash_amt, upi_amt),
    )

    db.commit()
    return jsonify({
        "success": True,
        "message": f"सवारी पूरी! Rs.{booking['fare_amount']} कमाए 🎉",
        "fare": booking['fare_amount'],
    })


@driver_bp.route('/earnings', methods=['GET'])
@jwt_required()
def get_earnings():
    driver_id = get_driver_id()
    db = get_db()

    today = db.execute("SELECT date('now')").fetchone()[0]

    today_earnings = db.execute(
        "SELECT * FROM driver_earnings WHERE driver_id=? AND date=?",
        (driver_id, today),
    ).fetchone()

    week_total = db.execute(
        "SELECT SUM(total_amount) as total, SUM(total_rides) as rides "
        "FROM driver_earnings WHERE driver_id=? AND date >= date('now', '-7 days')",
        (driver_id,),
    ).fetchone()

    recent_rides = db.execute(
        "SELECT * FROM bookings WHERE driver_id=? AND status='completed' "
        "ORDER BY completed_at DESC LIMIT 10",
        (driver_id,),
    ).fetchall()

    return jsonify({
        "success": True,
        "today": {
            "amount": today_earnings['total_amount'] if today_earnings else 0,
            "rides": today_earnings['total_rides'] if today_earnings else 0,
        },
        "week": {
            "amount": week_total['total'] or 0,
            "rides": week_total['rides'] or 0,
        },
        "recent_rides": [dict(r) for r in recent_rides],
    })
