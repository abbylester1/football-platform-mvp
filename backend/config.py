import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORAGE_DIR = os.environ.get("STORAGE_DIR", os.path.join(BASE_DIR, "data"))
VIDEOS_DIR = os.environ.get("VIDEOS_DIR", os.path.join(STORAGE_DIR, "videos"))
SCENES_DIR = os.environ.get("SCENES_DIR", os.path.join(STORAGE_DIR, "scenes"))
AVATARS_DIR = os.environ.get("AVATARS_DIR", os.path.join(STORAGE_DIR, "avatars"))

DATABASE_URL = f"sqlite:///{os.path.join(STORAGE_DIR, 'football.db')}"

MAX_UPLOAD_SIZE = 2 * 1024 * 1024 * 1024  # 2GB
ALLOWED_EXTENSIONS = {".mp4", ".mov"}

YOLO_MODEL = os.environ.get("YOLO_MODEL", os.path.join(BASE_DIR, "yolo11n.pt"))
DETECTION_CONFIDENCE = 0.3
FRAME_INTERVAL = 5  # Process every Nth frame
