"""Lightweight data helpers.

The route layer uses raw SQL against the SQLite connection (see `database.py`).
These modules document each table's columns and provide small serialization
helpers (`to_dict`) so responses can be shaped consistently if needed.
"""
from .user import User
from .driver import Driver
from .booking import Booking
from .fare import FareRule

__all__ = ['User', 'Driver', 'Booking', 'FareRule']
