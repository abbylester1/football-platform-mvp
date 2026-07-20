import os
import uuid
import aiofiles
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from backend.config import VIDEOS_DIR, ALLOWED_EXTENSIONS, MAX_UPLOAD_SIZE
from backend.database import SessionLocal, Drill, DrillStatus
from backend.models import DrillResponse

router = APIRouter()

@router.post("/upload", response_model=DrillResponse)
async def upload_drill(
    name: str = Form(...),
    category: str = Form(""),
    age_group: str = Form(""),
    difficulty: str = Form(""),
    description: str = Form(""),
    file: UploadFile = File(...)
):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported format. Allowed: {ALLOWED_EXTENSIONS}")

    os.makedirs(VIDEOS_DIR, exist_ok=True)
    drill_id = str(uuid.uuid4())
    video_filename = f"{drill_id}{ext}"
    video_path = os.path.join(VIDEOS_DIR, video_filename)

    total = 0
    async with aiofiles.open(video_path, "wb") as f:
        while chunk := await file.read(8 * 1024 * 1024):
            total += len(chunk)
            if total > MAX_UPLOAD_SIZE:
                os.remove(video_path)
                raise HTTPException(400, f"File exceeds {MAX_UPLOAD_SIZE // (1024**3)}GB limit")
            await f.write(chunk)

    db = SessionLocal()
    try:
        drill = Drill(
            id=drill_id,
            name=name,
            category=category,
            age_group=age_group,
            difficulty=difficulty,
            description=description,
            video_key=video_filename,
            status=DrillStatus.UPLOADING.value,
        )
        db.add(drill)
        db.commit()
        db.refresh(drill)
    except Exception:
        db.rollback()
        os.remove(video_path)
        raise
    finally:
        db.close()

    return drill
