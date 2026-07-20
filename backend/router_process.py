import os
import json
import traceback
import threading
from fastapi import APIRouter, HTTPException
from backend.database import SessionLocal, Drill, DrillStatus
from backend.config import VIDEOS_DIR, SCENES_DIR

router = APIRouter()

def _run_processing(drill_id: str, video_path: str):
    try:
        from backend.worker import process_drill_sync
        result = process_drill_sync(drill_id, video_path)
        db = SessionLocal()
        try:
            drill = db.query(Drill).filter(Drill.id == drill_id).first()
            if drill:
                drill.scene_key = os.path.basename(result)
                drill.status = DrillStatus.REVIEW.value
                db.commit()
        finally:
            db.close()
    except BaseException as e:
        db = SessionLocal()
        try:
            drill = db.query(Drill).filter(Drill.id == drill_id).first()
            if drill:
                drill.status = DrillStatus.FAILED.value
                db.commit()
        finally:
            db.close()

@router.post("/process/{drill_id}")
def start_processing(drill_id: str):
    db = SessionLocal()
    try:
        drill = db.query(Drill).filter(Drill.id == drill_id).first()
        if not drill:
            raise HTTPException(404, "Drill not found")
        drill.status = DrillStatus.PROCESSING.value
        db.commit()
        video_key = drill.video_key
    finally:
        db.close()

    video_path = os.path.join(VIDEOS_DIR, video_key)
    if not os.path.exists(video_path):
        raise HTTPException(400, "Video file not found")

    thread = threading.Thread(target=_run_processing, args=(drill_id, video_path), daemon=True)
    thread.start()

    return {"status": "processing"}

@router.get("/process/{drill_id}/status")
def process_status(drill_id: str):
    db = SessionLocal()
    try:
        drill = db.query(Drill).filter(Drill.id == drill_id).first()
        if not drill:
            raise HTTPException(404, "Drill not found")
        return {
            "status": drill.status,
            "scene_key": drill.scene_key or "",
        }
    finally:
        db.close()
