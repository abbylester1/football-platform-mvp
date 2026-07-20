# Design Spec: AI Football Drill Digitization Platform (MVP)

**Date:** 2026-07-19
**Status:** Approved Design
**Target:** Sprint prototype in 2-3 weeks

---

## 1. Product Vision

Convert mobile phone recordings of football training drills into interactive 3D scenes. Coaches upload a 2D video; the system detects players, ball, and cones, tracks their movement, and renders them as 3D avatars on a virtual pitch. The result is a rotatable, pausable, slow-motion 3D replay that reveals spatial relationships a flat video cannot.

## 2. Target User

Individual football coaches recording drills on their phone. Low-to-medium technical proficiency. Human-in-the-loop review/correction is expected.

## 3. Competitive Landscape

| Product | Category | 3D from video? | Football-specific? | Gap |
|---|---|---|---|---|
| Once Sport Analyser | Video analysis + 3D telestration | No (2D overlays) | Yes | Annotations on video, not 3D scene reconstruction |
| DeepMotion | General AI mocap | Yes | No | General animation tool, no drill abstraction |
| FC Tactix | Tactics board | No (drawing tool) | Yes | Manual drawing, no video input |
| Spiideo / Hudl / Veo | Match recording/analysis | No | Yes | Passive video libraries, no 3D conversion |

No existing product provides end-to-end football drill video → interactive 3D scene conversion.

## 4. MVP Scope

### Included
- Single fixed-camera video upload (MP4/MOV, ≤2GB)
- Up to ~6 players, 1 ball, cones
- YOLO detection + simple tracking (no pose estimation)
- 3D scene with low-poly avatars (predefined library of ~10-20 variants)
- Interactive viewer: play, pause, rewind, fast-forward, slow-mo, orbit, zoom, preset views
- Human-in-the-loop review screen (confirm/rename objects, draw missing bounding boxes)
- Timescale: 2-3 weeks to working prototype

### Excluded (Phase 2+)
- Pose estimation / limb tracking
- Multi-camera reconstruction
- Tactical analytics
- AI player scoring
- VR mode

## 5. Architecture

```
┌─────────────┐     ┌──────────┐     ┌──────────┐     ┌────────────┐
│ Next.js     │◄───►│ FastAPI  │◄───►│ Redis    │◄───►│ Python     │
│ (Frontend + │     │ (API)    │     │ Queue    │     │ Worker     │
│  3D Viewer) │     │          │     │          │     │ (GPU)      │
└─────────────┘     └────┬─────┘     └──────────┘     └──────┬─────┘
                         │                                    │
                         ▼                                    ▼
                    ┌──────────┐                     ┌──────────────┐
                    │  S3 /    │                     │ YOLOv11      │
                    │  Local   │                     │ ByteTrack    │
                    │  Storage │                     │ Kalman Filter│
                    └──────────┘                     └──────────────┘
```

### Components

| Component | Tech | Role |
|---|---|---|
| Portal | Next.js + Tailwind | Upload UI, drill library, 3D viewer page |
| API Server | FastAPI (Python) | Upload handling, job management, WebSocket progress |
| Worker | Python | GPU-accelerated AI pipeline (YOLO → track → project → animate) |
| Storage | S3-compatible (or local fs for prototype) | Video files, GLB scenes, detection data |
| Queue | Redis (or in-process for prototype) | Job coordination |
| DB | SQLite (prototype) → PostgreSQL (prod) | Drill metadata, detection config |

### Data Model: Drill

```
Drill {
  id: UUID
  name: string
  category: string        // "passing", "movement", "possession"
  age_group: string       // "U10", "U12", "U14", "adult"
  difficulty: string      // "beginner", "intermediate", "advanced"
  description: text
  video_key: string       // S3 key or file path
  status: enum            // uploading | processing | review | ready | failed
  detected_objects: [
    { type: "player", id: "P1", label: "John", avatar_id: "avatar_01", frames: [{x,y,w,h}...] },
    { type: "player", id: "P2", label: "Mike", avatar_id: "avatar_02", frames: [{x,y,w,h}...] },
    { type: "ball", id: "B1", frames: [{x,y}...] },
    { type: "cone", id: "C1", frames: [{x,y}...] },
  ]
  scene_key: string       // S3 key to GLB scene
  created_at: timestamp
  updated_at: timestamp
}
```

## 6. User Flow

### Screen 1: Upload
- Drag-and-drop video uploader (MP4/MOV, max 2GB)
- Form: drill name, category, age group, difficulty, description
- Auto-thumbnail extraction

### Screen 2: Processing
- Real-time progress via WebSocket
- Stages displayed: Upload → Detecting → Tracking → Building scene
- Estimated ~2-5 minutes

### Screen 3: Review & Correct
- Video player with detection overlay (bounding boxes)
- List of detected players (renameable), ball, cones
- "+ Add" button to draw missing bounding boxes manually
- Drag existing boxes to adjust
- "Looks good — Generate 3D" button triggers animation pipeline
- "Re-process" button re-runs AI with corrections as hints

