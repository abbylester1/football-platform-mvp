# AI Football Drill Digitization MVP — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a 2-3 week sprint prototype where a coach uploads a football drill video and gets back an interactive 3D scene with tracked player/ball/cone movement.

**Architecture:** Next.js frontend (upload + 3D viewer) talks to a FastAPI backend that queues processing jobs to a Python worker. The worker runs YOLOv11 detection → ByteTrack tracking → 2D→3D projection → animation → GLB export. Results stored locally (S3-compatible in production).

**Tech Stack:** Next.js 14+, React Three Fiber, Tailwind, FastAPI, YOLOv11 (Ultralytics), ByteTrack, OpenCV, SQLite, local file storage.

---

## File Structure

```
football-mvp/
├── frontend/                    # Next.js app
│   ├── package.json
│   ├── next.config.js
│   ├── tailwind.config.js
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx              # Drill library / home
│   │   ├── upload/
│   │   │   └── page.tsx          # Upload form
│   │   ├── drill/
│   │   │   └── [id]/
│   │   │       ├── page.tsx      # Drill detail (review or viewer)
│   │   │       └── viewer.tsx    # 3D viewer component
│   │   └── api/                  # API routes
│   │       ├── upload/route.ts
│   │       ├── drills/route.ts
│   │       ├── drills/[id]/route.ts
│   │       └── process/route.ts
│   └── components/
│       ├── UploadForm.tsx
│       ├── ProcessingStatus.tsx
│       ├── ReviewScreen.tsx
│       ├── Viewer3D.tsx
│       ├── AvatarLibrary.tsx
│       └── VideoPlayer.tsx
│
├── backend/                     # FastAPI + Worker
│   ├── requirements.txt
│   ├── main.py                  # FastAPI app
│   ├── database.py              # SQLite models
│   ├── models.py                # Pydantic schemas
│   ├── router_uploads.py        # Upload endpoints
│   ├── router_drills.py         # Drill CRUD endpoints
│   ├── router_process.py        # Processing endpoints + WebSocket
│   ├── worker.py                # AI pipeline worker
│   ├── detection.py             # YOLOv11 detection
│   ├── tracking.py              # ByteTrack / Kalman filter
│   ├── calibration.py           # Homography calibration
│   ├── projection.py            # 2D→3D projection
│   ├── smoothing.py             # Trajectory smoothing
│   ├── animation.py             # Animation generation + GLB export
│   └── config.py                # Configuration
│
├── data/                        # Local storage
│   ├── videos/
│   ├── scenes/
│   └── avatars/                 # Pre-rigged avatar GLB files
│
├── tests/
│   ├── test_detection.py
│   ├── test_tracking.py
│   ├── test_calibration.py
│   ├── test_projection.py
│   ├── test_smoothing.py
│   └── test_animation.py
│
└── docker-compose.yml
```

---

### Task 1: Project Scaffold — Backend

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/config.py`
- Create: `backend/database.py`
- Create: `backend/models.py`
- Create: `backend/main.py`

- [ ] **Step 1: Write requirements.txt**

```
fastapi==0.115.0
uvicorn[standard]==0.30.0
sqlalchemy==2.0.35
pydantic==2.9.0
python-multipart==0.0.9
websockets==13.0
opencv-python-headless==4.10.0
numpy==1.26.0
ultralytics==8.3.0
scipy==1.14.0
trimesh==4.4.0
```

- [ ] **Step 2: Write config.py**

```python
import os

STORAGE_DIR = os.environ.get("STORAGE_DIR", "data")
VIDEOS_DIR = os.environ.get("VIDEOS_DIR", os.path.join(STORAGE_DIR, "videos"))
SCENES_DIR = os.environ.get("SCENES_DIR", os.path.join(STORAGE_DIR, "scenes"))
AVATARS_DIR = os.environ.get("AVATARS_DIR", os.path.join(STORAGE_DIR, "avatars"))

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///data/football.db")

MAX_UPLOAD_SIZE = 2 * 1024 * 1024 * 1024  # 2GB
ALLOWED_EXTENSIONS = {".mp4", ".mov"}

YOLO_MODEL = "yolo11n.pt"
DETECTION_CONFIDENCE = 0.3
FRAME_INTERVAL = 5  # Process every Nth frame
```

- [ ] **Step 3: Write database.py**

```python
from sqlalchemy import create_engine, Column, String, Text, Float, Integer, DateTime, JSON, Enum
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, timezone
import enum
import uuid

from .config import DATABASE_URL

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
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

def init_db():
    Base.metadata.create_all(bind=engine)
    return SessionLocal()
```

- [ ] **Step 4: Write models.py**

```python
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class FramePosition(BaseModel):
    frame: int
    x: float
    y: float
    w: float = 0
    h: float = 0

class DetectedObject(BaseModel):
    type: str  # "player" | "ball" | "cone"
    id: str
    label: str = ""
    avatar_id: str = ""
    frames: List[FramePosition]

class DrillCreate(BaseModel):
    name: str
    category: str = ""
    age_group: str = ""
    difficulty: str = ""
    description: str = ""

class DrillResponse(BaseModel):
    id: str
    name: str
    category: str
    age_group: str
    difficulty: str
    description: str
    video_key: str
    status: str
    detected_objects: list
    scene_key: str
    created_at: datetime
    updated_at: datetime

class ObjectUpdate(BaseModel):
    detected_objects: List[DetectedObject]

class ProcessingStatus(BaseModel):
    status: str
    progress: float = 0.0
    message: str = ""
```

- [ ] **Step 5: Write main.py**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import init_db
from .router_uploads import router as upload_router
from .router_drills import router as drill_router
from .router_process import router as process_router

app = FastAPI(title="Football Drill MVP")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router, prefix="/api")
app.include_router(drill_router, prefix="/api")
app.include_router(process_router, prefix="/api")

@app.on_event("startup")
def startup():
    init_db()

@app.get("/api/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 6: Commit**

```bash
git add backend/
git commit -m "feat: scaffold FastAPI backend with SQLite models"
```

---

### Task 2: Upload and Drill CRUD Endpoints

**Files:**
- Create: `backend/router_uploads.py`
- Create: `backend/router_drills.py`
- Modify: `backend/main.py` (already done)

- [ ] **Step 1: Write router_uploads.py**

```python
import os
import uuid
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from .config import VIDEOS_DIR, ALLOWED_EXTENSIONS, MAX_UPLOAD_SIZE
from .database import SessionLocal, Drill, DrillStatus
from .models import DrillResponse
from datetime import datetime, timezone

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

    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(400, "File exceeds 2GB limit")

    with open(video_path, "wb") as f:
        f.write(content)

    db = SessionLocal()
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
    db.close()

    return DrillResponse(
        id=drill.id,
        name=drill.name,
        category=drill.category,
        age_group=drill.age_group,
        difficulty=drill.difficulty,
        description=drill.description,
        video_key=drill.video_key,
        status=drill.status,
        detected_objects=drill.detected_objects,
        scene_key=drill.scene_key,
        created_at=drill.created_at,
        updated_at=drill.updated_at,
    )
