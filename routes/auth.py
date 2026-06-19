"""Authentication routes — OTP login for passengers and drivers."""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from database import get_db
from config import Config
from utils.otp_helper import create_otp_session, verify_otp_code

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/send-otp', methods=['POST'])
def send_otp():
    """POST /api/auth/send-otp
    Body: {"phone": "9876543210", "role": "user"|"driver"}"""
    data = request.json or {}
    phone = data.get('phone', '').strip()

    if not phone or len(phone) != 10 or not phone.isdigit():
        return jsonify({"success": False, "message": "सही मोबाइल नंबर डालें"}), 400

    otp_code = create_otp_session(phone, purpose='login')
    resp = {"success": True, "message": "OTP भेज दिया गया है"}
    # No SMS gateway yet — return the OTP so the app can display it for testing.
    # Set DEV_SHOW_OTP=0 in the environment once a real SMS provider is wired up.
    if Config.DEV_SHOW_OTP:
        resp["dev_otp"] = otp_code
    return jsonify(resp)


@auth_bp.route('/verify-otp', methods=['POST'])
def verify_otp():
    """POST /api/auth/verify-otp
    Body: {"phone", "otp", "role": "user"|"driver"}
    Returns: JWT token + user/driver data."""
    data = request.json or {}
    phone = data.get('phone', '').strip()
    otp = data.get('otp', '').strip()
    role = data.get('role', 'user')

    if not verify_otp_code(phone, otp, purpose='login'):
        return jsonify({"success": False, "message": "गलत OTP है, फिर से डालें"}), 400

    db = get_db()

    if role == 'driver':
        driver = db.execute("SELECT * FROM drivers WHERE phone=?", (phone,)).fetchone()
        if not driver:
            # New driver — needs registration.
            return jsonify({
                "success": True,
                "needs_registration": True,
                "phone": phone,
                "message": "Registration required",
            })

        if driver['is_blocked']:
            return jsonify({
                "success": False,
                "message": "आपका अकाउंट बंद है। सहायता के लिए संपर्क करें।",
            }), 403

        token = create_access_token(identity=f"driver_{driver['id']}")
        return jsonify({
            "success": True,
            "token": token,
            "role": "driver",
            "driver": {
                "id": driver['id'],
                "name": driver['name'],
                "phone": driver['phone'],
                "is_verified": bool(driver['is_verified']),
                "vehicle_number": driver['vehicle_number'],
                "rating": driver['rating'],
                "total_rides": driver['total_rides'],
            },
        })

    # Passenger path — auto-create the account on first login.
    user = db.execute("SELECT * FROM users WHERE phone=?", (phone,)).fetchone()
    if not user:
        db.execute("INSERT INTO users (phone) VALUES (?)", (phone,))
        db.commit()
        user = db.execute("SELECT * FROM users WHERE phone=?", (phone,)).fetchone()

    token = create_access_token(identity=f"user_{user['id']}")
    return jsonify({
        "success": True,
        "token": token,
        "role": "user",
        "user": {
            "id": user['id'],
            "name": user['name'],
            "phone": user['phone'],
            "emergency_contact": user['emergency_contact'],
        },
    })


@auth_bp.route('/register-driver', methods=['POST'])
def register_driver():
    """POST /api/auth/register-driver
    Body: {phone, name, vehicle_number, vehicle_color, aadhar_number, license_number}"""
    data = request.json or {}
    phone = data.get('phone')
    name = data.get('name', '').strip()
    vehicle_number = data.get('vehicle_number', '').strip().upper()

    if not all([phone, name, vehicle_number]):
        return jsonify({"success": False, "message": "सभी जरूरी जानकारी भरें"}), 400

    db = get_db()

    try:
        db.execute(
            """INSERT INTO drivers
               (phone, name, vehicle_number, vehicle_color, aadhar_number, license_number)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                phone, name, vehicle_number,
                data.get('vehicle_color', ''),
                data.get('aadhar_number', ''),
                data.get('license_number', ''),
            ),
        )
        db.commit()

        driver = db.execute("SELECT * FROM drivers WHERE phone=?", (phone,)).fetchone()
        token = create_access_token(identity=f"driver_{driver['id']}")

        return jsonify({
            "success": True,
            "token": token,
            "message": "रजिस्ट्रेशन हो गया! Admin जांच के बाद आप शुरू कर सकेंगे।",
            "driver": {
                "id": driver['id'],
                "name": driver['name'],
                "is_verified": False,
            },
        })
    except Exception:
        return jsonify({"success": False, "message": "यह नंबर पहले से रजिस्टर है"}), 400
