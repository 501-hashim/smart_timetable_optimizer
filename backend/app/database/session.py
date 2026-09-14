import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from backend.app.core.config import settings

is_sqlite = settings.DATABASE_URL.startswith("sqlite")

engine_kwargs = {}
if is_sqlite:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs["pool_size"] = int(os.getenv("DB_POOL_SIZE", "10"))
    engine_kwargs["max_overflow"] = int(os.getenv("DB_MAX_OVERFLOW", "20"))
    engine_kwargs["pool_recycle"] = 300
    engine_kwargs["pool_pre_ping"] = True

engine = create_engine(settings.DATABASE_URL, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def ensure_schema():
    with engine.connect() as conn:
        try:
            if is_sqlite:
                res = conn.execute(text("PRAGMA table_info(subjects)")).fetchall()
                cols = [r[1] for r in res]
                if cols and "consecutive" not in cols:
                    conn.execute(text("ALTER TABLE subjects ADD COLUMN consecutive BOOLEAN DEFAULT 0"))
                    conn.commit()
        except Exception:
            pass

ensure_schema()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
