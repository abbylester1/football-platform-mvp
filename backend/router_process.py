import os
import json
import traceback
import cv2
import numpy as np
import onnxruntime
from fastapi import APIRouter, HTTPException
from backend.worker import process_drill_sync
from backend.database import SessionLocal, Drill, DrillStatus
from backend.config import VIDEOS_DIR, YOLO_MODEL

router = APIRouter()

@router.get("/process-diag")
def process_diagnostic():
    results = {}
    try:
        import scipy
        results["scipy"] = f"ok ({scipy.__version__})"
    except Exception as e:
        results["scipy"] = f"fail: {e}"

    try:
        import trimesh
        results["trimesh"] = f"ok ({trimesh.__version__})"
    except Exception as e:
        results["trimesh"] = f"fail: {e}"

    try:
        import onnxruntime
        results["onnxruntime"] = f"ok ({onnxruntime.__version__})"
    except Exception as e:
        results["onnxruntime"] = f"fail: {e}"

    try:
        sess = onnxruntime.InferenceSession(YOLO_MODEL, providers=["CPUExecutionProvider"])
        results["model_load"] = f"ok, input: {sess.get_inputs()[0].name}"
    except Exception as e:
        results["model_load"] = f"fail: {e}"

    try:
        cap = cv2.VideoCapture(0)
        results["opencv"] = f"ok, open={cap.isOpened()}"
        cap.release()
    except Exception as e:
        results["opencv"] = f"fail: {e}"

    try:
        cap = cv2.VideoCapture(os.path.join(VIDEOS_DIR, "doesnotexist.mp4"))
        ret, frame = cap.read()
        results["opencv_read"] = f"ok, ret={ret}"
        cap.release()
    except Exception as e:
        results["opencv_read"] = f"fail: {e}"

    return results

@router.post("/process/{drill_id}")
def start_processing(drill_id: str):
    db = SessionLocal()
    try:
        drill = db.query(Drill).filter(Drill.id == drill_id).first()
        if not drill:
            raise HTTPException(404, "Drill not found")
        drill.status = DrillStatus.PROCESSING.value
        db.commit()
    finally:
        db.close()

    video_path = os.path.join(VIDEOS_DIR, drill.video_key)
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
        return {"status": "complete", "scene_key": result}
    except Exception as e:
        db = SessionLocal()
        try:
            drill = db.query(Drill).filter(Drill.id == drill_id).first()
            if drill:
                drill.status = DrillStatus.FAILED.value
                db.commit()
        finally:
            db.close()
        raise HTTPException(500, f"Processing failed: {str(e)}")
