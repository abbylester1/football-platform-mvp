---
title: "Pose Estimation Integration — Articulated Player Skeletons"
spec_issue_number: TBD
status: draft
created: 2026-08-18
priority: critical
effort: 4-5 days
epic: football-platform-mvp
---

# Pose Estimation Integration — Articulated Player Skeletons

## Context

The football drill digitization MVP currently renders players as static capsule avatars that slide around a 3D pitch. Coaches see *where* players moved but not *how* — no body orientation, no arm movement, no running gait. This makes the 3D viewer a positional replay tool, not an analysis tool. Pose estimation transforms it into something a coach would actually use.

The pipeline already detects and tracks players frame-by-frame. The missing piece is extracting skeletal keypoints from each player crop and rendering them as an articulated stick figure in the 3D viewer.

## Current State

**Pipeline flow** (verified in `backend/worker.py:37-99`):
```
YOLO detect → IoU track → project_to_3d(center_point) → smooth → {type, id, frames: [{frame, x, y, z}]}
```

**Detection output** (`backend/detection.py:136-160` `detect_objects()`):
- Returns `[{type: "player"|"ball"|"cone", bbox: [x1,y1,x2,y2], confidence}]`
- No skeletal data — bounding box only

**Frame data model** (`backend/models.py:14` `FramePosition`):
```python
class FramePosition(BaseModel):
    frame: int
    x: float
    y: float
    w: float = 0.0
    h: float = 0.0
```
No keypoints field.

**3D rendering** (`frontend/components/Viewer3D.tsx:43-57` `Avatar` component):
- Player → capsule body (radius 0.15, height 0.4) + sphere head (radius 0.1) + text label
- Position set via `groupRef.position` only — no limb animation

**Animation system** (`frontend/components/Viewer3D.tsx:88-120` `AnimatedObject`):
- Interpolates between keyframes for position
- No rotation or skeletal interpolation

**GLB export** (`backend/animation.py:57-70` `_create_avatar_mesh`):
- Procedural cylinder + sphere mesh per player
- No skeleton geometry

**Smoothing** (`backend/smoothing.py`):
- Savitzky-Golay filter on `(x, y)` trajectories
- Can be extended to keypoints

**Tests** (`tests/test_detection.py`, `tests/test_tracking.py`):
- ~40 tests exist for detection, tracking, smoothing, animation, integration
- No pose-specific tests

## Proposed Change

Add pose estimation to the backend pipeline and render articulated stick-figure skeletons in the 3D viewer. When pose detection fails (player too small/occluded), fall back to the current capsule avatar.

### Architecture

```
                         CURRENT                          PROPOSED
                    ┌──────────────┐                ┌──────────────────┐
YOLO detect ──────> │ bounding box │ ──────────────> │ bounding box     │
                    └──────────────┘                │ + MediaPipe Pose │
                                                    │ → 33 keypoints   │
                                                    └──────────────────┘
                                                              │
                                                    ┌─────────▼─────────┐
                                                    │ IoU track         │
                                                    │ (unchanged)       │
                                                    └─────────┬─────────┘
                                                              │
                                                    ┌─────────▼─────────┐
                                                    │ Project to 3D     │
                                                    │ center + keypoints│
                                                    └─────────┬─────────┘
                                                              │
                                                    ┌─────────▼─────────┐
                                                    │ Smooth trajectories│
                                                    │ + keypoints       │
                                                    └─────────┬─────────┘
                                                              │
                                                    ┌─────────▼─────────┐
                                                    │ Render: skeleton  │
                                                    │ or fallback capsule│
                                                    └───────────────────┘
```

### Implementation Details

#### 1. Backend: Pose Extraction Module

**New file:** `backend/pose_estimation.py`

```python
# Core function signature
def extract_pose_keypoints(
    frame: np.ndarray,
    bbox: tuple[int, int, int, int],  # (x1, y1, x2, y2)
    confidence_threshold: float = 0.5
) -> list[dict] | None:
    """
    Run MediaPipe Pose on a cropped player region.
    
    Returns 33 landmarks as [{"x": 0.0-1.0, "y": 0.0-1.0, "z": float, "visibility": 0.0-1.0}]
    or None if pose detection fails.
    
    Coordinates are normalized relative to the crop bounding box.
    """
```

**MediaPipe integration:**
```python
import mediapipe as mp

mp_pose = mp.solutions.pose
pose = mp_pose.Pose(
    static_image_mode=False,
    model_complexity=1,  # 0=lite, 1=full, 2=heavy — balance speed/accuracy
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)
```

