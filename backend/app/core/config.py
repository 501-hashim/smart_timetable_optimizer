import os
from typing import List
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "Smart Academic Timetable Optimizer"
    VERSION: str = "1.0.0"

    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development").lower()
    DEBUG: bool = os.getenv("DEBUG", "true" if ENVIRONMENT == "development" else "false").lower() in ("true", "1", "yes")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production-1234567890")

    # Server Binding
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # Database URL
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DEFAULT_SQLITE_PATH: str = os.path.join(BASE_DIR, "timetable.db")
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_SQLITE_PATH}")

    # Convert postgres:// to postgresql:// for SQLAlchemy compatibility (Render/Railway/Heroku standard)
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

    # CORS Allowed Origins
    _raw_origins: str = os.getenv("ALLOWED_ORIGINS", "*")
    ALLOWED_ORIGINS: List[str] = [orig.strip() for orig in _raw_origins.split(",") if orig.strip()] if _raw_origins != "*" else ["*"]

    # Allowed Hosts
    _raw_hosts: str = os.getenv("ALLOWED_HOSTS", "*")
    ALLOWED_HOSTS: List[str] = [h.strip() for h in _raw_hosts.split(",") if h.strip()] if _raw_hosts != "*" else ["*"]

settings = Settings()