```

- [ ] **Step 2: Write router_drills.py**

```python
from fastapi import APIRouter, HTTPException
from .database import SessionLocal, Drill
from .models import DrillResponse, ObjectUpdate

router = APIRouter()

@router.get("/drills", response_model=list[DrillResponse])
def list_drills():
    db = SessionLocal()
    drills = db.query(Drill).order_by(Drill.created_at.desc()).all()
    db.close()
    return drills

@router.get("/drills/{drill_id}", response_model=DrillResponse)
def get_drill(drill_id: str):
    db = SessionLocal()
    drill = db.query(Drill).filter(Drill.id == drill_id).first()
    db.close()
    if not drill:
        raise HTTPException(404, "Drill not found")
    return drill

@router.put("/drills/{drill_id}/objects", response_model=DrillResponse)
def update_objects(drill_id: str, update: ObjectUpdate):
    db = SessionLocal()
    drill = db.query(Drill).filter(Drill.id == drill_id).first()
    if not drill:
        db.close()
        raise HTTPException(404, "Drill not found")
    drill.detected_objects = [obj.model_dump() for obj in update.detected_objects]
    drill.status = "review"
    db.commit()
    db.refresh(drill)
    db.close()
    return drill

@router.post("/drills/{drill_id}/generate")
def generate_3d(drill_id: str):
    db = SessionLocal()
    drill = db.query(Drill).filter(Drill.id == drill_id).first()
    if not drill:
        db.close()
        raise HTTPException(404, "Drill not found")
    drill.status = "processing"
    db.commit()
    db.close()
    # Worker picks up via in-process queue (Task 8)
    return {"status": "processing"}
```

- [ ] **Step 3: Commit**

```bash
git add backend/router_uploads.py backend/router_drills.py
git commit -m "feat: upload and drill CRUD endpoints"
```

---

### Task 3: Detection Module (YOLOv11)

**Files:**
- Create: `backend/detection.py`
- Create: `tests/test_detection.py`

- [ ] **Step 1: Write the test**

```python
import pytest
import numpy as np
from backend.detection import detect_objects

def test_detect_objects_returns_expected_keys():
    dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    results = detect_objects(dummy_frame)
    assert isinstance(results, list)
    for obj in results:
        assert "type" in obj
        assert "bbox" in obj
        assert "confidence" in obj
        assert obj["type"] in ("player", "ball", "cone")
        assert len(obj["bbox"]) == 4

def test_detect_objects_handles_empty_frame():
    results = detect_objects(None)
    assert results == []

def test_detect_objects_confidence_threshold():
    dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    results = detect_objects(dummy_frame, confidence_threshold=0.9)
    assert isinstance(results, list)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_detection.py -v`
Expected: FAIL with "cannot import detect_objects"

- [ ] **Step 3: Write detection.py**

```python
from ultralytics import YOLO
import numpy as np
from .config import YOLO_MODEL, DETECTION_CONFIDENCE

_model = None

def _get_model():
    global _model
    if _model is None:
        _model = YOLO(YOLO_MODEL)
    return _model

# COCO class IDs relevant to football
COCO_CLASS_MAP = {
    0: "player",   # person
    32: "ball",    # sports ball
}

def detect_objects(frame: np.ndarray | None, confidence_threshold: float = DETECTION_CONFIDENCE) -> list[dict]:
    if frame is None:
        return []

    model = _get_model()
    results = model(frame, conf=confidence_threshold, verbose=False)
    detections = []

    for r in results:
        for box in r.boxes:
            cls_id = int(box.cls[0])
            mapped_type = COCO_CLASS_MAP.get(cls_id)
            if mapped_type is None:
                continue
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            conf = float(box.conf[0])
            detections.append({
                "type": mapped_type,
                "bbox": [x1, y1, x2, y2],
                "confidence": conf,
            })

    return detections
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_detection.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/detection.py tests/test_detection.py
git commit -m "feat: YOLOv11 detection module for players, ball, cones"
```

---

### Task 4: Tracking Module (ByteTrack / Kalman)

**Files:**
- Create: `backend/tracking.py`
- Create: `tests/test_tracking.py`

- [ ] **Step 1: Write the test**

```python
import pytest
from backend.tracking import track_objects

def test_track_objects_assigns_ids():
    detections = [
        {"type": "player", "bbox": [10, 10, 50, 80], "confidence": 0.9},
        {"type": "player", "bbox": [100, 100, 140, 180], "confidence": 0.85},
        {"type": "ball", "bbox": [200, 150, 210, 160], "confidence": 0.7},
    ]
    tracked = track_objects(detections, frame_idx=0)
    assert len(tracked) == 3
    for obj in tracked:
        assert "track_id" in obj
        assert isinstance(obj["track_id"], int)

def test_track_objects_stable_ids_across_frames():
    d1 = [{"type": "player", "bbox": [10, 10, 50, 80], "confidence": 0.9}]
    d2 = [{"type": "player", "bbox": [12, 12, 52, 82], "confidence": 0.9}]
    t1 = track_objects(d1, frame_idx=0)
    t2 = track_objects(d2, frame_idx=1)
    assert t1[0]["track_id"] == t2[0]["track_id"]

def test_track_objects_empty():
    assert track_objects([], frame_idx=0) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_tracking.py -v`
Expected: FAIL

- [ ] **Step 3: Write tracking.py**

```python
import numpy as np
from scipy.optimize import linear_sum_assignment

class _TrackerState:
    def __init__(self):
        self.next_id = 1
        self.active_tracks: dict[int, dict] = {}
        self.max_disappeared = 10

    def reset(self):
        self.next_id = 1
        self.active_tracks.clear()

_tracker = _TrackerState()

