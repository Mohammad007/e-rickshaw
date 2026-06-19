-- ============================================
-- USERS (Passengers)
-- ============================================
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone VARCHAR(15) UNIQUE NOT NULL,
    name VARCHAR(100),
    profile_photo TEXT,
    language VARCHAR(5) DEFAULT 'hi',       -- 'hi' = Hindi, 'en' = English
    emergency_contact VARCHAR(15),           -- SOS contact number
    total_rides INTEGER DEFAULT 0,
    fcm_token TEXT,                          -- Push notification token
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_active DATETIME,
    is_active BOOLEAN DEFAULT 1
);

-- ============================================
-- DRIVERS
-- ============================================
CREATE TABLE IF NOT EXISTS drivers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone VARCHAR(15) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    profile_photo TEXT,
    aadhar_number VARCHAR(20),               -- Required for verification
    vehicle_number VARCHAR(20) NOT NULL,     -- e.g. MP09ER1234
    vehicle_color VARCHAR(30),
    license_number VARCHAR(30),
    is_verified BOOLEAN DEFAULT 0,           -- Admin must verify before driver can go online
    is_available BOOLEAN DEFAULT 0,          -- Online/Offline toggle
    is_blocked BOOLEAN DEFAULT 0,
    current_lat DECIMAL(10, 8),
    current_lng DECIMAL(11, 8),
    last_location_update DATETIME,
    total_rides INTEGER DEFAULT 0,
    total_earnings DECIMAL(10, 2) DEFAULT 0,
    rating DECIMAL(3, 2) DEFAULT 5.0,
    rating_count INTEGER DEFAULT 0,
    fcm_token TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1
);

-- ============================================
-- BOOKINGS
-- ============================================
CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_code VARCHAR(10) UNIQUE,          -- e.g. ER001234
    user_id INTEGER REFERENCES users(id),
    driver_id INTEGER REFERENCES drivers(id),

    -- Pickup Location
    pickup_lat DECIMAL(10, 8),
    pickup_lng DECIMAL(11, 8),
    pickup_address TEXT,

    -- Drop Location
    drop_lat DECIMAL(10, 8),
    drop_lng DECIMAL(11, 8),
    drop_address TEXT,

    distance_km DECIMAL(8, 2),
    estimated_time_min INTEGER,
    persons INTEGER DEFAULT 1,

    -- Fare
    fare_amount DECIMAL(8, 2),

    -- Nearest-first dispatch: the booking is offered to this driver until
    -- offer_expires_at, after which it opens to all nearby drivers.
    offered_driver_id INTEGER,
    offer_expires_at DATETIME,
    payment_method VARCHAR(20) DEFAULT 'cash', -- 'cash' | 'upi'
    payment_status VARCHAR(20) DEFAULT 'pending', -- 'pending' | 'paid'

    -- OTP for ride start verification
    otp_code VARCHAR(6),

    -- Status Flow:
    -- searching -> accepted -> driver_arrived -> ride_started -> completed -> cancelled
    status VARCHAR(30) DEFAULT 'searching',

    -- Timestamps
    requested_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    accepted_at DATETIME,
    driver_arrived_at DATETIME,
    started_at DATETIME,
    completed_at DATETIME,
    cancelled_at DATETIME,
    cancelled_by VARCHAR(20),                  -- 'user' | 'driver' | 'system'
    cancelled_reason TEXT,

    -- Ratings
    user_rating INTEGER,                       -- 1 to 5
    driver_rating INTEGER,
    user_feedback TEXT
);

-- ============================================
-- FARE RULES (Admin Configurable)
-- ============================================
CREATE TABLE IF NOT EXISTS fare_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_name VARCHAR(50) DEFAULT 'default',
    base_fare DECIMAL(8, 2) DEFAULT 10.0,     -- Minimum Rs.10
    per_km_rate DECIMAL(8, 2) DEFAULT 5.0,    -- Rs.5 per km
    per_person_extra DECIMAL(8, 2) DEFAULT 5.0, -- Rs.5 per extra passenger
    night_multiplier DECIMAL(4, 2) DEFAULT 1.5, -- 1.5x after 10 PM
    night_start_hour INTEGER DEFAULT 22,       -- 10 PM
    night_end_hour INTEGER DEFAULT 6,          -- 6 AM
    is_active BOOLEAN DEFAULT 1,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Insert default fare rule
INSERT OR IGNORE INTO fare_rules (id, rule_name, base_fare, per_km_rate)
VALUES (1, 'default', 10.0, 5.0);

-- ============================================
-- OTP SESSIONS
-- ============================================
CREATE TABLE IF NOT EXISTS otp_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone VARCHAR(15),
    otp_code VARCHAR(6),
    purpose VARCHAR(30),                       -- 'login' | 'ride_start'
    expires_at DATETIME,
    is_used BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- DRIVER DAILY EARNINGS
-- ============================================
CREATE TABLE IF NOT EXISTS driver_earnings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    driver_id INTEGER REFERENCES drivers(id),
    date DATE,
    total_rides INTEGER DEFAULT 0,
    total_amount DECIMAL(10, 2) DEFAULT 0,
    cash_amount DECIMAL(10, 2) DEFAULT 0,
    upi_amount DECIMAL(10, 2) DEFAULT 0,
    UNIQUE(driver_id, date)
);

-- ============================================
-- ADMIN USERS
-- ============================================
CREATE TABLE IF NOT EXISTS admin_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    name VARCHAR(100),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- ANNOUNCEMENTS (Admin broadcast to drivers)
-- ============================================
CREATE TABLE IF NOT EXISTS announcements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(200),
    message TEXT,
    target VARCHAR(20) DEFAULT 'all',         -- 'all' | 'drivers' | 'users'
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
