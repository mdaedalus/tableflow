import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-in-production-please")
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'restaurant.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
    QR_FOLDER = os.path.join(BASE_DIR, "static", "qrcodes")
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB
    LANGUAGES = ["tr", "en"]