def _iou(box_a: list[float], box_b: list[float]) -> float:
    x1 = max(box_a[0], box_b[0])
    y1 = max(box_a[1], box_b[1])
    x2 = min(box_a[2], box_b[2])
    y2 = min(box_a[3], box_b[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    area_a = (box_a[2] - box_a[0]) * (box_a[3] - box_a[1])
    area_b = (box_b[2] - box_b[0]) * (box_b[3] - box_b[1])
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0

def track_objects(detections: list[dict], frame_idx: int) -> list[dict]:
    if not detections:
        for tid in list(_tracker.active_tracks.keys()):
            _tracker.active_tracks[tid]["disappeared"] += 1
            if _tracker.active_tracks[tid]["disappeared"] > _tracker.max_disappeared:
                del _tracker.active_tracks[tid]
        return []

    det_boxes = [d["bbox"] for d in detections]
    track_boxes = [t["bbox"] for t in _tracker.active_tracks.values()]

    if not _tracker.active_tracks:
        for d in detections:
            tid = _tracker.next_id
            _tracker.next_id += 1
            _tracker.active_tracks[tid] = {**d, "disappeared": 0, "track_id": tid}
        return list(_tracker.active_tracks.values())

    # Build IoU cost matrix
    cost = np.ones((len(track_boxes), len(det_boxes)))
    for i, tb in enumerate(track_boxes):
        for j, db in enumerate(det_boxes):
            cost[i, j] = 1.0 - _iou(tb, db)

    row_idx, col_idx = linear_sum_assignment(cost)
    matched_dets = set()
    matched_tracks = set()

    for r, c in zip(row_idx, col_idx):
        if cost[r, c] < 0.7:  # IoU threshold
            tid = list(_tracker.active_tracks.keys())[r]
            _tracker.active_tracks[tid] = {
                **detections[c],
                "track_id": tid,
                "disappeared": 0,
            }
            matched_tracks.add(tid)
            matched_dets.add(c)

    # Unmatched detections -> new tracks
    for j in range(len(detections)):
        if j not in matched_dets:
            tid = _tracker.next_id
            _tracker.next_id += 1
            _tracker.active_tracks[tid] = {**detections[j], "track_id": tid, "disappeared": 0}

    # Unmatched tracks increment disappeared
    for tid in list(_tracker.active_tracks.keys()):
        if tid not in matched_tracks:
            _tracker.active_tracks[tid]["disappeared"] += 1
            if _tracker.active_tracks[tid]["disappeared"] > _tracker.max_disappeared:
                del _tracker.active_tracks[tid]

    return list(_tracker.active_tracks.values())

def reset_tracker():
    _tracker.reset()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_tracking.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/tracking.py tests/test_tracking.py
git commit -m "feat: IoU-based multi-object tracker"
```

---

### Task 5: Camera Calibration and 2D→3D Projection

**Files:**
- Create: `backend/calibration.py`
- Create: `backend/projection.py`
- Create: `tests/test_calibration.py`
- Create: `tests/test_projection.py`

- [ ] **Step 1: Write calibration.py**

```python
import cv2
import numpy as np

def estimate_homography(cone_positions: list[tuple[float, float]], field_width: float = 105.0, field_height: float = 68.0) -> np.ndarray | None:
    if len(cone_positions) < 4:
        return None
    src_pts = np.array(cone_positions, dtype=np.float32).reshape(-1, 1, 2)
    dst_pts = _estimate_field_points(len(cone_positions), field_width, field_height)
    H, _ = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
    return H

def _estimate_field_points(n: int, fw: float, fh: float) -> np.ndarray:
    if n == 4:
        return np.array([[0, 0], [fw, 0], [fw, fh], [0, fh]], dtype=np.float32).reshape(-1, 1, 2)
    # For >4 cones, distribute evenly on field perimeter
    pts = []
    perimeter = 2 * (fw + fh)
    for i in range(n):
        t = (i / n) * perimeter
        if t < fw:
            pts.append([t, 0])
        elif t < fw + fh:
            pts.append([fw, t - fw])
        elif t < 2 * fw + fh:
            pts.append([2 * fw + fh - t, fh])
        else:
            pts.append([0, perimeter - t])
    return np.array(pts, dtype=np.float32).reshape(-1, 1, 2)

def detect_cones_in_frame(frame: np.ndarray) -> list[tuple[float, float]]:
    return []  # Placeholder: color-based cone detection, enhanced in iteration
```

- [ ] **Step 2: Write projection.py**

```python
import numpy as np

def project_to_3d(
    x: float,
    y: float,
    homography: np.ndarray | None,
    frame_width: int = 640,
    frame_height: int = 480,
    field_scale: float = 30.0,
) -> tuple[float, float, float]:
    if homography is not None:
        pt = np.array([[[x, y]]], dtype=np.float32)
        transformed = cv2.perspectiveTransform(pt, homography)
        return (float(transformed[0, 0, 0]), 0.0, float(transformed[0, 0, 1]))

    # Fallback: map pixel coords to a field plane
    nx = (x / frame_width) * field_scale - field_scale / 2
    nz = (1.0 - y / frame_height) * field_scale * 0.6
    return (nx, 0.0, nz)
```

- [ ] **Step 3: Commit**

```bash
git add backend/calibration.py backend/projection.py
git commit -m "feat: camera calibration and 2D-to-3D projection"
```

---

### Task 6: Trajectory Smoothing

**Files:**
- Create: `backend/smoothing.py`
- Create: `tests/test_smoothing.py`

- [ ] **Step 1: Write the test**

```python
import pytest
import numpy as np
from backend.smoothing import smooth_trajectory

def test_smooth_trajectory_reduces_jitter():
    noisy = [(float(i), 0.0, float(i) + (0.5 if i % 2 == 0 else -0.5)) for i in range(20)]
    smoothed = smooth_trajectory(noisy)
    assert len(smoothed) == len(noisy)
    diffs = [abs(smoothed[i][2] - noisy[i][2]) for i in range(len(noisy))]
    assert sum(diffs) < len(noisy) * 0.3

def test_smooth_trajectory_short():
    assert smooth_trajectory([(0.0, 0.0, 0.0)]) == [(0.0, 0.0, 0.0)]

def test_smooth_trajectory_empty():
    assert smooth_trajectory([]) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_smoothing.py -v`
Expected: FAIL

- [ ] **Step 3: Write smoothing.py**

```python
import numpy as np
from scipy.signal import savgol_filter

def smooth_trajectory(positions: list[tuple[float, float, float]], window: int = 5, polyorder: int = 2) -> list[tuple[float, float, float]]:
    if len(positions) <= window:
        return positions

    arr = np.array(positions)
    smoothed = np.copy(arr)

    for dim in range(3):
        col = arr[:, dim]
        w = min(window, len(col) if len(col) % 2 == 1 else len(col) - 1)
        if w < 3:
            continue
        try:
            smoothed[:, dim] = savgol_filter(col, w, polyorder)
        except Exception:
            pass

    return [(float(x), float(y), float(z)) for x, y, z in smoothed]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_smoothing.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/smoothing.py tests/test_smoothing.py
git commit -m "feat: Savitzky-Golay trajectory smoothing"
```

---

### Task 7: Animation Generation and GLB Export

**Files:**
- Create: `backend/animation.py`
- Create: `tests/test_animation.py`

- [ ] **Step 1: Write the test**

```python
import pytest
from backend.animation import build_scene

def test_build_scene_returns_glb_path():
    objects = [
        {"type": "player", "id": "P1", "frames": [{"frame": 0, "x": 0, "y": 0, "z": 0}, {"frame": 1, "x": 1, "y": 0, "z": 1}]},
        {"type": "ball", "id": "B1", "frames": [{"frame": 0, "x": 2, "y": 0, "z": 2}]},
    ]
    path = build_scene(objects, "test_drill", "data/scenes")
    assert path.endswith(".glb")

def test_build_scene_with_empty_objects():
    path = build_scene([], "empty_drill", "data/scenes")
    assert path.endswith(".glb")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_animation.py -v`
Expected: FAIL

- [ ] **Step 3: Write animation.py**

```python
import os
import json
import trimesh
import numpy as np

def build_scene(objects: list[dict], drill_id: str, scenes_dir: str, avatar_dir: str = "data/avatars") -> str:
    os.makedirs(scenes_dir, exist_ok=True)
    scene = trimesh.Scene()

    # Add field plane
    field = trimesh.creation.box(extents=[30, 0.1, 20])
    field.apply_translation([0, -0.05, 0])
    field.visual.face_colors = [0.2, 0.5, 0.2, 1.0]
    scene.add_geometry(field)

    # Add objects
    for obj in objects:
        if obj["type"] == "player":
            _add_player_avatar(scene, obj, avatar_dir)
        elif obj["type"] == "ball":
            _add_ball(scene, obj)
        elif obj["type"] == "cone":
            _add_cone(scene, obj)

    output_path = os.path.join(scenes_dir, f"{drill_id}.glb")
    scene.export(output_path)
    return output_path

AVATAR_MAP = {
    "standard_red": (0.8, 0.2, 0.2),
    "standard_blue": (0.2, 0.3, 0.8),
    "standard_white": (0.9, 0.9, 0.9),
    "standard_black": (0.2, 0.2, 0.2),
    "standard_yellow": (0.9, 0.8, 0.1),
    "standard_green": (0.2, 0.7, 0.2),
    "lean_red": (0.7, 0.15, 0.15),
    "lean_blue": (0.15, 0.25, 0.7),
    "stocky_red": (0.75, 0.15, 0.15),
    "stocky_blue": (0.15, 0.25, 0.75),
    "youth_red": (1.0, 0.3, 0.3),
    "youth_blue": (0.3, 0.4, 1.0),
    "generic": (1.0, 0.6, 0.0),
}

def _select_avatar(obj: dict) -> tuple[str, tuple[float, float, float]]:
    avatar_id = obj.get("avatar_id", "generic")
    if avatar_id in AVATAR_MAP:
        return avatar_id, AVATAR_MAP[avatar_id]
    return "generic", AVATAR_MAP["generic"]

def _create_avatar_mesh(avatar_id: str, color: tuple[float, float, float], body_type: str = "standard") -> trimesh.Trimesh:
    # Try loading pre-rigged GLB first
    avatar_path = os.path.join(avatar_dir, f"{avatar_id}.glb")
    if os.path.exists(avatar_path):
        mesh = trimesh.load(avatar_path)
        return mesh

    # Fallback procedural avatar
    scale_map = {"lean": (0.85, 1.0, 0.85), "stocky": (1.15, 0.9, 1.15), "youth": (0.7, 0.7, 0.7)}
    scale = scale_map.get(body_type, (1.0, 1.0, 1.0))

    body = trimesh.creation.cylinder(radius=0.15 * scale[0], height=0.6 * scale[1], sections=8)
    body.apply_translation([0, 0.3 * scale[1], 0])
    body.visual.face_colors = [*color, 1.0]

    head = trimesh.creation.sphere(radius=0.1 * scale[0])
    head.apply_translation([0, 0.7 * scale[1], 0])
    head.visual.face_colors = [0.96, 0.82, 0.69, 1.0]

    left_arm = trimesh.creation.cylinder(radius=0.03, height=0.3 * scale[1], sections=4)
    left_arm.apply_translation([-0.15 * scale[0], 0.5 * scale[1], 0])
    left_arm.visual.face_colors = [*color, 1.0]

    right_arm = trimesh.creation.cylinder(radius=0.03, height=0.3 * scale[1], sections=4)
    right_arm.apply_translation([0.15 * scale[0], 0.5 * scale[1], 0])
    right_arm.visual.face_colors = [*color, 1.0]

    return body + head + left_arm + right_arm

def _add_player_avatar(scene, obj, avatar_dir):
    avatar_id, color = _select_avatar(obj)
    body_type = avatar_id.split("_")[0] if "_" in avatar_id else "standard"
    mesh = _create_avatar_mesh(avatar_id, color, body_type)

    if obj.get("frames"):
        pos = obj["frames"][0]
        mesh.apply_translation([pos["x"], 0.0, pos["z"]])
    scene.add_geometry(mesh)

def _add_ball(scene, obj):
    sphere = trimesh.creation.sphere(radius=0.11)
    sphere.visual.face_colors = [1.0, 1.0, 1.0, 1.0]
    if obj.get("frames"):
        pos = obj["frames"][0]
        sphere.apply_translation([pos["x"], 0.11, pos["z"]])
    scene.add_geometry(sphere)

def _add_cone(scene, obj):
    cone = trimesh.creation.cone(radius=0.05, height=0.15, sections=8)
    cone.visual.face_colors = [1.0, 0.6, 0.0, 1.0]
    if obj.get("frames"):
        pos = obj["frames"][0]
        cone.apply_translation([pos["x"], 0.075, pos["z"]])
    scene.add_geometry(cone)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_animation.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/animation.py tests/test_animation.py
git commit -m "feat: GLB scene generation with avatars, ball, cones"
```

---

### Task 8: Worker + Processing Endpoint with WebSocket

**Files:**
- Create: `backend/worker.py`
- Create: `backend/router_process.py`

- [ ] **Step 1: Write worker.py**

```python
import os
import cv2
import json
import threading
from queue import Queue
from .config import VIDEOS_DIR, SCENES_DIR, FRAME_INTERVAL
from .detection import detect_objects
from .tracking import track_objects, reset_tracker
from .projection import project_to_3d
from .calibration import estimate_homography
from .smoothing import smooth_trajectory
from .animation import build_scene
from .database import SessionLocal, Drill, DrillStatus
from datetime import datetime, timezone

_job_queue: Queue = Queue()
_progress_store: dict[str, dict] = {}

def enqueue(drill_id: str):
    _job_queue.put(drill_id)

def get_progress(drill_id: str) -> dict:
    return _progress_store.get(drill_id, {"status": "unknown", "progress": 0, "message": ""})

def _set_progress(drill_id: str, progress: float, message: str, status: str = "processing"):
    _progress_store[drill_id] = {"status": status, "progress": progress, "message": message}

def _worker_loop():
    while True:
        drill_id = _job_queue.get()
        try:
            _process_drill(drill_id)
        except Exception as e:
            _set_progress(drill_id, 0, str(e), "failed")
            db = SessionLocal()
            drill = db.query(Drill).filter(Drill.id == drill_id).first()
            if drill:
                drill.status = DrillStatus.FAILED.value
                db.commit()
            db.close()

def _process_drill(drill_id: str):
    db = SessionLocal()
    drill = db.query(Drill).filter(Drill.id == drill_id).first()
    if not drill:
        db.close()
        return
    db.close()

    video_path = os.path.join(VIDEOS_DIR, drill.video_key)
    if not os.path.exists(video_path):
        _set_progress(drill_id, 0, "Video file not found", "failed")
        return

    _set_progress(drill_id, 0.05, "Opening video...")
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_count = 0
    all_detections = []
    reset_tracker()

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame_count += 1
        if frame_count % FRAME_INTERVAL != 0:
            continue

        detections = detect_objects(frame)
        tracked = track_objects(detections, frame_count)

        for obj in tracked:
            x1, y1, x2, y2 = obj["bbox"]
            cx = (x1 + x2) / 2
            cy = (y1 + y2) / 2
            obj["center"] = (cx, cy)

            # Make frame JSON-serializable (set on the tracked result)
            obj["frame_idx"] = frame_count

        all_detections.extend(tracked)

        progress = 0.05 + 0.6 * (frame_count / max(total_frames, 1))
        _set_progress(drill_id, min(progress, 0.65), f"Tracking... ({frame_count}/{total_frames})")

    cap.release()

    _set_progress(drill_id, 0.7, "Projecting to 3D...")

    # Group tracked objects by track_id
    objects_by_id: dict[int, list] = {}
    for det in all_detections:
        tid = det.get("track_id")
        if tid is None:
            continue
        objects_by_id.setdefault(tid, []).append(det)

    cone_positions_2d = []
    detected_objects_list = []

    for tid, dets in objects_by_id.items():
        obj_type = dets[0]["type"]
        if obj_type == "cone":
            cone_positions_2d.extend([d["center"] for d in dets])

    homography = None
    if len(cone_positions_2d) >= 4:
        _set_progress(drill_id, 0.72, "Calibrating camera...")
        homography = estimate_homography(cone_positions_2d[:4])

    _set_progress(drill_id, 0.75, "Building 3D positions...")

    for tid, dets in objects_by_id.items():
        obj_type = dets[0]["type"]
        label = dets[0].get("type", "")
        frames = []
        for det in dets:
            cx, cy = det["center"]
            h, w = det.get("bbox", [0, 0, 0, 0])[2] - det.get("bbox", [0, 0, 0, 0])[0], det.get("bbox", [0, 0, 0, 0])[3] - det.get("bbox", [0, 0, 0, 0])[1]
            x3d, y3d, z3d = project_to_3d(cx, cy, homography)
            frames.append({
                "frame": det["frame_idx"],
                "x": float(x3d),
                "y": float(y3d),
                "z": float(z3d),
                "w": float(w),
                "h": float(h),
            })

        positions = [(f["x"], f["y"], f["z"]) for f in frames]
        smoothed = smooth_trajectory(positions)
        for i, f in enumerate(frames):
            f["x"], f["y"], f["z"] = smoothed[i]

        detected_objects_list.append({
            "type": obj_type,
            "id": f"{obj_type}_{tid}",
            "label": label,
            "frames": frames,
        })

    _set_progress(drill_id, 0.85, "Generating 3D scene...")

    scene_path = build_scene(detected_objects_list, drill_id, SCENES_DIR)

    _set_progress(drill_id, 0.95, "Saving...")

    db = SessionLocal()
    drill = db.query(Drill).filter(Drill.id == drill_id).first()
    if drill:
        drill.detected_objects = detected_objects_list
        drill.scene_key = os.path.basename(scene_path)
        drill.status = DrillStatus.REVIEW.value
        db.commit()
    db.close()

    _set_progress(drill_id, 1.0, "Complete!", "review")

_thread = threading.Thread(target=_worker_loop, daemon=True)
_thread.start()
```

- [ ] **Step 2: Write router_process.py**

```python
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from .worker import enqueue, get_progress
from .database import SessionLocal, Drill

router = APIRouter()

@router.post("/process/{drill_id}")
def start_processing(drill_id: str):
    db = SessionLocal()
    drill = db.query(Drill).filter(Drill.id == drill_id).first()
    if drill:
        drill.status = "processing"
        db.commit()
    db.close()
    enqueue(drill_id)
    return {"status": "queued"}

@router.websocket("/ws/progress/{drill_id}")
async def progress_websocket(websocket: WebSocket, drill_id: str):
    await websocket.accept()
    try:
        import asyncio
        while True:
            progress = get_progress(drill_id)
            await websocket.send_json(progress)
            if progress["status"] in ("review", "failed", "ready"):
                break
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass
```

- [ ] **Step 3: Commit**

```bash
git add backend/worker.py backend/router_process.py
git commit -m "feat: processing worker with WebSocket progress"
```

---

### Task 9: Next.js Frontend Scaffold

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/next.config.js`
- Create: `frontend/tailwind.config.js`
- Create: `frontend/app/layout.tsx`
- Create: `frontend/app/page.tsx`
- Create: `frontend/app/upload/page.tsx`

- [ ] **Step 1: Write package.json**

```json
{
  "name": "football-mvp-frontend",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start"
  },
  "dependencies": {
    "next": "^14.2.0",
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "three": "^0.168.0",
    "@react-three/fiber": "^8.17.0",
    "@react-three/drei": "^9.111.0",
    "tailwindcss": "^3.4.0",
    "typescript": "^5.5.0",
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "@types/three": "^0.168.0"
  }
}
```

- [ ] **Step 2: Write next.config.js**

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  async rewrites() {
    return [
      { source: '/api/:path*', destination: 'http://localhost:8000/api/:path*' },
    ];
  },
};
module.exports = nextConfig;
```

- [ ] **Step 3: Write tailwind.config.js**

```javascript
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}'],
  theme: { extend: {} },
  plugins: [],
};
```

- [ ] **Step 4: Write app/layout.tsx**

```tsx
import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = { title: 'Football Drill Digitizer', description: 'Convert training videos to interactive 3D drills' };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-gray-950 text-white min-h-screen">{children}</body>
    </html>
  );
}
```

- [ ] **Step 5: Write globals.css**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

- [ ] **Step 6: Write app/page.tsx (Drill library)**

```tsx
'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';

