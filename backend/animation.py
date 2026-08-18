import os
import json
import trimesh
import numpy as np

def build_scene(objects: list[dict], drill_id: str, scenes_dir: str, avatar_dir: str = "data/avatars") -> str:
    os.makedirs(scenes_dir, exist_ok=True)
    scene = trimesh.Scene()

    field = trimesh.creation.box(extents=[30, 0.1, 20])
    field.apply_translation([0, -0.05, 0])
    field.visual.face_colors = [0.2, 0.5, 0.2, 1.0]
    scene.add_geometry(field)

    for obj in objects:
        if obj["type"] == "player":
            _add_player_avatar(scene, obj, avatar_dir)
        elif obj["type"] == "ball":
            _add_ball(scene, obj)
        elif obj["type"] == "cone":
            _add_cone(scene, obj)

    output_path = os.path.join(scenes_dir, f"{drill_id}.glb")
    scene.export(output_path)
    return output_path

AVATAR_MAP = {
    "standard_red": (0.8, 0.2, 0.2),
    "standard_blue": (0.2, 0.3, 0.8),
    "standard_white": (0.9, 0.9, 0.9),
    "standard_black": (0.2, 0.2, 0.2),
    "standard_yellow": (0.9, 0.8, 0.1),
    "standard_green": (0.2, 0.7, 0.2),
    "lean_red": (0.7, 0.15, 0.15),
    "lean_blue": (0.15, 0.25, 0.7),
    "stocky_red": (0.75, 0.15, 0.15),
    "stocky_blue": (0.15, 0.25, 0.75),
    "youth_red": (1.0, 0.3, 0.3),
    "youth_blue": (0.3, 0.4, 1.0),
    "generic": (1.0, 0.6, 0.0),
}

def _select_avatar(obj: dict) -> tuple[str, tuple[float, float, float]]:
    avatar_id = obj.get("avatar_id", "generic")
    if avatar_id in AVATAR_MAP:
        return avatar_id, AVATAR_MAP[avatar_id]
    return "generic", AVATAR_MAP["generic"]

def _create_avatar_mesh(avatar_id: str, color: tuple[float, float, float], avatar_dir: str, body_type: str = "standard") -> trimesh.Trimesh:
    avatar_path = os.path.join(avatar_dir, f"{avatar_id}.glb")
    if os.path.exists(avatar_path):
        mesh = trimesh.load(avatar_path)
        return mesh

    scale_map = {"lean": (0.85, 1.0, 0.85), "stocky": (1.15, 0.9, 1.15), "youth": (0.7, 0.7, 0.7)}
    scale = scale_map.get(body_type, (1.0, 1.0, 1.0))

    body = trimesh.creation.cylinder(radius=0.15 * scale[0], height=0.6 * scale[1], sections=8)
    body.apply_translation([0, 0.3 * scale[1], 0])
    body.visual.face_colors = [*color, 1.0]

    head = trimesh.primitives.Sphere(radius=0.1 * scale[0])
    head.apply_translation([0, 0.7 * scale[1], 0])
    head.visual.face_colors = [0.96, 0.82, 0.69, 1.0]

    left_arm = trimesh.creation.cylinder(radius=0.03, height=0.3 * scale[1], sections=4)
    left_arm.apply_translation([-0.15 * scale[0], 0.5 * scale[1], 0])
    left_arm.visual.face_colors = [*color, 1.0]

    right_arm = trimesh.creation.cylinder(radius=0.03, height=0.3 * scale[1], sections=4)
    right_arm.apply_translation([0.15 * scale[0], 0.5 * scale[1], 0])
    right_arm.visual.face_colors = [*color, 1.0]

    left_leg = trimesh.creation.cylinder(radius=0.03, height=0.3 * scale[1], sections=4)
    left_leg.apply_translation([-0.07 * scale[0], 0.15 * scale[1], 0])
    left_leg.visual.face_colors = [0.3, 0.3, 0.3, 1.0]

    right_leg = trimesh.creation.cylinder(radius=0.03, height=0.3 * scale[1], sections=4)
    right_leg.apply_translation([0.07 * scale[0], 0.15 * scale[1], 0])
    right_leg.visual.face_colors = [0.3, 0.3, 0.3, 1.0]

    return body + head + left_arm + right_arm + left_leg + right_leg

