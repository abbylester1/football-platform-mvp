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
