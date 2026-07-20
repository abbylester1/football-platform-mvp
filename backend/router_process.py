import os
import json
import traceback
from fastapi import APIRouter, HTTPException
from backend.worker import process_drill_sync
from backend.database import SessionLocal, Drill, DrillStatus
from backend.config import VIDEOS_DIR

router = APIRouter()

@router.post("/process/{drill_id}")
def start_processing(drill_id: str):
    try:
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
            db = SessionLocal()
            try:
                drill = db.query(Drill).filter(Drill.id == drill_id).first()
                if drill:
                    drill.status = DrillStatus.FAILED.value
                    db.commit()
            finally:
                db.close()
            raise HTTPException(400, "Video file not found")

        try:
            result = process_drill_sync(drill_id, video_path)
        except Exception as e:
            raise HTTPException(500, f"process_drill_sync failed: {traceback.format_exc()}")

        return {"status": "complete", "scene_key": result}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"start_processing failed: {traceback.format_exc()}")
