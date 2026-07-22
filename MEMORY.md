# Deployment Memory

## Frontend (Vercel)

| Detail | Value |
|--------|-------|
| Project name | `frontend` |
| Deploy from | `frontend/` directory ONLY |
| Production URL | `https://football-drill-mvp.vercel.app` |
| Build command | `npm install && npm run build` (defined in Vercel dashboard/Docker) |
| Env var | `NEXT_PUBLIC_RENDER_URL=https://backend-production-77b2d.up.railway.app` |
| Rewrites | `frontend/next.config.js` rewrites `/api/*` to Railway backend |
| Deploy command | `cd frontend && vercel deploy --prod` |
| **NEVER** | Deploy from root (`vercel.json` was removed — no package.json there) |

- The `football-drill-mvp.vercel.app` domain is an alias on the `frontend` project
- The old `football-drill-mvp` Vercel project (root-level) was **deleted** — do NOT recreate it
- Run `vercel deploy --prod` from `frontend/` only

## Backend (Railway)

| Detail | Value |
|--------|-------|
| Project | `football-mvp-backend` |
| Service | `football-mvp-backend` |
| Production URL | `https://backend-production-77b2d.up.railway.app` |
| Deploy from | `backend/` subdirectory |
| Config file | `railway.json` at root specifies Dockerfile path |
| Build driver | Docker (via `railway.json`) |
| Dockerfile | `backend/Dockerfile` |
| Deploy command | `cd backend && railway up` |
| **NEVER** | Run `railway up` from root — it creates a duplicate project |

- The `backend` project (created accidentally) was **deleted**
- Only `football-mvp-backend` project should exist

## API Architecture

- Frontend calls `/api/*` — Next.js rewrites proxy to Railway backend
- `backend/main.py` has routers: upload, drills, process
- Key endpoints:
  - `POST /api/upload` — upload video
  - `POST /api/process/{id}` — start processing
  - `GET /api/process/{id}/status` — poll processing status
  - `GET /api/drills` — list drills
  - `GET /api/drills/{id}` — get drill (includes detected_objects, scene_key)
  - `GET /api/health` — health check
  - `GET /api/debug` — debug info

## Detection Pipeline

- Primary: YOLO11n ONNX (detects class 0=person, class 32=sports_ball)
- Fallback: `MotionDetector` (background subtraction MOG2) — kicks in when YOLO finds nothing
- Motion detector classifies blobs by color: white+small=ball, orange=cone, rest=player
- YOLO fails on aerial/overhead footage — players are too small (<40px in 800x450)
- Detection confidence threshold: 0.3 (`DETECTION_CONFIDENCE` in config.py)
- Frame interval: 5 (`FRAME_INTERVAL` in config.py)

## Git

| Detail | Value |
|--------|-------|
| Origin | `https://github.com/abbylester1/football-platform-mvp.git` |
| Branch | `main` |
| ONNX models | `yolo11n.onnx` tracked, `yolo11s.pt` and `yolo11m.pt` are untracked locals |

## Tests

- Run: `python3 -m pytest tests/ -v`
- 40 tests covering detection, tracking, projection, calibration, smoothing, animation, models, config
