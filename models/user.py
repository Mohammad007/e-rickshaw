"""Passenger (users table) helpers."""

TABLE = 'users'
COLUMNS = [
    'id', 'phone', 'name', 'profile_photo', 'language', 'emergency_contact',
    'total_rides', 'fcm_token', 'created_at', 'last_active', 'is_active',
]

# Fields safe to return to clients.
PUBLIC_FIELDS = ['id', 'phone', 'name', 'profile_photo', 'language',
                 'emergency_contact', 'total_rides']


class User:
    @staticmethod
    def to_dict(row, public=True):
        if row is None:
            return None
        fields = PUBLIC_FIELDS if public else COLUMNS
        return {k: row[k] for k in fields if k in row.keys()}
