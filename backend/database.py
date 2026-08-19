from sqlalchemy import create_engine, Column, String, Text, Float, Integer, DateTime, JSON, Enum
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, timezone
import enum
import uuid

import os
from config import DATABASE_URL, STORAGE_DIR, VIDEOS_DIR, SCENES_DIR

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class DrillStatus(str, enum.Enum):
    UPLOADING = "uploading"
    PROCESSING = "processing"
    REVIEW = "review"
    READY = "ready"
    FAILED = "failed"

class Drill(Base):
    __tablename__ = "drills"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    category = Column(String, default="")
    age_group = Column(String, default="")
    difficulty = Column(String, default="")
    description = Column(Text, default="")
    video_key = Column(String, nullable=False)
    status = Column(String, default=DrillStatus.UPLOADING.value)
    detected_objects = Column(JSON, default=list)
    scene_key = Column(String, default="")
    scene_analysis = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

def init_db():
    os.makedirs(STORAGE_DIR, exist_ok=True)
    os.makedirs(VIDEOS_DIR, exist_ok=True)
    os.makedirs(SCENES_DIR, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    # Add new columns if missing (SQLite migration)
    with engine.connect() as conn:
        try:
            conn.execute("SELECT scene_analysis FROM drills LIMIT 1")
        except Exception:
            conn.execute("ALTER TABLE drills ADD COLUMN scene_analysis JSON DEFAULT '{}'" )
            conn.commit()
    return SessionLocal()
