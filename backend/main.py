from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.database import init_db
from backend.router_uploads import router as upload_router
from backend.router_drills import router as drill_router
from backend.router_process import router as process_router

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

@app.get("/api/debug")
def debug():
    import sys, os, platform
    info = {
        "python": sys.version,
        "platform": platform.platform(),
        "cwd": os.getcwd(),
        "files": os.listdir("."),
        "backend_files": os.listdir("backend") if os.path.isdir("backend") else [],
    }
    for mod in ["cv2", "numpy", "onnxruntime", "scipy", "trimesh", "PIL"]:
        try:
            m = __import__(mod)
            info[mod] = getattr(m, "__version__", "ok")
        except Exception as e:
            info[mod] = f"missing: {e}"
    # Test ONNX model
    from backend.config import YOLO_MODEL
    info["model_exists"] = os.path.exists(YOLO_MODEL)
    info["model_path"] = YOLO_MODEL
    info["model_size"] = os.path.getsize(YOLO_MODEL) if os.path.exists(YOLO_MODEL) else 0
    return info
