"""Fare rule (fare_rules table) helpers."""

TABLE = 'fare_rules'
COLUMNS = [
    'id', 'rule_name', 'base_fare', 'per_km_rate', 'night_multiplier',
    'night_start_hour', 'night_end_hour', 'is_active', 'updated_at',
]


class FareRule:
    @staticmethod
    def to_dict(row):
        if row is None:
            return None
        out = dict(row)
        if 'is_active' in out:
            out['is_active'] = bool(out['is_active'])
        return out