interface Drill { id: string; name: string; status: string; created_at: string; }

export default function Home() {
  const [drills, setDrills] = useState<Drill[]>([]);

  useEffect(() => {
    fetch('/api/drills').then(r => r.json()).then(setDrills).catch(() => {});
  }, []);

  return (
    <main className="max-w-4xl mx-auto p-6">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-2xl font-bold">Football Drills</h1>
        <Link href="/upload" className="bg-green-600 hover:bg-green-700 px-4 py-2 rounded-lg">Upload New Drill</Link>
      </div>

      {drills.length === 0 && <p className="text-gray-400">No drills yet. Upload your first one!</p>}

      <div className="grid gap-4">
        {drills.map(d => (
          <Link key={d.id} href={`/drill/${d.id}`} className="bg-gray-800 p-4 rounded-lg hover:bg-gray-700 flex justify-between items-center">
            <div>
              <div className="font-semibold">{d.name || 'Untitled Drill'}</div>
              <div className="text-sm text-gray-400">{new Date(d.created_at).toLocaleDateString()}</div>
            </div>
            <span className={`px-2 py-1 rounded text-xs ${statusColor(d.status)}`}>{d.status}</span>
          </Link>
        ))}
      </div>
    </main>
  );
}

function statusColor(s: string) {
  switch(s) {
    case 'ready': return 'bg-green-900 text-green-300';
    case 'processing': return 'bg-yellow-900 text-yellow-300';
    case 'review': return 'bg-blue-900 text-blue-300';
    case 'failed': return 'bg-red-900 text-red-300';
    default: return 'bg-gray-700 text-gray-300';
  }
}
```

- [ ] **Step 7: Write app/upload/page.tsx**

```tsx
'use client';
import { useState, useRef } from 'react';
import { useRouter } from 'next/navigation';

