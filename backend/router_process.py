import os
import traceback
import threading
import logging
import sys
from fastapi import APIRouter, HTTPException
from database import SessionLocal, Drill, DrillStatus
from config import VIDEOS_DIR

logger = logging.getLogger(__name__)
# Ensure logs go to stdout so Railway captures them
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False

MODULE_VERSION = "v2-reset-and-debug"
router = APIRouter()


def _run_processing(drill_id: str, video_path: str):
    import faulthandler
    faulthandler.enable()
    try:
        logger.info(f"Starting processing for drill {drill_id}")
        from worker import process_drill_sync
        result = process_drill_sync(drill_id, video_path)
        logger.info(f"Processing completed for drill {drill_id}, scene={result}")
        db = SessionLocal()
        try:
            drill = db.query(Drill).filter(Drill.id == drill_id).first()
            if drill:
                drill.scene_key = os.path.basename(result)
                drill.status = DrillStatus.REVIEW.value
                db.commit()
                logger.info(f"Drill {drill_id} saved with status REVIEW")
        finally:
            db.close()
    except Exception:
        logger.error(f"Processing failed for drill {drill_id}: {traceback.format_exc()}")
        sys.stdout.flush()
        try:
            db = SessionLocal()
            try:
                drill = db.query(Drill).filter(Drill.id == drill_id).first()
                if drill:
                    drill.status = DrillStatus.FAILED.value
                    db.commit()
                    logger.info(f"Drill {drill_id} set to FAILED")
            finally:
                db.close()
        except Exception:
            logger.error(f"Failed to update drill {drill_id} to FAILED status: {traceback.format_exc()}")
            sys.stdout.flush()

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


@router.post("/process/{drill_id}/reset")
def reset_processing(drill_id: str):
    db = SessionLocal()
    try:
        drill = db.query(Drill).filter(Drill.id == drill_id).first()
        if not drill:
            raise HTTPException(404, "Drill not found")
        drill.status = DrillStatus.UPLOADING.value
        drill.detected_objects = []
        drill.scene_key = ""
        db.commit()
        return {"status": "reset"}
    finally:
        db.close()


@router.post("/debug/test-process/{drill_id}")
def debug_process(drill_id: str):
    """Sync process test — runs inline, not in background thread."""
    from config import VIDEOS_DIR, SCENES_DIR
    db = SessionLocal()
    try:
        drill = db.query(Drill).filter(Drill.id == drill_id).first()
        if not drill:
            raise HTTPException(404, "Drill not found")
        video_key = drill.video_key
    finally:
        db.close()

    video_path = os.path.join(VIDEOS_DIR, video_key)
    if not os.path.exists(video_path):
        return {"error": f"Video not found at {video_path}", "videos_dir": VIDEOS_DIR, "files": os.listdir(VIDEOS_DIR) if os.path.isdir(VIDEOS_DIR) else []}

    from worker import process_drill_sync
    try:
        result = process_drill_sync(drill_id, video_path)
        return {"status": "ok", "scene": result, "detected_objects_count": 0}
    except Exception as e:
        return {"status": "error", "error": str(e), "traceback": traceback.format_exc()}