**Key decisions:**
- Run MediaPipe on the **cropped player region** (bbox from YOLO), not the full frame — faster, more accurate
- Normalize keypoints to 0-1 range relative to the crop — resolution-independent
- Store all 33 landmarks but the stick figure only uses ~17 core body joints (same as COCO keypoint format used by Three.js loaders)

**Performance estimate:** ~15ms per crop on CPU. For 150 frames × 6 players = 900 crops ≈ 13.5s added processing. Acceptable for Railway.

#### 2. Backend: Extend Data Model

**File:** `backend/models.py`

```python
class Keypoint(BaseModel):
    x: float  # Normalized 0-1 relative to player bbox
    y: float  # Normalized 0-1 relative to player bbox
    z: float  # Depth estimate from MediaPipe
    visibility: float  # 0-1, confidence of this landmark

class FramePosition(BaseModel):
    frame: int
    x: float
    y: float
    w: float = 0.0
    h: float = 0.0
    keypoints: list[Keypoint] | None = None  # NEW: 33 landmarks or None
```

**Backward compatibility:** `keypoints` defaults to `None`, so existing drill data renders with capsules. No migration needed.

#### 3. Backend: Integrate into Detection Pipeline

**File:** `backend/detection.py` — extend `detect_objects()`:

```python
def detect_objects(frame: np.ndarray, frame_num: int = 0) -> list[dict]:
    # ... existing YOLO detection ...
    
    for detection in yolo_results:
        obj = {
            "type": "player",
            "bbox": [x1, y1, x2, y2],
            "confidence": conf,
        }
        
        # NEW: Extract pose keypoints for players
        if obj["type"] == "player":
            keypoints = extract_pose_keypoints(frame, (x1, y1, x2, y2))
            obj["keypoints"] = keypoints  # None if detection fails
        
        detected_objects_list.append(obj)
```

**File:** `backend/worker.py` — pass keypoints through pipeline:

```python
# In process_drill_sync(), after grouping by track_id:
for frame_data in track_frames:
    projected = project_to_3d(frame_data["x"], frame_data["y"])
    
    frame_result = {
        "frame": frame_data["frame"],
        "x": projected["x"],
        "y": projected["y"],
        "z": projected.get("z", 0.0),
        "w": frame_data.get("w", 0.0),
        "h": frame_data.get("h", 0.0),
    }
    
    # NEW: Include keypoints if available
    if frame_data.get("keypoints"):
        frame_result["keypoints"] = frame_data["keypoints"]
    
    frames.append(frame_result)
```

**File:** `backend/worker.py` — project keypoints to 3D:

```python
def project_keypoints_to_3d(keypoints, bbox, homography):
    """Transform normalized crop keypoints to 3D world coordinates."""
    # Convert normalized crop coords to full-frame pixel coords
    # Then apply homography to get world coords
    world_keypoints = []
    for kp in keypoints:
        # Scale to frame pixel coords
        px = bbox[0] + kp["x"] * (bbox[2] - bbox[0])
        py = bbox[1] + kp["y"] * (bbox[3] - bbox[1])
        # Apply homography
        world = apply_homography(homography, px, py)
        world_keypoints.append({
            "x": world["x"],
            "y": world["y"],
            "z": kp["z"],  # Relative depth from MediaPipe
            "visibility": kp["visibility"]
        })
    return world_keypoints
```

#### 4. Backend: Smooth Keypoints

**File:** `backend/smoothing.py` — extend to smooth keypoints per track:

```python
def smooth_keypoints(tracks: list[dict]) -> list[dict]:
    """
    Apply Savitzky-Golay filter to keypoint trajectories per track.
    Each of the 33 keypoints gets smoothed independently across frames.
    """
    for track in tracks:
        if not track.get("frames") or not any(f.get("keypoints") for f in track["frames"]):
            continue
        
        # Group keypoints by landmark index across frames
        for landmark_idx in range(33):
            x_values = []
            y_values = []
            valid_frames = []
            
            for frame in track["frames"]:
                kps = frame.get("keypoints")
                if kps and len(kps) > landmark_idx and kps[landmark_idx]["visibility"] > 0.5:
                    x_values.append(kps[landmark_idx]["x"])
                    y_values.append(kps[landmark_idx]["y"])
                    valid_frames.append(frame)
            
            if len(x_values) >= window_size:
                smoothed_x = savgol_filter(x_values, window_size, polyorder)
                smoothed_y = savgol_filter(y_values, window_size, polyorder)
                for i, frame in enumerate(valid_frames):
                    frame["keypoints"][landmark_idx]["x"] = smoothed_x[i]
                    frame["keypoints"][landmark_idx]["y"] = smoothed_y[i]
    
    return tracks
```

#### 5. Frontend: Articulated Skeleton Component