export default function UploadPage() {
  const router = useRouter();
  const formRef = useRef<HTMLFormElement>(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setUploading(true);
    const form = new FormData(formRef.current!);

    const res = await fetch('/api/upload', { method: 'POST', body: form });
    if (!res.ok) { alert('Upload failed'); setUploading(false); return; }
    const drill = await res.json();
    router.push(`/drill/${drill.id}`);
  }

  return (
    <main className="max-w-2xl mx-auto p-6">
      <h1 className="text-2xl font-bold mb-6">Upload New Drill</h1>
      <form ref={formRef} onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm mb-1">Video (MP4/MOV, max 2GB)</label>
          <input type="file" name="file" accept=".mp4,.mov" required className="w-full bg-gray-800 rounded p-2" />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm mb-1">Drill Name</label>
            <input type="text" name="name" required className="w-full bg-gray-800 rounded p-2" />
          </div>
          <div>
            <label className="block text-sm mb-1">Category</label>
            <select name="category" className="w-full bg-gray-800 rounded p-2">
              <option value="">Select...</option>
              <option value="passing">Passing</option>
              <option value="movement">Movement</option>
              <option value="possession">Possession</option>
              <option value="shooting">Shooting</option>
            </select>
          </div>
          <div>
            <label className="block text-sm mb-1">Age Group</label>
            <select name="age_group" className="w-full bg-gray-800 rounded p-2">
              <option value="">Select...</option>
              <option value="U10">U10</option>
              <option value="U12">U12</option>
              <option value="U14">U14</option>
              <option value="adult">Adult</option>
            </select>
          </div>
          <div>
            <label className="block text-sm mb-1">Difficulty</label>
            <select name="difficulty" className="w-full bg-gray-800 rounded p-2">
              <option value="">Select...</option>
              <option value="beginner">Beginner</option>
              <option value="intermediate">Intermediate</option>
              <option value="advanced">Advanced</option>
            </select>
          </div>
        </div>
        <div>
          <label className="block text-sm mb-1">Description (optional)</label>
          <textarea name="description" className="w-full bg-gray-800 rounded p-2" rows={3} />
        </div>
        <button type="submit" disabled={uploading} className="bg-green-600 hover:bg-green-700 px-6 py-2 rounded-lg disabled:opacity-50">
          {uploading ? 'Uploading...' : 'Upload & Process'}
        </button>
      </form>
    </main>
  );
}
```

- [ ] **Step 8: Commit**

```bash
git add frontend/
git commit -m "feat: Next.js scaffold with drill library and upload page"
```

---

### Task 10: Review Screen with Video Overlay and Manual Correction

**Files:**
- Create: `frontend/components/VideoPlayer.tsx`
- Create: `frontend/components/ReviewScreen.tsx`
- Create: `frontend/app/drill/[id]/page.tsx` (part 1: review mode)

- [ ] **Step 1: Write VideoPlayer.tsx**

```tsx
'use client';
import { useRef, useEffect, useState } from 'react';

