"""
Video Analysis Module — understands the video before processing.

Samples ~20 frames evenly, runs detection + cone detection on each,
then determines:
  - Camera angle (overhead / sideline / broadcast)
  - Drill area polygon (from cone positions)
  - Expected participant count (from consistent detections)
  - Field dimensions estimate
  - Confidence score for each determination

This analysis guides the full pipeline: which detections to keep,
where the drill area is, what camera model to use.
"""

import cv2
import numpy as np
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class SceneAnalysis:
    """Result of pre-analyzing a video."""
    camera_angle: str = "unknown"       # "overhead", "sideline", "broadcast"
    camera_confidence: float = 0.0
    drill_polygon: Optional[np.ndarray] = None  # Convex polygon of drill area (screen coords)
    drill_area_bbox: Optional[tuple] = None     # Bounding box of drill area (x1,y1,x2,y2)
    cone_positions: list = field(default_factory=list)  # Consistent cone positions (screen coords)
    expected_players: int = 0            # Estimated number of drill participants
    player_confidence: float = 0.0
    total_detections: int = 0            # Total raw detections across sampled frames
    consistent_detections: int = 0       # Detections that appear in >30% of frames
    frame_width: int = 0
    frame_height: int = 0
    fps: float = 0.0
    total_frames: int = 0
    analysis_confidence: float = 0.0     # Overall confidence in the analysis


def analyze_video(video_path: str, sample_count: int = 20) -> SceneAnalysis:
    """
    Pre-analyze a video to understand its content before full processing.
    
    Returns a SceneAnalysis with camera angle, drill area, and participant estimate.
    """
    logger.info(f"[analysis] Starting video analysis: {video_path}")
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        logger.error(f"[analysis] Cannot open video: {video_path}")
        return SceneAnalysis()
    
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    # Sample frames evenly across the video
    sample_indices = np.linspace(0, total_frames - 1, min(sample_count, total_frames), dtype=int)
    
    all_detections_per_frame = []  # List of (frame_idx, detections)
    all_cones_per_frame = []       # List of (frame_idx, cone_bboxes)
    frame_aspects = []             # Frame aspect ratios
    
    from detection import detect_objects
    from calibration import detect_cones_in_frame
    
    for idx in sample_indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
        ret, frame = cap.read()
        if not ret:
            continue
        
        frame_aspects.append(frame_width / frame_height)
        
        # Run YOLO detection
        detections = detect_objects(frame)
        all_detections_per_frame.append((int(idx), detections))
        
        # Run cone detection (independent of YOLO)
        cones = detect_cones_in_frame(frame)
        all_cones_per_frame.append((int(idx), cones))
    
    cap.release()
    
    logger.info(f"[analysis] Sampled {len(all_detections_per_frame)} frames")
    
    # --- Analyze camera angle ---
    camera_angle, camera_confidence = _analyze_camera_angle(
        frame_width, frame_height, all_detections_per_frame
    )
    
    # --- Analyze cone positions ---
    cone_positions = _analyze_cones(all_cones_per_frame, frame_width, frame_height)
    
    # --- Build drill area polygon from cones ---
    drill_polygon, drill_area_bbox = _build_drill_area(cone_positions, frame_width, frame_height)
    
    # --- Estimate participant count ---
    expected_players, player_confidence, consistent_count, total_count = _estimate_participants(
        all_detections_per_frame, drill_polygon, frame_height
    )
    
    # --- Overall confidence ---
    analysis_confidence = _compute_confidence(
        camera_confidence, player_confidence, cone_positions, drill_polygon
    )
    
    result = SceneAnalysis(
        camera_angle=camera_angle,
        camera_confidence=camera_confidence,
        drill_polygon=drill_polygon,
        drill_area_bbox=drill_area_bbox,
        cone_positions=cone_positions,
        expected_players=expected_players,
        player_confidence=player_confidence,
        total_detections=total_count,
        consistent_detections=consistent_count,
        frame_width=frame_width,
        frame_height=frame_height,
        fps=fps,
        total_frames=total_frames,
        analysis_confidence=analysis_confidence,
    )
    
    logger.info(
        f"[analysis] Results: camera={camera_angle} ({camera_confidence:.0%}), "
        f"cones={len(cone_positions)}, expected_players={expected_players} ({player_confidence:.0%}), "
        f"drill_area={'yes' if drill_polygon is not None else 'no'}, "
        f"confidence={analysis_confidence:.0%}"
    )
    
    return result


