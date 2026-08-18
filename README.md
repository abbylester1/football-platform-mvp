<div align="center">

# ⚽ Football Drill Digitization Platform

**AI-powered football training analysis — upload a video, get a 3D replay with articulated player skeletons.**

[![Deployed](https://img.shields.io/badge/Deployed-Live-brightgreen)](https://football-drill-mvp.vercel.app)
[![Python](https://img.shields.io/badge/Python-3.9+-blue?logo=python)](https://python.org)
[![Next.js](https://img.shields.io/badge/Next.js-14-black?logo=next.js)](https://nextjs.org)
[![YOLOv11](https://img.shields.io/badge/YOLO-v11-red?logo=yolo)](https://github.com/ultralytics/ultralytics)
[![MediaPipe](https://img.shields.io/badge/MediaPipe-Pose-00C853)](https://google.github.io/mediapipe/)
[![Tests](https://img.shields.io/badge/Tests-62%20passing-brightgreen)](tests/)
[![License](https://img.shields.io/badge/License-MIT-blue)](LICENSE)

[**Live Demo**](https://football-drill-mvp.vercel.app) · [**API Docs**](https://football-mvp-backend-production.up.railway.app/docs) · [**Report Bug**](https://github.com/abbylester1/football-platform-mvp/issues)

</div>

---

## 🎯 About

Football Drill Digitization Platform transforms raw training footage into interactive 3D visualizations. Coaches upload a video of a training drill, and the AI pipeline automatically:

1. **Detects** every player, ball, and cone in each frame
2. **Tracks** objects across frames with persistent IDs
3. **Extracts skeletal poses** — 33 body landmarks per player via MediaPipe
4. **Projects** 2D detections into 3D world coordinates on the pitch
5. **Renders** an interactive 3D scene with articulated stick-figure skeletons

The result: coaches can replay any drill in 3D, scrub through time, change camera angles, and analyze player movement with realistic body animation — not just sliding dots.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🎬 **Video Upload** | Drag-and-drop MP4/MOV files up to 2GB with chunked upload |
| 🤖 **AI Detection** | YOLOv11 detects players, ball, and cones in every frame |
| 🦴 **Pose Estimation** | MediaPipe extracts 33 skeletal landmarks per player |
| 🎯 **Object Tracking** | IoU-based tracking with persistent player IDs across frames |
| 📐 **3D Projection** | Homography-based 2D→3D mapping using calibration cones |
| 📈 **Trajectory Smoothing** | Savitzky-Golay filter removes jitter from paths and poses |
| 🎮 **Interactive 3D Viewer** | Orbit, zoom, play/pause, slow-mo, camera presets |
| 🦴 **Articulated Skeletons** | 12-bone stick figures with joint spheres, not capsule avatars |
| 📦 **GLB Export** | Download 3D scenes as standard GLB files for use in Blender/Unity |
| 🔄 **Fallback Rendering** | Graceful degradation to capsule avatars when pose detection fails |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Vercel)                        │
│   Next.js 14 · React Three Fiber · Tailwind CSS · Three.js     │
│                                                                 │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│   │ Upload   │  │ Processing│  │ 3D Viewer│  │ Skeleton     │  │
│   │ Page     │→ │ Animation │→ │          │→ │ Renderer     │  │
│   └──────────┘  └──────────┘  └──────────┘  └──────────────┘  │
└─────────────────────────────┬───────────────────────────────────┘
                              │ /api/* (proxy)
┌─────────────────────────────▼───────────────────────────────────┐
│                       BACKEND (Railway)                         │
│   FastAPI · OpenCV · YOLO · MediaPipe · SciPy · trimesh        │
│                                                                 │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│   │ Video    │  │Detection │  │ Tracking │  │   Pose       │  │
│   │ Upload   │→ │ YOLOv11  │→ │ IoU/     │→ │  MediaPipe   │  │
│   │          │  │ + Motion │  │ Hungarian│  │  33 landmarks │  │
│   └──────────┘  └──────────┘  └──────────┘  └──────┬───────┘  │
│                                                      │          │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────▼───────┐  │
│   │ GLB      │← │Smoothing │← │Projection│← │  Keypoint    │  │
│   │ Export   │  │ Savitzky │  │Homography│  │  3D Project  │  │
│   └──────────┘  └──────────┘  └──────────┘  └──────────────┘  │
│                                                                 │
│   ┌──────────────────────────────────────────────────────────┐  │
│   │  SQLite Database · SQLAlchemy · File Storage (/data)     │  │
│   └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Node.js 18+
- YOLOv11 ONNX model (included as `yolo11n.onnx`)

### Backend Setup

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

---

## 🧪 Testing

```bash
# Run all tests (62 tests)
cd tests
python -m pytest -v

# Run specific test suites
python -m pytest test_pose_estimation.py -v    # 17 pose tests
python -m pytest test_integration_pipeline.py -v # 34 integration tests
python -m pytest test_tracking.py -v             # Tracking tests
python -m pytest test_smoothing.py -v            # Smoothing tests
```

---

## 📁 Project Structure

```
football-platform-mvp/
├── backend/
│   ├── main.py              # FastAPI application entry
│   ├── detection.py         # YOLO + MotionDetector
│   ├── pose_estimation.py   # MediaPipe Pose wrapper
│   ├── tracking.py          # IoU tracker with Hungarian assignment
│   ├── projection.py        # 2D → 3D homography projection
│   ├── calibration.py       # Cone detection + homography estimation
│   ├── smoothing.py         # Savitzky-Golay trajectory + keypoint smoothing
│   ├── animation.py         # GLB scene generation with trimesh
│   ├── worker.py            # Full processing pipeline orchestrator
│   ├── models.py            # Pydantic data models (Keypoint, FramePosition, etc.)
│   ├── database.py          # SQLAlchemy + SQLite
│   ├── config.py            # Environment configuration
│   ├── router_uploads.py    # Upload endpoints
│   ├── router_drills.py     # Drill CRUD endpoints
│   ├── router_process.py    # Processing trigger + status
│   └── requirements.txt     # Python dependencies
├── frontend/
│   ├── app/
│   │   ├── page.tsx          # Home / upload page
│   │   ├── layout.tsx        # Root layout
│   │   └── drill/[id]/       # Drill viewer page
│   ├── components/
│   │   └── Viewer3D.tsx      # Three.js 3D viewer + Skeleton renderer
│   ├── next.config.js        # API proxy rewrites
│   └── package.json          # Node dependencies
├── tests/
│   ├── test_pose_estimation.py      # 17 tests for pose extraction
│   ├── test_integration_pipeline.py # 34 integration tests
│   ├── test_tracking.py             # Tracker tests
│   ├── test_smoothing.py            # Smoothing tests
│   ├── test_detection.py            # Detection tests
│   └── test_animation.py            # Animation tests
├── docs/
│   └── superpowers/specs/    # Design specs and plans
└── MEMORY.md                 # Deployment memory
```

---

## 🎬 How It Works

### Step 1: Upload
Upload a football training video (MP4/MOV, up to 2GB). The video is stored locally on Railway's persistent volume.

### Step 2: Process
The AI pipeline runs automatically:
- **YOLOv11** detects players, ball, and cones in sampled frames (every Nth frame)
- **MediaPipe Pose** extracts 33 skeletal landmarks from each player crop
- **IoU Tracking** assigns persistent IDs across frames
- **Homography Projection** maps 2D pixel coords to 3D pitch coordinates
- **Savitzky-Golay Smoothing** removes jitter from trajectories and keypoints

### Step 3: View
Explore the 3D scene in the interactive viewer:
- 🖱️ **Orbit** — drag to rotate the camera
- ⏯️ **Play/Pause** — control the drill replay
- 🐢 **Slow-mo** — 0.5x, 1x, 2x playback speed
- 📷 **Camera presets** — player view, top-down, default
- 🔍 **Zoom** — scroll to zoom in/out
- 🦴 **Skeleton rendering** — articulated stick figures with 12 bone connections

### Step 4: Export
Download the 3D scene as a GLB file for use in Blender, Unity, or any 3D tool.

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | Next.js 14, React Three Fiber, Three.js, Tailwind CSS |
| **Backend** | FastAPI, Python 3.9, SQLAlchemy, Pydantic |
| **AI/ML** | YOLOv11 (ONNX), MediaPipe Pose, OpenCV |
| **3D Export** | trimesh (GLB format) |
| **Smoothing** | SciPy (Savitzky-Golay filter) |
| **Database** | SQLite (Railway persistent volume) |
| **Frontend Host** | Vercel |
| **Backend Host** | Railway (Docker) |
| **Testing** | pytest (62 tests) |

---

## 📊 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/upload` | Upload a drill video |
| `GET` | `/api/drills` | List all drills |
| `GET` | `/api/drills/{id}` | Get drill details + detected objects |
| `POST` | `/api/process/{id}` | Start processing pipeline |
| `GET` | `/api/process/{id}/status` | Poll processing status |
| `GET` | `/api/health` | Health check |
| `GET` | `/api/debug` | Debug info |

---

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📝 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**Built with ❤️ for football coaches and analysts**

[⬆ Back to top](#-football-drill-digitization-platform)

</div>