interface BBox { x: number; y: number; w: number; h: number; label: string; color: string; }

export default function VideoPlayer({ src, boundingBoxes, onDrawBox }: {
  src: string;
  boundingBoxes: BBox[];
  onDrawBox?: (box: { x: number; y: number; w: number; h: number }) => void;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [drawing, setDrawing] = useState(false);
  const [startPos, setStartPos] = useState({ x: 0, y: 0 });
  const [currentBox, setCurrentBox] = useState<{ x: number; y: number; w: number; h: number } | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const rect = containerRef.current?.getBoundingClientRect();

  function handleMouseDown(e: React.MouseEvent) {
    if (!onDrawBox) return;
    setDrawing(true);
    const r = containerRef.current!.getBoundingClientRect();
    setStartPos({ x: e.clientX - r.left, y: e.clientY - r.top });
  }

  function handleMouseMove(e: React.MouseEvent) {
    if (!drawing) return;
    const r = containerRef.current!.getBoundingClientRect();
    const x = Math.min(startPos.x, e.clientX - r.left);
    const y = Math.min(startPos.y, e.clientY - r.top);
    const w = Math.abs(e.clientX - r.left - startPos.x);
    const h = Math.abs(e.clientY - r.top - startPos.y);
    setCurrentBox({ x, y, w, h });
  }

  function handleMouseUp() {
    if (drawing && currentBox && onDrawBox) {
      onDrawBox(currentBox);
    }
    setDrawing(false);
    setCurrentBox(null);
  }

  return (
    <div ref={containerRef} className="relative" style={{ aspectRatio: '16/9' }}
      onMouseDown={handleMouseDown} onMouseMove={handleMouseMove} onMouseUp={handleMouseUp}>
      <video ref={videoRef} src={src} controls className="w-full h-full object-contain bg-black rounded" />
      {boundingBoxes.map((b, i) => (
        <div key={i} style={{
          position: 'absolute', left: b.x, top: b.y, width: b.w, height: b.h,
          border: `2px solid ${b.color}`, borderRadius: 4, pointerEvents: 'none',
        }}>
          <span style={{ background: b.color, color: '#fff', fontSize: 10, padding: '0 4px', borderRadius: '0 4px 0 0' }}>{b.label}</span>
        </div>
      ))}
      {currentBox && drawing && (
        <div style={{
          position: 'absolute', left: currentBox.x, top: currentBox.y,
          width: currentBox.w, height: currentBox.h,
          border: '2px dashed #fff', background: 'rgba(255,255,255,0.1)', borderRadius: 4, pointerEvents: 'none',
        }} />
      )}
      {onDrawBox && <div className="absolute bottom-2 left-2 text-xs bg-black/70 px-2 py-1 rounded">Draw a box on a player to add a missing detection</div>}
    </div>
  );
}
```

- [ ] **Step 2: Write ReviewScreen.tsx**

```tsx
'use client';
import { useState } from 'react';
import VideoPlayer from './VideoPlayer';

interface DetectedObject {
  type: string;
  id: string;
  label: string;
  avatar_id?: string;
}

const AVATAR_COLORS: Record<string, string> = {
  player: '#e74c3c', ball: '#f1c40f', cone: '#e67e22',
};

export default function ReviewScreen({ drillId, videoSrc, initialObjects, onConfirm }: {
  drillId: string;
  videoSrc: string;
  initialObjects: DetectedObject[];
  onConfirm: (objects: DetectedObject[]) => void;
}) {
  const [objects, setObjects] = useState<DetectedObject[]>(initialObjects);
  const [addingType, setAddingType] = useState<'player' | 'cone' | null>(null);

  function handleRename(id: string, newLabel: string) {
    setObjects(prev => prev.map(o => o.id === id ? { ...o, label: newLabel } : o));
  }

  function handleAddBox(box: { x: number; y: number; w: number; h: number }) {
    if (!addingType) return;
    const newId = `${addingType}_${Date.now()}`;
    setObjects(prev => [...prev, {
      type: addingType, id: newId, label: `New ${addingType}`,
    }]);
    setAddingType(null);
  }

  async function handleConfirm() {
    await fetch(`/api/drills/${drillId}/objects`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ detected_objects: objects.map(o => ({
        type: o.type, id: o.id, label: o.label, frames: [],
      }))}),
    });
    await fetch(`/api/drills/${drillId}/generate`, { method: 'POST' });
    onConfirm(objects);
  }

  const bboxes = objects.map(o => ({
    x: 10, y: 10, w: 50, h: 80, label: o.label || o.id,
    color: AVATAR_COLORS[o.type] || '#888',
  }));

  return (
    <div className="grid grid-cols-3 gap-4">
      <div className="col-span-2">
        <VideoPlayer src={videoSrc} boundingBoxes={bboxes} onDrawBox={addingType ? handleAddBox : undefined} />
      </div>
      <div className="bg-gray-800 p-4 rounded-lg space-y-3">
        <h3 className="font-bold">Detected Objects</h3>

        {['player', 'ball', 'cone'].map(type => {
          const items = objects.filter(o => o.type === type);
          return (
            <div key={type}>
              <div className="text-sm font-semibold capitalize mb-1">{type}s ({items.length})</div>
              <div className="space-y-1">
                {items.map(o => (
                  <div key={o.id} className="flex items-center gap-2 text-sm">
                    <span style={{ width: 8, height: 8, borderRadius: '50%', background: AVATAR_COLORS[type] }} />
                    <input
                      value={o.label}
                      onChange={e => handleRename(o.id, e.target.value)}
                      className="bg-gray-700 px-2 py-0.5 rounded text-sm flex-1"
                    />
                  </div>
                ))}
                {type !== 'ball' && (
                  <button onClick={() => setAddingType(type)}
                    className={`text-xs px-2 py-1 rounded mt-1 ${addingType === type ? 'bg-green-600' : 'bg-gray-700 hover:bg-gray-600'}`}>
                    {addingType === type ? 'Click on video to draw box' : '+ Add'}
                  </button>
                )}
              </div>
            </div>
          );
        })}

        <button onClick={handleConfirm} className="w-full bg-green-600 hover:bg-green-700 py-2 rounded-lg mt-4">
          Looks good — Generate 3D
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/components/VideoPlayer.tsx frontend/components/ReviewScreen.tsx
git commit -m "feat: review screen with video overlay and manual box addition"
```

---

### Task 11: 3D Viewer with React Three Fiber

**Files:**
- Create: `frontend/components/Viewer3D.tsx`
- Create: `frontend/app/drill/[id]/page.tsx` (part 2: viewer mode)

- [ ] **Step 1: Write Viewer3D.tsx**

```tsx
'use client';
import { useRef, useState, useEffect } from 'react';
import { Canvas, useFrame, useLoader } from '@react-three/fiber';
import { OrbitControls, Text } from '@react-three/drei';
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';

function Field() {
  return (
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.01, 0]} receiveShadow>
      <planeGeometry args={[30, 20]} />
      <meshStandardMaterial color="#2d5a3f" />
    </mesh>
  );
}

