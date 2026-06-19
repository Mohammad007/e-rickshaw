"""Booking (bookings table) helpers."""

TABLE = 'bookings'

# Status flow.
STATUS_SEARCHING = 'searching'
STATUS_ACCEPTED = 'accepted'
STATUS_DRIVER_ARRIVED = 'driver_arrived'
STATUS_RIDE_STARTED = 'ride_started'
STATUS_COMPLETED = 'completed'
STATUS_CANCELLED = 'cancelled'

ACTIVE_STATUSES = (
    STATUS_SEARCHING, STATUS_ACCEPTED, STATUS_DRIVER_ARRIVED, STATUS_RIDE_STARTED,
)

COLUMNS = [
    'id', 'booking_code', 'user_id', 'driver_id',
    'pickup_lat', 'pickup_lng', 'pickup_address',
    'drop_lat', 'drop_lng', 'drop_address',
    'distance_km', 'estimated_time_min', 'fare_amount',
    'payment_method', 'payment_status', 'otp_code', 'status',
    'requested_at', 'accepted_at', 'driver_arrived_at', 'started_at',
    'completed_at', 'cancelled_at', 'cancelled_by', 'cancelled_reason',
    'user_rating', 'driver_rating', 'user_feedback',
]


class Booking:
    @staticmethod
    def to_dict(row, include_otp=False):
        if row is None:
            return None
        out = dict(row)
        if not include_otp:
            out.pop('otp_code', None)
        return out
