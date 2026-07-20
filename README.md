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