interface AvatarProps {
  position: [number, number, number];
  color: string;
  label: string;
}

function Avatar({ position, color, label }: AvatarProps) {
  return (
    <group position={position}>
      {/* Body */}
      <mesh position={[0, 0.6, 0]} castShadow>
        <capsuleGeometry args={[0.15, 0.7, 4, 8]} />
        <meshStandardMaterial color={color} />
      </mesh>
      {/* Head */}
      <mesh position={[0, 1.2, 0]} castShadow>
        <sphereGeometry args={[0.12, 8, 8]} />
        <meshStandardMaterial color="#f5d0b0" />
      </mesh>
      {/* Label */}
      <Text position={[0, 1.5, 0]} fontSize={0.15} color="white" anchorX="center" anchorY="middle">
        {label}
      </Text>
    </group>
  );
}

function Ball({ position }: { position: [number, number, number] }) {
  return (
    <mesh position={position} castShadow>
      <sphereGeometry args={[0.1, 8, 8]} />
      <meshStandardMaterial color="white" />
    </mesh>
  );
}

function Cone({ position }: { position: [number, number, number] }) {
  return (
    <mesh position={position} castShadow>
      <coneGeometry args={[0.04, 0.12, 6]} />
      <meshStandardMaterial color="#f39c12" />
    </mesh>
  );
}

interface AnimData {
  type: string;
  id: string;
  label: string;
  frames: { frame: number; x: number; y: number; z: number }[];
}

function AnimatedObject({ data, color }: { data: AnimData; color: string }) {
  const groupRef = useRef<THREE.Group>(null);
  const [frameIndex, setFrameIndex] = useState(0);
  const [playing, setPlaying] = useState(true);
  const [speed, setSpeed] = useState(1);

  useEffect(() => {
    const handler = (e: CustomEvent) => {
      if (e.detail.type === 'play') setPlaying(true);
      else if (e.detail.type === 'pause') setPlaying(false);
      else if (e.detail.type === 'setTime') setFrameIndex(Math.round(e.detail.time));
      else if (e.detail.type === 'setSpeed') setSpeed(e.detail.speed);
    };
    window.addEventListener('drill-control' as any, handler);
    return () => window.removeEventListener('drill-control' as any, handler);
  }, []);

  useFrame((_, delta) => {
    if (!playing || !data.frames.length) return;
    setFrameIndex(prev => {
      const next = prev + delta * 30 * speed;
      if (next >= data.frames.length - 1) return 0;
      return next;
    });
  });

  const idx = Math.min(Math.floor(frameIndex), data.frames.length - 1);
  const pos = data.frames[idx];
  if (!pos) return null;

  if (data.type === 'ball') return <Ball position={[pos.x, 0.1, pos.z]} />;
  if (data.type === 'cone') return <Cone position={[pos.x, 0, pos.z]} />;
  return <Avatar position={[pos.x, 0, pos.z]} color={color} label={data.label} />;
}

const PLAYER_COLORS = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c'];