### Screen 4: 3D Viewer
- Three.js / React Three Fiber scene
- Green pitch with markings
- Pre-rigged low-poly avatar library (~10-20 variants)
  - Multiple body types (tall, stocky, average)
  - Team color kits (red, blue, white, etc.)
  - Age-appropriate scaling
- Animation: walk/run cycle driven by tracked 2D positions projected onto 3D plane
- Controls: play/pause, rewind, fast-forward, slow-motion (0.25x, 0.5x)
- Camera: orbit (click-drag), zoom (scroll), preset views (top, side, free)
- Player trails: faint path lines showing movement over time
- Cone markers on field
- Timeline scrubber with time display
- Player legend (click to highlight path)

## 7. AI Pipeline

```
Video Frames (every N frames, e.g., 5-10 fps)
    │
    ▼
YOLOv11 Detection ───► Players, Ball, Cones (bounding boxes + class)
    │
    ▼
ByteTrack / Kalman Filter ───► Consistent object IDs across frames
    │
    ▼
Camera Calibration (homography) ───► Estimate field plane from cone positions
    │
    ▼
2D→3D Projection ───► (x, y, z) positions on virtual field plane
    │
    ▼
Trajectory Smoothing ───► Apply Savitzky-Golay filter to remove jitter
    │
    ▼
Animation Generation ───► Map positions to avatar walk/run cycles, interpolate
    │
    ▼
GLB Export ───► Pack scene (field + avatars + cones + ball) into single GLB
```

### Key Design Decisions

1. **No pose estimation in MVP.** Avatars use pre-defined walk/run animations blended with movement direction and speed. Limb-level accuracy is Phase 2.
2. **Homography from cones.** Cones placed at known drill positions allow camera calibration. If no cones, fall back to an assumed ground plane.
3. **ID preservation via tracking.** ByteTrack handles re-identification if players cross paths (limited reliability with few players).
4. **Trajectory smoothing.** Raw detection jitter smoothed with Savitzky-Golay filter. Ball trajectory gets stronger smoothing.

## 8. Avatar Library

Pre-rigged Mixamo-compatible avatars shipped with the app:

| Variant | Body Type | Available Colors |
|---|---|---|
| Standard Adult | Average build | Red, Blue, White, Black, Yellow, Green |
| Lean Athlete | Tall, slim | Red, Blue, White, Black |
| Stocky Player | Wider build | Red, Blue, White |
| Youth Player | Smaller scale | Red, Blue, Green, Yellow |
| Generic | Neutral | Orange (default) |

Total: ~18 avatar variants. All use the same Mixamo skeleton so animation data is universal.

Coaches can assign avatars during review or change them later from the viewer sidebar.

## 9. Technology Stack

| Layer | Technology |
|---|---|
| Frontend framework | Next.js 14+ |
| 3D rendering | React Three Fiber + Three.js + @react-three/drei |
| Styling | Tailwind CSS |
| API | FastAPI (Python) |
| Detection | YOLOv11 (Ultralytics) |
| Tracking | ByteTrack (or Kalman filter for simplicity) |
| Calibration | OpenCV (find homography from field landmarks / cones) |
| Animation | Pre-baked Mixamo animations, blended by speed/direction |
| 3D format | GLB/GLTF (exported via trimesh + custom blenderless pipeline) |
| Queue | Redis (prototype: in-process threading) |
| Database | SQLite → PostgreSQL |
| Storage | Local filesystem → S3-compatible |
| Container | Docker Compose (API + worker + Redis) |

## 10. Infrastructure (MVP)

For the 2-3 week sprint, everything runs on a single machine:
- Python FastAPI server + worker (GPU if available, CPU fallback)
- Next.js dev server
- SQLite database
- Local file storage

Production would require:
- GPU-equipped worker nodes
- S3 for video/asset storage
- Proper job queue (Redis + Celery or similar)
- PostgreSQL

## 11. Non-Functional Requirements

| Metric | Target |
|---|---|
| Processing time | <5 min for 2-min video |
| Viewer FPS | 60 FPS (target), 30 FPS (acceptable) |
| Max upload | 2GB |
| Supported formats | MP4, MOV |
| Player tracking accuracy | >95% (with ≤6 players) |
| Ball tracking accuracy | >90% |
| Animation smoothness | No visible jitter post-smoothing |

## 12. Edge Cases

| Case | Handling |
|---|---|
| Video has more than 6 players | Process what's detected, warn coach accuracy may be lower |
| Camera moves during recording | MVP requires fixed camera. Warn if frame-to-frame motion exceeds threshold |
| Player occlusion (players cross) | Tracking handles brief occlusions; extended occlusion breaks ID |
| Ball not visible in some frames | Interpolate ball position between known frames |
| No cones visible | Fall back to assumed ground plane, use player positions for scale estimation |
| Poor lighting | YOLO handles varied lighting; warn if confidence is low |
| Wrong sport uploaded | Detect based on field colors; warn if not a football/green-field video |
| Processing fails | Show error with "contact support" / "try different video" options |

## 13. Success Metrics

- Processing success rate >95%
- Review screen approval rate >80% (coach clicks "Looks good" without re-processing)
- Viewer interactions: avg session time >2 min (coach actually watches the 3D version)
- Tracking accuracy validated against hand-labeled test set