**File:** `frontend/components/Viewer3D.tsx` — replace `Avatar` component:

```tsx
// MediaPipe Pose landmark indices (COCO format subset for stick figure)
const SKELETON_CONNECTIONS: [number, number][] = [
  [11, 12],  // shoulders
  [11, 13],  // left upper arm
  [13, 15],  // left forearm
  [12, 14],  // right upper arm
  [14, 16],  // right forearm
  [11, 23],  // left torso
  [12, 24],  // right torso
  [23, 24],  // hips
  [23, 25],  // left upper leg
  [25, 27],  // left lower leg
  [24, 26],  // right upper leg
  [26, 28],  // right lower leg
];

const JOINT_INDICES = [0, 11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28];

function Skeleton({ keypoints, scale = 1 }: { keypoints: Keypoint3D[]; scale?: number }) {
  const joints = JOINT_INDICES.map(i => keypoints[i]).filter(Boolean);
  const connections = SKELETON_CONNECTIONS.filter(
    ([a, b]) => keypoints[a]?.visibility > 0.5 && keypoints[b]?.visibility > 0.5
  );
  
  return (
    <group>
      {/* Joint spheres */}
      {joints.map((kp, i) => (
        <mesh key={i} position={[kp.x * scale, kp.y * scale, kp.z * scale]}>
          <sphereGeometry args={[0.03, 8, 8]} />
          <meshStandardMaterial color="#4FC3F7" />
        </mesh>
      ))}
      {/* Bone cylinders */}
      {connections.map(([a, b], i) => {
        const start = new Vector3(keypoints[a].x * scale, keypoints[a].y * scale, keypoints[a].z * scale);
        const end = new Vector3(keypoints[b].x * scale, keypoints[b].y * scale, keypoints[b].z * scale);
        return <BoneLine key={i} start={start} end={end} />;
      })}
      {/* Head (approximate from nose landmark 0) */}
      {keypoints[0]?.visibility > 0.5 && (
        <mesh position={[keypoints[0].x * scale, keypoints[0].y * scale + 0.05, keypoints[0].z * scale]}>
          <sphereGeometry args={[0.06, 8, 8]} />
          <meshStandardMaterial color="#4FC3F7" />
        </mesh>
      )}
    </group>
  );
}

function BoneLine({ start, end }: { start: Vector3; end: Vector3 }) {
  const ref = useRef<THREE.CylinderGeometry>(null);
  const midpoint = start.clone().add(end).multiplyScalar(0.5);
  const length = start.distanceTo(end);
  const direction = end.clone().sub(start).normalize();
  
  return (
    <mesh position={midpoint} quaternion={new Quaternion().setFromUnitVectors(
      new Vector3(0, 1, 0), direction
    )}>
      <cylinderGeometry args={[0.015, 0.015, length, 6]} />
      <meshStandardMaterial color="#4FC3F7" />
    </mesh>
  );
}
```

#### 6. Frontend: Update AnimatedObject

**File:** `frontend/components/Viewer3D.tsx` — modify `AnimatedObject`:

```tsx
function AnimatedObject({ track, playbackTime, playing }: Props) {
  const groupRef = useRef<Group>(null);
  const [currentFrame, setCurrentFrame] = useState<FrameData | null>(null);
  const [prevFrame, setPrevFrame] = useState<FrameData | null>(null);
  
  // Existing interpolation logic (unchanged)
  // ...
  
  const hasKeypoints = currentFrame?.keypoints && currentFrame.keypoints.length > 0;
  
  return (
    <group ref={groupRef}>
      {track.type === "player" && (
        hasKeypoints ? (
          <Skeleton keypoints={currentFrame.keypoints} scale={1} />
        ) : (
          // Fallback: original capsule avatar
          <>
            <mesh position={[0, 0.2, 0]}>
              <capsuleGeometry args={[0.15, 0.4, 4, 8]} />
              <meshStandardMaterial color={getColor(track.id)} />
            </mesh>
            <mesh position={[0, 0.5, 0]}>
              <sphereGeometry args={[0.1, 8, 8]} />
              <meshStandardMaterial color={getColor(track.id)} />
            </mesh>
          </>
        )
      )}
      {track.type === "ball" && <Ball />}
      {track.type === "cone" && <Cone />}
      <Text position={[0, 0.7, 0]} fontSize={0.08} color="white" anchorX="center">
        {track.id}
      </Text>
    </group>
  );
}
```

#### 7. GLB Export Update

**File:** `backend/animation.py` — update `_create_avatar_mesh`:

When keypoints are available, export skeleton as line segments + joint spheres instead of capsule mesh. Use `trimesh` Path objects for bones and spheres for joints.

### File Reference

