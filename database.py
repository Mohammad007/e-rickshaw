"""SQLite database initialization and connection helpers."""
import sqlite3
from flask import g
from config import Config


def get_conn():
    """Open a fresh connection. Use OUTSIDE a request context (e.g. SocketIO
    handlers, scripts). Caller is responsible for closing it."""
    conn = sqlite3.connect(Config.DATABASE)
    conn.row_factory = sqlite3.Row
    # Enforce foreign keys.
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_db():
    """Connection bound to the current request context (Flask `g`).
    Closed automatically by `close_db` on teardown."""
    if 'db' not in g:
        g.db = get_conn()
    return g.db


def close_db(exception=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def _column_exists(db, table, column):
    cols = [r[1] for r in db.execute(f"PRAGMA table_info({table})").fetchall()]
    return column in cols


def _migrate(db):
    """Add columns introduced after the initial schema (CREATE TABLE IF NOT
    EXISTS won't alter existing tables, so apply ALTERs here idempotently)."""
    migrations = [
        # (table, column, DDL)
        ('fare_rules', 'per_person_extra',
         "ALTER TABLE fare_rules ADD COLUMN per_person_extra DECIMAL(8,2) DEFAULT 5.0"),
        ('bookings', 'persons',
         "ALTER TABLE bookings ADD COLUMN persons INTEGER DEFAULT 1"),
        ('bookings', 'offered_driver_id',
         "ALTER TABLE bookings ADD COLUMN offered_driver_id INTEGER"),
        ('bookings', 'offer_expires_at',
         "ALTER TABLE bookings ADD COLUMN offer_expires_at DATETIME"),
    ]
    for table, column, ddl in migrations:
        if not _column_exists(db, table, column):
            db.execute(ddl)


def init_db():
    """Create all tables from schema.sql if they don't exist, then migrate."""
    db = get_conn()
    with open(Config.SCHEMA, 'r', encoding='utf-8') as f:
        db.executescript(f.read())
    _migrate(db)
    db.commit()
    db.close()
    print("✅ Database initialized successfully")
