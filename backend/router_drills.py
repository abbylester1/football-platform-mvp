import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from database import SessionLocal, Drill, DrillStatus
from models import DrillResponse, ObjectUpdate
from config import VIDEOS_DIR, SCENES_DIR

router = APIRouter()

@router.get("/drills", response_model=list[DrillResponse])
def list_drills():
    db = SessionLocal()
    try:
        drills = db.query(Drill).order_by(Drill.created_at.desc()).all()
    finally:
        db.close()
    return drills

@router.get("/drills/{drill_id}", response_model=DrillResponse)
def get_drill(drill_id: str):
    db = SessionLocal()
    try:
        drill = db.query(Drill).filter(Drill.id == drill_id).first()
    finally:
        db.close()
    if not drill:
        raise HTTPException(404, "Drill not found")
    return drill

@router.put("/drills/{drill_id}/objects", response_model=DrillResponse)
def update_objects(drill_id: str, update: ObjectUpdate):
    db = SessionLocal()
    try:
        drill = db.query(Drill).filter(Drill.id == drill_id).first()
        if not drill:
            raise HTTPException(404, "Drill not found")
        drill.detected_objects = [obj.model_dump() for obj in update.detected_objects]
        drill.status = DrillStatus.REVIEW.value
        db.commit()
        db.refresh(drill)
    finally:
        db.close()
    return drill

@router.post("/drills/{drill_id}/generate")
def generate_3d(drill_id: str):
    db = SessionLocal()
    try:
        drill = db.query(Drill).filter(Drill.id == drill_id).first()
        if not drill:
            raise HTTPException(404, "Drill not found")
        drill.status = DrillStatus.PROCESSING.value
        db.commit()
    finally:
        db.close()
    return {"status": "processing"}

@router.get("/video/{video_key}")
def serve_video(video_key: str):
    safe_path = os.path.realpath(os.path.join(VIDEOS_DIR, video_key))
    videos_dir = os.path.realpath(VIDEOS_DIR)
    if not safe_path.startswith(videos_dir):
        raise HTTPException(400, "Invalid path")
    if not os.path.exists(safe_path):
        raise HTTPException(404, "Video not found")
    ext = os.path.splitext(video_key)[1].lower()
    media_type = {"mp4": "video/mp4", "mov": "video/quicktime"}.get(ext, "application/octet-stream")
    return FileResponse(safe_path, media_type=media_type)

@router.get("/scene/{scene_key}")
def serve_scene(scene_key: str):
    safe_path = os.path.realpath(os.path.join(SCENES_DIR, scene_key))
    scenes_dir = os.path.realpath(SCENES_DIR)
    if not safe_path.startswith(scenes_dir):
        raise HTTPException(400, "Invalid path")
    if not os.path.exists(safe_path):
        raise HTTPException(404, "Scene not found")
    return FileResponse(safe_path, media_type="model/gltf-binary")
