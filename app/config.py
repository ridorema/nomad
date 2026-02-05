import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    # =========================
    # Core
    # =========================
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")

    # =========================
    # Database
    # =========================
    # DEV: SQLite
    # PROD: vendos DATABASE_URL në environment (PostgreSQL)
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{BASE_DIR / 'crm.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # =========================
    # Uploads
    # =========================
    UPLOAD_FOLDER = os.environ.get(
        "UPLOAD_FOLDER",
        str(BASE_DIR / "uploads")
    )
    MAX_CONTENT_LENGTH = 20 * 1024 * 1024  # 20 MB per file

    # =========================
    # Business settings
    # =========================
    BASE_CURRENCY = "EUR"
    SUPPORTED_CURRENCIES = ["EUR", "ALL", "USD", "GBP"]

    # =========================
    # Pagination (future-proof)
    # =========================
    DEFAULT_PAGE_SIZE = 25
    MAX_PAGE_SIZE = 100

    # =========================
    # Security
    # =========================
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # =========================
    # Environment
    # =========================
    ENV = os.environ.get("FLASK_ENV", "development")
    DEBUG = ENV == "development"