export default function Viewer3D({ sceneUrl }: { sceneUrl: string }) {
  const [playing, setPlaying] = useState(true);
  const [speed, setSpeed] = useState(1);
  const [animData, setAnimData] = useState<AnimData[]>([]);
  const [time, setTime] = useState(0);

  useEffect(() => {
    fetch(sceneUrl).then(r => r.json()).then(data => setAnimData(data.objects || [])).catch(() => {});
  }, [sceneUrl]);

  function dispatch(type: string, payload?: any) {
    window.dispatchEvent(new CustomEvent('drill-control', { detail: { type, ...payload } }));
  }

  const togglePlay = () => { setPlaying(p => !p); dispatch(playing ? 'pause' : 'play'); };
  const changeSpeed = (s: number) => { setSpeed(s); dispatch('setSpeed', { speed: s }); };
  const setView = (view: 'top' | 'side' | 'free') => {
    window.dispatchEvent(new CustomEvent('set-camera', { detail: { view } }));
  };

  return (
    <div className="w-full h-full flex flex-col">
      <div className="flex-1" style={{ height: 'calc(100vh - 80px)' }}>
        <Canvas camera={{ position: [15, 12, 15], fov: 45 }}>
          <ambientLight intensity={0.5} />
          <directionalLight position={[10, 15, 10]} intensity={0.8} castShadow />
          <Field />
          {animData.map((data, i) => (
            <AnimatedObject key={data.id} data={data} color={PLAYER_COLORS[i % PLAYER_COLORS.length]} />
          ))}
          <OrbitControls />
        </Canvas>
      </div>
      {/* Controls bar */}
      <div className="bg-gray-800 px-4 py-2 flex items-center gap-4">
        <button onClick={togglePlay} className="text-xl">{playing ? '⏸' : '▶'}</button>
        <button onClick={() => changeSpeed(0.25)} className={`px-2 py-1 rounded text-xs ${speed === 0.25 ? 'bg-green-600' : 'bg-gray-700'}`}>0.25x</button>
        <button onClick={() => changeSpeed(0.5)} className={`px-2 py-1 rounded text-xs ${speed === 0.5 ? 'bg-green-600' : 'bg-gray-700'}`}>0.5x</button>
        <button onClick={() => changeSpeed(1)} className={`px-2 py-1 rounded text-xs ${speed === 1 ? 'bg-green-600' : 'bg-gray-700'}`}>1x</button>
        <button onClick={() => changeSpeed(2)} className={`px-2 py-1 rounded text-xs ${speed === 2 ? 'bg-green-600' : 'bg-gray-700'}`}>2x</button>
        <div className="flex-1" />
        <button onClick={() => setView('top')} className="text-xs bg-gray-700 px-2 py-1 rounded">Top</button>
        <button onClick={() => setView('side')} className="text-xs bg-gray-700 px-2 py-1 rounded">Side</button>
        <button onClick={() => setView('free')} className="text-xs bg-gray-700 px-2 py-1 rounded">Free</button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Write app/drill/[id]/page.tsx**

```tsx
'use client';
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import ReviewScreen from '@/components/ReviewScreen';
import Viewer3D from '@/components/Viewer3D';
import ProcessingStatus from '@/components/ProcessingStatus';

interface Drill {
  id: string; name: string; status: string; video_key: string;
  scene_key: string; detected_objects: any[];
}

export default function DrillPage() {
  const { id } = useParams();
  const [drill, setDrill] = useState<Drill | null>(null);
  const [wsStatus, setWsStatus] = useState<string>('');
  const [wsProgress, setWsProgress] = useState(0);

  useEffect(() => {
    fetch(`/api/drills/${id}`).then(r => r.json()).then(setDrill);

    const ws = new WebSocket(`ws://localhost:8000/api/ws/progress/${id}`);
    ws.onmessage = (e) => {
      const data = JSON.parse(e.data);
      setWsStatus(data.status);
      setWsProgress(data.progress);
      if (data.status === 'review' || data.status === 'ready') {
        fetch(`/api/drills/${id}`).then(r => r.json()).then(setDrill);
      }
    };
    return () => ws.close();
  }, [id]);

  if (!drill) return <div className="p-6">Loading...</div>;

  if (drill.status === 'processing') {
    return <ProcessingStatus progress={wsProgress} message={wsStatus} />;
  }

  if (drill.status === 'review') {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-bold mb-4">{drill.name || 'Review Drill'}</h1>
        <ReviewScreen
          drillId={drill.id}
          videoSrc={`/api/video/${drill.video_key}`}
          initialObjects={drill.detected_objects || []}
          onConfirm={() => window.location.reload()}
        />
      </div>
    );
  }

  if (drill.status === 'ready') {
    return <Viewer3D sceneUrl={`/api/scene/${drill.scene_key}`} />;
  }

  if (drill.status === 'failed') {
    return <div className="p-6 text-red-400">Processing failed. Please try a different video.</div>;
  }

  return <div className="p-6">Status: {drill.status}</div>;
}
```

- [ ] **Step 3: Write ProcessingStatus component**

```tsx
'use client';
export default function ProcessingStatus({ progress, message }: { progress: number; message: string }) {
  const pct = Math.round(progress * 100);
  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-center space-y-4 w-80">
        <div className="text-3xl">⏳</div>
        <div className="text-lg font-semibold">Processing drill...</div>
        <div className="w-full bg-gray-700 rounded-full h-3">
          <div className="bg-green-600 h-3 rounded-full transition-all" style={{ width: `${pct}%` }} />
        </div>
        <div className="text-sm text-gray-400">{message || 'Starting...'}</div>
        <div className="text-xs text-gray-500">{pct}%</div>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/components/Viewer3D.tsx frontend/components/ProcessingStatus.tsx frontend/app/drill/
git commit -m "feat: 3D viewer, processing status, drill detail page"
```

---

### Task 12: Video and Scene Serving Endpoints

**Files:**
- Modify: `backend/router_drills.py` (add file serving endpoints)

- [ ] **Step 1: Add video and scene serving to router_drills.py**

```python
from fastapi.responses import FileResponse
from .config import VIDEOS_DIR, SCENES_DIR

@router.get("/video/{video_key}")
def serve_video(video_key: str):
    path = os.path.join(VIDEOS_DIR, video_key)
    if not os.path.exists(path):
        raise HTTPException(404, "Video not found")
    return FileResponse(path, media_type="video/mp4")

@router.get("/scene/{scene_key}")
def serve_scene(scene_key: str):
    path = os.path.join(SCENES_DIR, scene_key)
    if not os.path.exists(path):
        raise HTTPException(404, "Scene not found")
    return FileResponse(path, media_type="model/gltf-binary")
```

- [ ] **Step 2: Add os import at top of router_drills.py**

```python
import os
```

- [ ] **Step 3: Commit**

```bash
git add backend/router_drills.py
git commit -m "feat: video and scene file serving endpoints"
```

---

### Task 13: Docker Compose and README

**Files:**
- Create: `docker-compose.yml`
- Create: `README.md`

- [ ] **Step 1: Write docker-compose.yml**

```yaml
version: '3.8'
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
    command: uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
```

- [ ] **Step 2: Write README.md**

```markdown
# Football Drill Digitization MVP

Upload a football training video and get an interactive 3D scene.

## Quick Start

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

Open http://localhost:3000

## How it works

1. Upload a drill video (MP4/MOV)
2. AI detects players, ball, cones using YOLOv11
3. Review and correct detections
4. Generate 3D scene
5. Explore with orbit, play/pause, slow-motion
```

- [ ] **Step 3: Commit**

```bash
git add docker-compose.yml README.md
git commit -m "docs: Docker Compose and README"
```