def _analyze_camera_angle(
    frame_width: int, 
    frame_height: int, 
    detections_per_frame: list
) -> tuple[str, float]:
    """
    Determine camera angle from frame proportions and detection patterns.
    
    Heuristics:
    - Overhead: frame is roughly square or portrait, players appear small and evenly distributed
    - Sideline: frame is wide (16:9), players appear larger, clustered in middle band
    - Broadcast: wide frame, players have clear perspective (bigger at bottom)
    """
    aspect = frame_width / frame_height
    
    # Gather detection size info
    all_heights = []
    all_y_centers = []
    for _, dets in detections_per_frame:
        for d in dets:
            if d["type"] == "player":
                bbox = d["bbox"]
                h = bbox[3] - bbox[1]
                cy = (bbox[1] + bbox[3]) / 2
                all_heights.append(h / frame_height)  # Normalized height
                all_y_centers.append(cy / frame_height)  # Normalized y center
    
    if not all_heights:
        # No players detected — guess from aspect ratio
        if aspect < 1.2:
            return "overhead", 0.3
        elif aspect < 1.8:
            return "sideline", 0.3
        else:
            return "broadcast", 0.3
    
    mean_height = np.mean(all_heights)
    height_variance = np.var(all_heights)
    y_spread = np.max(all_y_centers) - np.min(all_y_centers) if len(all_y_centers) > 1 else 0
    
    # Overhead: players are small, roughly equal size, spread across frame
    if mean_height < 0.08 and height_variance < 0.001 and y_spread > 0.5:
        return "overhead", min(0.95, 0.6 + y_spread * 0.4)
    
    # Sideline: players are medium-sized, clustered in a band
    if mean_height > 0.05 and y_spread < 0.7:
        return "sideline", min(0.85, 0.5 + (1 - y_spread) * 0.3)
    
    # Broadcast: wide angle, perspective visible (height variance)
    if aspect > 1.5 and height_variance > 0.0005:
        return "broadcast", min(0.8, 0.4 + height_variance * 100)
    
    # Default: use aspect ratio alone
    if aspect < 1.2:
        return "overhead", 0.4
    elif aspect < 1.8:
        return "sideline", 0.4
    else:
        return "broadcast", 0.4


def _analyze_cones(
    cones_per_frame: list, 
    frame_width: int, 
    frame_height: int
) -> list[tuple[float, float]]:
    """
    Find consistent cone positions across frames.
    
    A cone is "consistent" if similar positions appear in multiple frames.
    Returns list of (cx, cy) in normalized coordinates.
    """
    # Collect all cone center points
    all_centers = []
    for frame_idx, cones in cones_per_frame:
        for x1, y1, x2, y2 in cones:
            cx = (x1 + x2) / 2 / frame_width  # Normalize to 0-1
            cy = (y1 + y2) / 2 / frame_height
            all_centers.append((cx, cy, frame_idx))
    
    if not all_centers:
        return []
    
    # Cluster nearby cone centers (same cone across frames)
    # Use simple grid-based clustering
    grid_size = 0.03  # 3% of frame = same cone
    clusters = []
    used = set()
    
    for i, (cx1, cy1, fi) in enumerate(all_centers):
        if i in used:
            continue
        cluster = [(cx1, cy1)]
        used.add(i)
        for j, (cx2, cy2, fj) in enumerate(all_centers):
            if j in used:
                continue
            if abs(cx1 - cx2) < grid_size and abs(cy1 - cy2) < grid_size:
                cluster.append((cx2, cy2))
                used.add(j)
        clusters.append(cluster)
    
    # Keep clusters that appear in at least 2 frames (consistent cones)
    consistent_cones = []
    for cluster in clusters:
        if len(cluster) >= 2:
            mean_cx = np.mean([c[0] for c in cluster])
            mean_cy = np.mean([c[1] for c in cluster])
            consistent_cones.append((mean_cx, mean_cy))
    
    logger.info(f"[analysis] Cone analysis: {len(all_centers)} raw, {len(clusters)} clusters, {len(consistent_cones)} consistent")
    
    return consistent_cones


def _build_drill_area(
    cone_positions: list[tuple[float, float]],
    frame_width: int,
    frame_height: int
) -> tuple[Optional[np.ndarray], Optional[tuple]]:
    """
    Build drill area polygon from cone positions.
    
    If >= 3 cones: convex hull of cone positions
    If < 3 cones but >= 2: expand a rectangle around the cones
    If < 2: return None (no spatial filtering possible)
    """
    if len(cone_positions) < 2:
        return None, None
    
    # Convert to pixel coordinates
    pts = np.array([(cx * frame_width, cy * frame_height) for cx, cy in cone_positions], dtype=np.float32)
    
    if len(cone_positions) >= 3:
        # Convex hull of cone positions
        hull = cv2.convexHull(pts)
        # Expand hull by 40% to give generous margin
        center = np.mean(hull, axis=0)
        expanded = center + (hull - center) * 1.4
        expanded = expanded.astype(np.float32)
        
        bbox = (
            float(expanded[:,:,0].min()), float(expanded[:,:,1].min()),
            float(expanded[:,:,0].max()), float(expanded[:,:,1].max())
        )
        return expanded, bbox
    
    # Only 2 cones: create a wide rectangle around them
    cx1, cy1 = pts[0]
    cx2, cy2 = pts[1]
    margin_x = abs(cx2 - cx1) * 0.5 + frame_width * 0.1
    margin_y = abs(cy2 - cy1) * 0.5 + frame_height * 0.1
    
    x1 = min(cx1, cx2) - margin_x
    y1 = min(cy1, cy2) - margin_y
    x2 = max(cx1, cx2) + margin_x
    y2 = max(cy1, cy2) + margin_y
    
    # Clamp to frame bounds
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(frame_width, x2), min(frame_height, y2)
    
    rect = np.array([[x1, y1], [x2, y1], [x2, y2], [x1, y2]], dtype=np.float32)
    return rect, (x1, y1, x2, y2)