SKELETON_CONNECTIONS = [
    (11, 12),  # shoulders
    (11, 13),  # left upper arm
    (13, 15),  # left forearm
    (12, 14),  # right upper arm
    (14, 16),  # right forearm
    (11, 23),  # left torso
    (12, 24),  # right torso
    (23, 24),  # hips
    (23, 25),  # left upper leg
    (25, 27),  # left lower leg
    (24, 26),  # right upper leg
    (26, 28),  # right lower leg
]


def _create_skeleton_mesh(keypoints: list[dict], color: tuple[float, float, float]) -> trimesh.Trimesh:
    """Create a stick-figure skeleton from keypoints for GLB export."""
    parts = []

    # Joint spheres
    joint_indices = [0, 11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28]
    for idx in joint_indices:
        if idx < len(keypoints) and keypoints[idx]["visibility"] > 0.3:
            kp = keypoints[idx]
            sphere = trimesh.primitives.Sphere(radius=0.03)
            sphere.apply_translation([kp["x"], kp["y"], kp["z"]])
            sphere.visual.face_colors = [*color, 1.0]
            parts.append(sphere)

    # Bone cylinders
    for a, b in SKELETON_CONNECTIONS:
        if a < len(keypoints) and b < len(keypoints):
            kpa = keypoints[a]
            kpb = keypoints[b]
            if kpa["visibility"] > 0.3 and kpb["visibility"] > 0.3:
                start = np.array([kpa["x"], kpa["y"], kpa["z"]])
                end = np.array([kpb["x"], kpb["y"], kpb["z"]])
                midpoint = (start + end) / 2
                length = np.linalg.norm(end - start)
                if length > 0.001:
                    bone = trimesh.creation.cylinder(radius=0.015, height=length, sections=4)
                    bone.apply_translation(midpoint)
                    bone.visual.face_colors = [*color, 1.0]
                    parts.append(bone)

    if not parts:
        # Fallback: tiny sphere if no valid keypoints
        sphere = trimesh.primitives.Sphere(radius=0.05)
        sphere.visual.face_colors = [*color, 1.0]
        return sphere

    combined = parts[0]
    for part in parts[1:]:
        combined = combined + part
    return combined


def _add_player_avatar(scene, obj, avatar_dir):
    # Check if we have keypoints for skeleton rendering
    has_keypoints = False
    if obj.get("frames") and len(obj["frames"]) > 0:
        first_frame = obj["frames"][0]
        if first_frame.get("keypoints") and len(first_frame["keypoints"]) > 0:
            has_keypoints = True

    if has_keypoints:
        # Render skeleton from keypoints (use first frame's pose)
        avatar_id, color = _select_avatar(obj)
        keypoints = obj["frames"][0]["keypoints"]
        mesh = _create_skeleton_mesh(keypoints, color)
        pos = obj["frames"][0]
        mesh.apply_translation([pos["x"], 0.0, pos["z"]])
        scene.add_geometry(mesh)
    else:
        # Fallback: capsule avatar mesh
        avatar_id, color = _select_avatar(obj)
        body_type = avatar_id.split("_")[0] if "_" in avatar_id else "standard"
        mesh = _create_avatar_mesh(avatar_id, color, avatar_dir, body_type)
        if obj.get("frames"):
            pos = obj["frames"][0]
            mesh.apply_translation([pos["x"], 0.0, pos["z"]])
        scene.add_geometry(mesh)

def _add_ball(scene, obj):
    sphere = trimesh.primitives.Sphere(radius=0.11)
    sphere.visual.face_colors = [1.0, 1.0, 1.0, 1.0]
    if obj.get("frames"):
        pos = obj["frames"][0]
        sphere.apply_translation([pos["x"], 0.11, pos["z"]])
    scene.add_geometry(sphere)

def _add_cone(scene, obj):
    cone = trimesh.creation.cone(radius=0.05, height=0.15, sections=8)
    cone.visual.face_colors = [1.0, 0.6, 0.0, 1.0]
    if obj.get("frames"):
        pos = obj["frames"][0]
        cone.apply_translation([pos["x"], 0.075, pos["z"]])
    scene.add_geometry(cone)
