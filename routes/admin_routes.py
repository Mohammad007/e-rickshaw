"""Admin panel routes (server-rendered HTML)."""
import os
from functools import wraps
from flask import (Blueprint, render_template, request, redirect, url_for,
                   session, flash)
from database import get_db
from config import Config

# Templates/static live under backend/admin/, one level up from routes/.
_ADMIN_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'admin')

admin_bp = Blueprint(
    'admin', __name__,
    template_folder=os.path.join(_ADMIN_DIR, 'templates'),
    static_folder=os.path.join(_ADMIN_DIR, 'static'),
    static_url_path='/static',
)


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin.login'))
        return f(*args, **kwargs)
    return decorated


@admin_bp.route('/')
def index():
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == Config.ADMIN_USERNAME and password == Config.ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            session['admin_username'] = username
            return redirect(url_for('admin.dashboard'))
        return render_template('login.html', error='Invalid username or password')
    return render_template('login.html')


@admin_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('admin.login'))


@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    db = get_db()
    stats = {
        'total_drivers': db.execute("SELECT COUNT(*) FROM drivers").fetchone()[0],
        'active_drivers': db.execute(
            "SELECT COUNT(*) FROM drivers WHERE is_available=1").fetchone()[0],
        'pending_verification': db.execute(
            "SELECT COUNT(*) FROM drivers WHERE is_verified=0 AND is_blocked=0"
        ).fetchone()[0],
        'total_users': db.execute("SELECT COUNT(*) FROM users").fetchone()[0],
        'today_rides': db.execute(
            "SELECT COUNT(*) FROM bookings WHERE date(requested_at)=date('now') "
            "AND status='completed'").fetchone()[0],
        'today_earnings': db.execute(
            "SELECT SUM(fare_amount) FROM bookings WHERE date(requested_at)=date('now') "
            "AND status='completed'").fetchone()[0] or 0,
        'active_rides': db.execute(
            "SELECT COUNT(*) FROM bookings WHERE status IN "
            "('searching','accepted','driver_arrived','ride_started')").fetchone()[0],
    }
    recent = db.execute(
        """SELECT b.booking_code, b.status, b.fare_amount, b.requested_at,
                  u.name as user_name, d.name as driver_name
           FROM bookings b
           LEFT JOIN users u ON b.user_id = u.id
           LEFT JOIN drivers d ON b.driver_id = d.id
           ORDER BY b.requested_at DESC LIMIT 8"""
    ).fetchall()
    return render_template('dashboard.html', stats=stats, recent=recent)


@admin_bp.route('/drivers')
@admin_required
def drivers():
    db = get_db()
    filter_type = request.args.get('filter', 'all')

    if filter_type == 'pending':
        rows = db.execute(
            "SELECT * FROM drivers WHERE is_verified=0 AND is_blocked=0 "
            "ORDER BY created_at DESC").fetchall()
    elif filter_type == 'blocked':
        rows = db.execute(
            "SELECT * FROM drivers WHERE is_blocked=1 ORDER BY created_at DESC").fetchall()
    elif filter_type == 'active':
        rows = db.execute(
            "SELECT * FROM drivers WHERE is_available=1 ORDER BY created_at DESC").fetchall()
    else:
        rows = db.execute("SELECT * FROM drivers ORDER BY created_at DESC").fetchall()

    return render_template('drivers.html', drivers=rows, filter=filter_type)


@admin_bp.route('/driver/<int:driver_id>')
@admin_required
def driver_detail(driver_id):
    db = get_db()
    driver = db.execute("SELECT * FROM drivers WHERE id=?", (driver_id,)).fetchone()
    if not driver:
        return redirect(url_for('admin.drivers'))
    recent = db.execute(
        """SELECT booking_code, status, fare_amount, distance_km, requested_at
           FROM bookings WHERE driver_id=?
           ORDER BY requested_at DESC LIMIT 10""",
        (driver_id,),
    ).fetchall()
    return render_template('driver_detail.html', d=driver, recent=recent)