def _estimate_participants(
    detections_per_frame: list,
    drill_polygon: Optional[np.ndarray],
    frame_height: int
) -> tuple[int, float, int, int]:
    """
    Estimate how many players are in the drill.
    
    Strategy:
    1. For each frame, count player detections inside the drill area
    2. Take the median count (robust to outliers)
    3. Count how many unique detection "clusters" appear consistently
    """
    per_frame_player_counts = []
    total_detections = 0
    all_player_centers = []
    
    for frame_idx, dets in detections_per_frame:
        frame_players = []
        for d in dets:
            if d["type"] == "player":
                total_detections += 1
                bbox = d["bbox"]
                cx = (bbox[0] + bbox[2]) / 2
                cy = (bbox[1] + bbox[3]) / 2
                
                # Check if inside drill area (if available)
                if drill_polygon is not None:
                    inside = cv2.pointPolygonTest(
                        drill_polygon, (float(cx), float(cy)), False
                    ) >= 0
                else:
                    inside = True  # No polygon = accept all
                
                if inside:
                    frame_players.append((cx / frame_height, cy / frame_height, frame_idx))
                    all_player_centers.append((cx / frame_height, cy / frame_height))
        
        per_frame_player_counts.append(len(frame_players))
    
    if not per_frame_player_counts:
        return 0, 0.0, 0, total_detections
    
    # Median count of players per frame
    median_count = int(np.median(per_frame_player_counts))
    max_count = max(per_frame_player_counts)
    
    # Cluster player centers to estimate unique individuals
    if all_player_centers:
        unique_players = _count_unique_players(all_player_centers)
    else:
        unique_players = median_count
    
    # Confidence: higher when counts are consistent across frames
    if len(per_frame_player_counts) > 1:
        std_dev = np.std(per_frame_player_counts)
        consistency = max(0, 1 - std_dev / max(median_count, 1))
    else:
        consistency = 0.3
    
    # Use the more reliable estimate (cluster-based vs median)
    if unique_players > 0 and abs(unique_players - median_count) <= 2:
        estimate = unique_players
        confidence = min(0.95, consistency + 0.3)
    else:
        # Prefer the cluster count but cap it
        estimate = min(unique_players, max_count + 1)
        confidence = consistency * 0.7
    
    consistent_count = sum(1 for c in per_frame_player_counts if c >= median_count * 0.5)
    
    return estimate, confidence, consistent_count, total_detections


def _count_unique_players(centers: list[tuple[float, float]], grid_size: float = 0.05) -> int:
    """
    Count unique player positions by spatial clustering.
    
    Uses grid-based clustering: centers within grid_size of each other
    are considered the same player.
    """
    if not centers:
        return 0
    
    # Simple greedy clustering
    clusters = []
    used = [False] * len(centers)
    
    for i in range(len(centers)):
        if used[i]:
            continue
        cluster = [centers[i]]
        used[i] = True
        for j in range(i + 1, len(centers)):
            if used[j]:
                continue
            # Check if close to any point in the cluster
            for cx, cy in cluster:
                if abs(cx - centers[j][0]) < grid_size and abs(cy - centers[j][1]) < grid_size:
                    cluster.append(centers[j])
                    used[j] = True
                    break
        clusters.append(cluster)
    
    return len(clusters)


def _compute_confidence(
    camera_confidence: float,
    player_confidence: float,
    cone_positions: list,
    drill_polygon: Optional[np.ndarray]
) -> float:
    """Compute overall analysis confidence."""
    score = 0.0
    
    # Camera angle detection
    score += camera_confidence * 0.25
    
    # Player count estimation
    score += player_confidence * 0.35
    
    # Cone detection (good for spatial anchoring)
    if len(cone_positions) >= 4:
        score += 0.25
    elif len(cone_positions) >= 2:
        score += 0.15
    elif len(cone_positions) >= 1:
        score += 0.05
    
    # Drill area polygon
    if drill_polygon is not None:
        score += 0.15
    
    return min(1.0, score)
