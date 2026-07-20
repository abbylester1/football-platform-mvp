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
    model_config = {"from_attributes": True}

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
