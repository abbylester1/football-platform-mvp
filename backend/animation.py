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

    # Add field lines
    center_line = trimesh.creation.box(extents=[0.04, 0.01, 20])
    center_line.apply_translation([0, 0.0, 0])
    center_line.visual.face_colors = [1.0, 1.0, 1.0, 0.3]
    scene.add_geometry(center_line)

    # Center circle
    ring = trimesh.creation.annulus(r_min=4.5, r_max=4.54, height=0.01, sections=32)
    ring.apply_translation([0, 0.005, 0])
    rot = trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0])
    ring.apply_transform(rot)
    ring.visual.face_colors = [1.0, 1.0, 1.0, 0.3]
    scene.add_geometry(ring)

    for obj in objects:
        if obj["type"] == "player":
            _add_player(scene, obj, avatar_dir)
        elif obj["type"] == "ball":
            _add_ball(scene, obj)
        elif obj["type"] == "cone":
            _add_cone(scene, obj)

    output_path = os.path.join(scenes_dir, f"{drill_id}.glb")
    scene.export(output_path)
    return output_path


# ─── Team color assignments ───
TEAM_PALETTES = [
    {"jersey": [0.8, 0.13, 0.2], "shorts": [1.0, 1.0, 1.0], "socks": [0.8, 0.13, 0.2], "skin": [0.96, 0.82, 0.66]},
    {"jersey": [0.13, 0.27, 0.67], "shorts": [1.0, 1.0, 1.0], "socks": [0.13, 0.27, 0.67], "skin": [0.96, 0.82, 0.66]},
    {"jersey": [0.87, 0.67, 0.0], "shorts": [0.13, 0.13, 0.13], "socks": [0.87, 0.67, 0.0], "skin": [0.96, 0.82, 0.66]},
    {"jersey": [0.13, 0.53, 0.2], "shorts": [1.0, 1.0, 1.0], "socks": [0.13, 0.53, 0.2], "skin": [0.96, 0.82, 0.66]},
    {"jersey": [0.94, 0.94, 0.94], "shorts": [0.13, 0.13, 0.13], "socks": [0.94, 0.94, 0.94], "skin": [0.96, 0.82, 0.66]},
    {"jersey": [0.13, 0.13, 0.13], "shorts": [1.0, 1.0, 1.0], "socks": [0.13, 0.13, 0.13], "skin": [0.96, 0.82, 0.66]},
]


def _assign_team(obj_id: str, label: str) -> dict:
    """Consistent team assignment based on ID hash."""
    h = 0
    s = obj_id + label
    for c in s:
        h = ((h << 5) - h + ord(c)) & 0xFFFFFFFF
    idx = abs(h) % len(TEAM_PALETTES)
    return TEAM_PALETTES[idx]


def _add_player(scene, obj, avatar_dir):
    """Add a realistic football player mesh to the scene."""
    team = _assign_team(obj["id"], obj.get("label", ""))
    jersey = team["jersey"]
    shorts = team["shorts"]
    socks = team["socks"]
    skin = team["skin"]

    # Determine position from first frame
    if not obj.get("frames"):
        return
    pos = obj["frames"][0]
    x, z = pos["x"], pos["z"]

    # Check for keypoints (skeleton rendering)
    has_kp = pos.get("keypoints") and len(pos.get("keypoints", [])) > 0

    if has_kp:
        _add_skeleton(scene, pos["keypoints"], jersey, x, z)
    else:
        _add_procedural_player(scene, jersey, shorts, socks, skin, x, z)