| File | Change |
|------|--------|
| `backend/pose_estimation.py` | **NEW** — MediaPipe Pose wrapper |
| `backend/detection.py:136` | Add pose extraction call in `detect_objects()` |
| `backend/models.py:14` | Add `Keypoint` model, extend `FramePosition` with `keypoints` field |
| `backend/worker.py:56-99` | Pass keypoints through pipeline, add `project_keypoints_to_3d()` |
| `backend/smoothing.py` | Add `smooth_keypoints()` function |
| `backend/animation.py:57-70` | Update `_create_avatar_mesh()` for skeleton export |
| `backend/requirements.txt` | Add `mediapipe>=0.10.9` |
| `frontend/components/Viewer3D.tsx:43-57` | Replace `Avatar` with `Skeleton` component + fallback |
| `frontend/components/Viewer3D.tsx:88-120` | Update `AnimatedObject` to render skeleton or capsule |
| `tests/test_pose_estimation.py` | **NEW** — Unit tests for pose extraction |
| `tests/test_integration_pipeline.py` | Add integration test for pose-inclusive pipeline |

## Acceptance Criteria

1. ✅ `backend/pose_estimation.py` extracts 33 MediaPipe Pose landmarks from a player crop, returning normalized coordinates with visibility scores
2. ✅ `detect_objects()` returns keypoints alongside bounding boxes for each player detection
3. ✅ `FramePosition` model includes optional `keypoints: list[Keypoint] | None` field
4. ✅ `worker.py` passes keypoints through tracking, projection, and smoothing without data loss
5. ✅ `smooth_keypoints()` applies Savitzky-Golay filtering to keypoint trajectories independently per landmark
6. ✅ Frontend renders articulated stick-figure skeleton when keypoints are present, using 12 bone connections and joint spheres
7. ✅ Frontend falls back to capsule avatar when keypoints are `None` (MediaPipe failed or old drill data)
8. ✅ Existing drill data without keypoints renders correctly with capsule avatars (backward compatible)
9. ✅ GLB export includes skeleton geometry when keypoints are available
10. ✅ Processing time for a 30-second video at 5fps with 6 players does not exceed 60 seconds total (detection + pose + projection + smoothing)
11. ✅ All existing tests pass unchanged
12. ✅ New unit tests cover: pose extraction success, pose extraction failure/fallback, keypoint smoothing, skeleton rendering with/without data

## Testing Plan

| Layer | What | Count |
|-------|------|-------|
| Unit | `extract_pose_keypoints()` — valid crop, empty crop, low-res crop, occluded player | +4 |
| Unit | `smooth_keypoints()` — short track, long track, sparse keypoints, all invisible | +3 |
| Unit | `project_keypoints_to_3d()` — homography transform, identity transform | +2 |
| Unit | `Skeleton` component — renders with keypoints, renders nothing without | +2 |
| Integration | Full pipeline: upload video → pose extraction → smooth → GLB export includes skeleton | +1 |
| Integration | Backward compat: existing drill without keypoints renders capsule avatars | +1 |
| E2E | Upload drill video → 3D viewer shows stick-figure players with limb movement | +1 |

## Effort Estimate

| Component | Time |
|-----------|------|
| `pose_estimation.py` module | 3h |
| Data model + detection integration | 2h |
| Worker pipeline integration (projection + smoothing) | 4h |
| Frontend skeleton component + AnimatedObject update | 6h |
| GLB export skeleton geometry | 3h |
| Tests (unit + integration) | 4h |
| Debugging, edge cases, performance tuning | 4h |
| **Total** | **~26h (3-4 days)** |

## Rollback Plan

- Revert all changes — no data migration, no schema changes to existing data
- `keypoints: None` default means old drills are unaffected
- MediaPipe is an additive dependency — removing it restores previous behavior

## Out of Scope

- Multi-camera 3D pose reconstruction (separate epic)
- Pose-based analytics (speed from keypoints, acceleration, movement patterns)
- Real-time pose estimation (batch processing only)
- Hand/finger landmark detail (only body pose — 33 landmarks)
- Ball or cone pose estimation
- Replacing YOLO detection with pose-based detection
- Player re-identification across poses
- Face detection or identity recognition

## Dependencies

- `mediapipe>=0.10.9` — Google MediaPipe Pose solution
- Existing: `ultralytics` (YOLO), `opencv-python`, `numpy`, `scipy`
- Frontend: `@react-three/fiber`, `three` (already in project)

## Related

- Original design spec: `docs/superpowers/specs/2026-07-19-football-drill-digitization-design.md`
- MVP plan: `docs/superpowers/plans/2026-07-19-football-drill-mvp-plan.md`
