"""Flask main entry point for the E-Rickshaw booking backend."""
import sys

# Windows consoles default to cp1252, which can't encode the emoji used in
# log/OTP messages. Force UTF-8 so startup and OTP printing don't crash.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding='utf-8')
    except (AttributeError, ValueError):
        pass

import os

from flask import Flask, render_template, send_from_directory, abort
from flask_cors import CORS
from flask_socketio import SocketIO, join_room
from flask_jwt_extended import JWTManager

from config import Config
from database import init_db, get_conn, close_db

from routes.auth import auth_bp
from routes.user_routes import user_bp
from routes.driver_routes import driver_bp
from routes.booking_routes import booking_bp
from routes.fare_routes import fare_bp
from routes.admin_routes import admin_bp

app = Flask(__name__)
app.config.from_object(Config)

CORS(app, origins="*")
jwt = JWTManager(app)
socketio = SocketIO(app, cors_allowed_origins="*",
                    async_mode=Config.SOCKETIO_ASYNC_MODE)

# Register all blueprints
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(user_bp, url_prefix='/api/user')
app.register_blueprint(driver_bp, url_prefix='/api/driver')
app.register_blueprint(booking_bp, url_prefix='/api/booking')
app.register_blueprint(fare_bp, url_prefix='/api/fare')
app.register_blueprint(admin_bp, url_prefix='/admin')

# Close per-request DB connections automatically.
app.teardown_appcontext(close_db)

# Initialize database on startup
with app.app_context():
    init_db()


@app.route('/')
def landing():
    """Public marketing site — about the app, features, and download."""
    return render_template('index.html')


# Folder where a built APK can be dropped to make it downloadable.
DOWNLOAD_DIR = os.path.join(os.path.dirname(__file__), 'static', 'downloads')
APK_NAME = 'e-rickshaw.apk'


@app.route('/download')
def download_app():
    """Serve the Android APK if a build has been placed in static/downloads,
    otherwise show a friendly 'coming soon' page."""
    apk_path = os.path.join(DOWNLOAD_DIR, APK_NAME)
    if os.path.exists(apk_path):
        return send_from_directory(DOWNLOAD_DIR, APK_NAME, as_attachment=True)
    return render_template('download_soon.html'), 404


@app.route('/api/health')
def health():
    return {"success": True, "status": "ok", "service": "erickshaw-backend"}


# ============================================
# SOCKETIO — Real-time Driver Location Tracking
# ============================================
@socketio.on('driver_location_update')
def handle_driver_location(data):
    """Driver sends location every ~10 seconds during an active ride."""
    booking_id = data.get('booking_id')
    driver_id = data.get('driver_id')
    lat = data.get('lat')
    lng = data.get('lng')

    if booking_id:
        # Broadcast location to the passenger watching this booking.
        socketio.emit('driver_location', {
            'lat': lat,
            'lng': lng,
            'driver_id': driver_id,
            'booking_id': booking_id,
        }, room=f'booking_{booking_id}')

    # Persist driver location. SocketIO handlers run outside the request
    # context, so use a fresh connection rather than the request-bound get_db().
    if driver_id is not None:
        db = get_conn()
        try:
            db.execute(
                "UPDATE drivers SET current_lat=?, current_lng=?, "
                "last_location_update=datetime('now') WHERE id=?",
                (lat, lng, driver_id),
            )
            db.commit()
        finally:
            db.close()


@socketio.on('join_booking_room')
def join_booking(data):
    """Passenger joins a room to track their booking."""
    booking_id = data.get('booking_id')
    join_room(f'booking_{booking_id}')


if __name__ == '__main__':
    # Railway (and most hosts) inject the port to bind via $PORT.
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', '1') == '1'
    socketio.run(app, debug=debug, host='0.0.0.0', port=port,
                 allow_unsafe_werkzeug=True)
