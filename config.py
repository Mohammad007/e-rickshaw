"""Application configuration."""
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'erickshaw-india-2024-secret')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'erickshaw-jwt-secret-key')
    # No expiry for simplicity (matches spec). Set a value in production.
    JWT_ACCESS_TOKEN_EXPIRES = False

    DATABASE = os.environ.get('DATABASE', os.path.join(BASE_DIR, 'erickshaw.db'))
    SCHEMA = os.path.join(BASE_DIR, 'schema.sql')

    # SocketIO async mode. 'threading' works everywhere (incl. Windows) without eventlet.
    SOCKETIO_ASYNC_MODE = os.environ.get('SOCKETIO_ASYNC_MODE', 'threading')

    # Admin panel default credentials (override in production via env).
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', '12345678')

    # No SMS gateway yet: when true, /auth/send-otp returns the OTP in its
    # response so the app can display it for testing. Set DEV_SHOW_OTP=0 once a
    # real SMS provider (MSG91/Fast2SMS) is wired up.
    DEV_SHOW_OTP = os.environ.get('DEV_SHOW_OTP', '1') == '1'