def _add_procedural_player(scene, jersey, shorts, socks, skin, x, z):
    """Build a football player from basic shapes."""
    parts = []

    # Torso (jersey)
    torso = trimesh.creation.box(extents=[0.32, 0.4, 0.2])
    torso.apply_translation([x, 0.85, z])
    torso.visual.face_colors = [*jersey, 1.0]
    parts.append(torso)

    # Shorts
    short = trimesh.creation.box(extents=[0.34, 0.16, 0.22])
    short.apply_translation([x, 0.58, z])
    short.visual.face_colors = [*shorts, 1.0]
    parts.append(short)

    # Head
    head = trimesh.primitives.Sphere(radius=0.1, subdivisions=6)
    head.apply_translation([x, 1.18, z])
    head.visual.face_colors = [*skin, 1.0]
    parts.append(head)

    # Hair
    hair = trimesh.primitives.Sphere(radius=0.1, subdivisions=6)
    hair.apply_translation([x, 1.23, z - 0.02])
    hair.visual.face_colors = [0.23, 0.16, 0.1, 1.0]
    parts.append(hair)

    # Arms (jersey upper + skin lower)
    for side in [-1, 1]:
        upper_arm = trimesh.creation.box(extents=[0.08, 0.16, 0.08])
        upper_arm.apply_translation([x + side * 0.22, 0.87, z])
        upper_arm.visual.face_colors = [*jersey, 1.0]
        parts.append(upper_arm)

        lower_arm = trimesh.creation.box(extents=[0.06, 0.12, 0.06])
        lower_arm.apply_translation([x + side * 0.22, 0.73, z])
        lower_arm.visual.face_colors = [*skin, 1.0]
        parts.append(lower_arm)

    # Legs (skin thigh + sock shin + boot)
    for side in [-1, 1]:
        thigh = trimesh.creation.box(extents=[0.1, 0.2, 0.1])
        thigh.apply_translation([x + side * 0.1, 0.38, z])
        thigh.visual.face_colors = [*skin, 1.0]
        parts.append(thigh)

        shin = trimesh.creation.box(extents=[0.08, 0.16, 0.08])
        shin.apply_translation([x + side * 0.1, 0.2, z])
        shin.visual.face_colors = [*socks, 1.0]
        parts.append(shin)

        boot = trimesh.creation.box(extents=[0.09, 0.06, 0.14])
        boot.apply_translation([x + side * 0.1, 0.12, z + 0.02])
        boot.visual.face_colors = [0.07, 0.07, 0.07, 1.0]
        parts.append(boot)

    combined = parts[0]
    for part in parts[1:]:
        combined = combined + part
    scene.add_geometry(combined)


def _add_skeleton(scene, keypoints, color, x, z):
    """Add skeleton mesh from keypoints."""
    parts = []
    connections = [
        (11, 12), (11, 13), (13, 15), (12, 14), (14, 16),
        (11, 23), (12, 24), (23, 24), (23, 25), (25, 27), (24, 26), (26, 28),
    ]

    # Joint spheres
    for idx in [0, 11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28]:
        if idx < len(keypoints) and keypoints[idx].get("visibility", 0) > 0.3:
            kp = keypoints[idx]
            sphere = trimesh.primitives.Sphere(radius=0.03)
            sphere.apply_translation([kp["x"], kp["y"], kp["z"]])
            sphere.visual.face_colors = [*color, 1.0]
            parts.append(sphere)

    # Bone cylinders
    for a, b in connections:
        if a < len(keypoints) and b < len(keypoints):
            kpa, kpb = keypoints[a], keypoints[b]
            if kpa.get("visibility", 0) > 0.3 and kpb.get("visibility", 0) > 0.3:
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
        sphere = trimesh.primitives.Sphere(radius=0.15)
        sphere.visual.face_colors = [*color, 1.0]
        parts.append(sphere)

    combined = parts[0]
    for part in parts[1:]:
        combined = combined + part
    scene.add_geometry(combined)


def _add_ball(scene, obj):
    sphere = trimesh.primitives.Sphere(radius=0.11)
    sphere.visual.face_colors = [1.0, 1.0, 1.0, 1.0]
    if obj.get("frames"):
        pos = obj["frames"][0]
        sphere.apply_translation([pos["x"], 0.11, pos["z"]])
    scene.add_geometry(sphere)


def _add_cone(scene, obj):
    cone = trimesh.creation.cone(radius=0.05, height=0.15, sections=8)
    cone.visual.face_colors = [1.0, 0.55, 0.0, 1.0]
    if obj.get("frames"):
        pos = obj["frames"][0]
        cone.apply_translation([pos["x"], 0.075, pos["z"]])
    base = trimesh.creation.cylinder(radius=0.06, height=0.02, sections=8)
    base.visual.face_colors = [1.0, 0.4, 0.0, 1.0]
    if obj.get("frames"):
        pos = obj["frames"][0]
        base.apply_translation([pos["x"], 0.01, pos["z"]])
    scene.add_geometry(cone + base)
