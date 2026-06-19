"""JWT identity helpers.

Identities are stored as "user_<id>" or "driver_<id>" strings. These helpers
parse them so routes don't repeat the split logic.
"""
from flask_jwt_extended import create_access_token, get_jwt_identity


def make_identity(role, entity_id):
    """Build a JWT identity string, e.g. make_identity('driver', 7) -> 'driver_7'."""
    return f"{role}_{entity_id}"


def create_token(role, entity_id):
    return create_access_token(identity=make_identity(role, entity_id))


def parse_identity(identity=None):
    """Return (role, id) from a JWT identity string. Reads the current
    request's identity if none is passed."""
    if identity is None:
        identity = get_jwt_identity()
    role, _, entity_id = identity.partition('_')
    return role, int(entity_id)


def current_entity_id(identity=None):
    """Return just the integer id from the current/given identity."""
    return parse_identity(identity)[1]