@admin_bp.route('/driver/verify/<int:driver_id>', methods=['POST'])
@admin_required
def verify_driver(driver_id):
    db = get_db()
    db.execute("UPDATE drivers SET is_verified=1 WHERE id=?", (driver_id,))
    db.commit()
    return redirect(request.referrer or url_for('admin.drivers', filter='pending'))


@admin_bp.route('/driver/block/<int:driver_id>', methods=['POST'])
@admin_required
def block_driver(driver_id):
    db = get_db()
    db.execute("UPDATE drivers SET is_blocked=1, is_available=0 WHERE id=?", (driver_id,))
    db.commit()
    return redirect(request.referrer or url_for('admin.drivers'))


@admin_bp.route('/driver/unblock/<int:driver_id>', methods=['POST'])
@admin_required
def unblock_driver(driver_id):
    db = get_db()
    db.execute("UPDATE drivers SET is_blocked=0 WHERE id=?", (driver_id,))
    db.commit()
    return redirect(request.referrer or url_for('admin.drivers'))


@admin_bp.route('/users')
@admin_required
def users():
    db = get_db()
    rows = db.execute(
        "SELECT * FROM users ORDER BY created_at DESC LIMIT 200").fetchall()
    return render_template('users.html', users=rows)


@admin_bp.route('/user/<int:user_id>')
@admin_required
def user_detail(user_id):
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if not user:
        return redirect(url_for('admin.users'))
    recent = db.execute(
        """SELECT b.booking_code, b.status, b.fare_amount, b.distance_km,
                  b.requested_at, d.name as driver_name
           FROM bookings b
           LEFT JOIN drivers d ON b.driver_id = d.id
           WHERE b.user_id=?
           ORDER BY b.requested_at DESC LIMIT 10""",
        (user_id,),
    ).fetchall()
    completed = db.execute(
        "SELECT COUNT(*) FROM bookings WHERE user_id=? AND status='completed'",
        (user_id,),
    ).fetchone()[0]
    return render_template('user_detail.html', u=user, recent=recent,
                           completed=completed)


@admin_bp.route('/bookings')
@admin_required
def bookings():
    db = get_db()
    rows = db.execute(
        """SELECT b.*, u.name as user_name, u.phone as user_phone,
                  d.name as driver_name, d.vehicle_number
           FROM bookings b
           LEFT JOIN users u ON b.user_id = u.id
           LEFT JOIN drivers d ON b.driver_id = d.id
           ORDER BY b.requested_at DESC LIMIT 100"""
    ).fetchall()
    return render_template('bookings.html', bookings=rows)


@admin_bp.route('/fare', methods=['GET', 'POST'])
@admin_required
def fare_management():
    db = get_db()
    if request.method == 'POST':
        db.execute(
            "UPDATE fare_rules SET base_fare=?, per_km_rate=?, per_person_extra=?, "
            "night_multiplier=?, night_start_hour=?, night_end_hour=?, "
            "updated_at=datetime('now') WHERE id=1",
            (
                request.form.get('base_fare'),
                request.form.get('per_km_rate'),
                request.form.get('per_person_extra', 5),
                request.form.get('night_multiplier'),
                request.form.get('night_start_hour', 22),
                request.form.get('night_end_hour', 6),
            ),
        )
        db.commit()
        flash('Fare updated', 'success')
        return redirect(url_for('admin.fare_management'))

    fare_rule = db.execute("SELECT * FROM fare_rules WHERE id=1").fetchone()
    return render_template('fare_management.html', fare=fare_rule)


@admin_bp.route('/reports')
@admin_required
def reports():
    db = get_db()
    daily = db.execute(
        """SELECT date(requested_at) as day,
                  COUNT(*) as rides,
                  SUM(CASE WHEN status='completed' THEN fare_amount ELSE 0 END) as earnings
           FROM bookings
           WHERE requested_at >= date('now', '-14 days')
           GROUP BY date(requested_at)
           ORDER BY day DESC"""
    ).fetchall()
    top_drivers = db.execute(
        """SELECT name, vehicle_number, total_rides, total_earnings, rating
           FROM drivers ORDER BY total_earnings DESC LIMIT 10"""
    ).fetchall()
    return render_template('reports.html', daily=daily, top_drivers=top_drivers)
