# 🛺 हरा रिक्शा — Backend (Flask + SQLite)

REST API + real-time tracking + server-rendered admin panel for the E-Rickshaw
booking platform.

## Setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows  (use: source venv/bin/activate on Linux/Mac)
pip install -r requirements.txt
python app.py
```

The SQLite database (`erickshaw.db`) and all tables are created automatically on
first run from `schema.sql`. The server starts on **http://localhost:5000**.

Optional: copy `.env.example` to `.env` to override secrets / admin credentials.

## Admin Panel

- URL: http://localhost:5000/admin
- Default login: `admin` / `erickshaw@2024` (override via `.env`)
- Pages: Dashboard, Drivers (verify/block), Passengers, Bookings, Fare, Reports

## API Overview

Base URL: `http://localhost:5000`

### Auth (`/api/auth`)
| Method | Path | Body | Notes |
|--------|------|------|-------|
| POST | `/send-otp` | `{phone, role}` | OTP printed to console in dev |
| POST | `/verify-otp` | `{phone, otp, role}` | Returns JWT; auto-creates passenger; driver may need registration |
| POST | `/register-driver` | `{phone, name, vehicle_number, ...}` | Creates driver (unverified) |

### Passenger (`/api/user`) — JWT required
- `POST /nearby-drivers` `{lat, lng, radius_km}`
- `POST /fare-estimate` `{pickup_lat, pickup_lng, drop_lat, drop_lng}`
- `PUT  /profile` `{name, emergency_contact}`
- `GET  /booking-history`
- `POST /rate-driver` `{booking_id, rating, feedback}`

### Driver (`/api/driver`) — JWT required
- `POST /toggle-availability` `{is_available}`
- `POST /update-location` `{lat, lng}`
- `POST /accept-ride/<booking_id>`
- `POST /reject-ride/<booking_id>`
- `POST /arrived/<booking_id>`
- `POST /start-ride` `{booking_id, otp}`
- `POST /complete-ride` `{booking_id}`
- `GET  /earnings`

### Booking (`/api/booking`) — JWT required
- `POST /create` `{pickup_*, drop_*, payment_method}` → returns ride-start OTP
- `GET  /status/<booking_id>`
- `POST /cancel/<booking_id>` `{cancelled_by, reason}`
- `GET  /pending-for-driver` (searching rides within 5 km of driver)

### Fare (`/api/fare`) — public
- `GET  /current-rules`
- `POST /calculate` `{distance_km}` or `{pickup_*, drop_*}`

### Health
- `GET /api/health`

## Real-time (SocketIO)

- Client emits `join_booking_room` `{booking_id}` to watch a ride.
- Driver emits `driver_location_update` `{booking_id, driver_id, lat, lng}`.
- Server broadcasts `driver_location` to room `booking_<id>`.

## Notes / Production TODOs

- **OTP**: `utils/otp_helper.send_otp` prints to console — wire up MSG91/Fast2SMS.
- **Push**: `utils/notification_helper` is a stub — wire up FCM.
- **Admin auth**: uses a single env-configured credential pair (matches spec).
  The `admin_users` table exists for migrating to hashed multi-admin logins.
- **JWT**: tokens never expire (per spec) — set `JWT_ACCESS_TOKEN_EXPIRES` for prod.
- **SocketIO**: runs in `threading` mode for Windows compatibility; switch to
  `eventlet`/`gevent` + a proper WSGI server for production scale.
