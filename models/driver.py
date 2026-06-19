"""Driver (drivers table) helpers."""

TABLE = 'drivers'
COLUMNS = [
    'id', 'phone', 'name', 'profile_photo', 'aadhar_number', 'vehicle_number',
    'vehicle_color', 'license_number', 'is_verified', 'is_available', 'is_blocked',
    'current_lat', 'current_lng', 'last_location_update', 'total_rides',
    'total_earnings', 'rating', 'rating_count', 'fcm_token', 'created_at', 'is_active',
]

# Fields safe to expose to passengers (no Aadhaar/license/phone-by-default).
PUBLIC_FIELDS = ['id', 'name', 'profile_photo', 'vehicle_number', 'vehicle_color',
                 'rating', 'total_rides', 'current_lat', 'current_lng']


class Driver:
    @staticmethod
    def to_dict(row, public=True):
        if row is None:
            return None
        fields = PUBLIC_FIELDS if public else COLUMNS
        out = {k: row[k] for k in fields if k in row.keys()}
        for b in ('is_verified', 'is_available', 'is_blocked', 'is_active'):
            if b in out:
                out[b] = bool(out[b])
        return out
