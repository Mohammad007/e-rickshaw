"""OTP generation, delivery, and verification."""
import random
import string
from datetime import datetime, timedelta
from database import get_db


def generate_otp(length=6):
    return ''.join(random.choices(string.digits, k=length))


def send_otp(phone, otp_code, purpose='login'):
    """In production: integrate with MSG91, TextLocal, or Fast2SMS.
    For development: print to console."""
    # TODO: Replace with SMS API
    print(f"📱 OTP for {phone}: {otp_code} (Purpose: {purpose})")

    # For MSG91 integration:
    # import requests
    # url = "https://api.msg91.com/api/v5/otp"
    # payload = {"template_id": "YOUR_TEMPLATE_ID", "mobile": phone, "otp": otp_code}
    # headers = {"authkey": "YOUR_MSG91_KEY"}
    # requests.post(url, json=payload, headers=headers)

    return True


def create_otp_session(phone, purpose='login'):
    """Create an OTP in the database with a 5-minute expiry."""
    db = get_db()
    otp_code = generate_otp()
    expires_at = datetime.now() + timedelta(minutes=5)

    # Delete old OTPs for this phone + purpose.
    db.execute("DELETE FROM otp_sessions WHERE phone=? AND purpose=?", (phone, purpose))
    db.execute(
        "INSERT INTO otp_sessions (phone, otp_code, purpose, expires_at) VALUES (?, ?, ?, ?)",
        (phone, otp_code, purpose, expires_at),
    )
    db.commit()

    send_otp(phone, otp_code, purpose)
    return otp_code


def verify_otp_code(phone, otp_code, purpose='login'):
    """Verify an OTP. Returns True/False."""
    db = get_db()
    session = db.execute(
        """SELECT * FROM otp_sessions
           WHERE phone=? AND otp_code=? AND purpose=?
             AND is_used=0 AND expires_at > datetime('now')
           ORDER BY created_at DESC LIMIT 1""",
        (phone, otp_code, purpose),
    ).fetchone()

    if session:
        db.execute("UPDATE otp_sessions SET is_used=1 WHERE id=?", (session['id'],))
        db.commit()
        return True
    return False
