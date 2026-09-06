"""Generate a compact, Roblox-oriented sci-fi prop pack with Blender.

Executed headlessly by GitHub Actions. Geometry is authored in metric units using
Roblox's documented physical convention of 1 stud = 0.28 metres. Each prop is
exported as GLB and FBX, rendered to a PNG preview, and described in catalog.json.
"""
from __future__ import annotations

import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import bpy
from mathutils import Vector

STUD_METRES = 0.28
ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get("ASSET_OUT", ROOT / "dist")).resolve()
ASSET_DIR = OUT / "assets"
PREVIEW_DIR = OUT / "previews"
SOURCE_DIR = OUT / "source"
DOWNLOAD_DIR = OUT / "downloads"

for directory in (OUT, ASSET_DIR, PREVIEW_DIR, SOURCE_DIR, DOWNLOAD_DIR):
    directory.mkdir(parents=True, exist_ok=True)


def studs(value: float) -> float:
    return value * STUD_METRES


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in list(bpy.data.collections):
        if collection.name != "Collection":
            bpy.data.collections.remove(collection)
    base = bpy.data.collections.get("Collection")
    if base:
        for obj in list(base.objects):
            base.objects.unlink(obj)


def move_to_collection(obj: bpy.types.Object, collection: bpy.types.Collection) -> None:
    for current in list(obj.users_collection):
        current.objects.unlink(obj)
    collection.objects.link(obj)


def material(
    name: str,
    colour: tuple[float, float, float, float],
    *,
    metallic: float = 0.0,
    roughness: float = 0.45,
    emission: tuple[float, float, float, float] | None = None,
    emission_strength: float = 0.0,
) -> bpy.types.Material:
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name=name)
    mat.use_nodes = True
    mat.diffuse_color = colour
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is None:
        raise RuntimeError(f"Principled BSDF missing for material {name}")
    bsdf.inputs["Base Color"].default_value = colour
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    if emission is not None:
        emission_input = bsdf.inputs.get("Emission Color") or bsdf.inputs.get("Emission")
        strength_input = bsdf.inputs.get("Emission Strength")
        if emission_input is not None:
            emission_input.default_value = emission
        if strength_input is not None:
            strength_input.default_value = emission_strength
    return mat


MATS = {
    "navy": material("Navy Polymer", (0.025, 0.055, 0.09, 1), metallic=0.22, roughness=0.30),
    "steel": material("Brushed Steel", (0.18, 0.23, 0.29, 1), metallic=0.78, roughness=0.24),
    "dark_steel": material("Dark Steel", (0.045, 0.065, 0.085, 1), metallic=0.72, roughness=0.32),
    "orange": material("Signal Orange", (0.95, 0.23, 0.045, 1), metallic=0.18, roughness=0.34),
    "gold": material("Pickup Gold", (1.0, 0.52, 0.055, 1), metallic=0.72, roughness=0.22),
    "cyan": material(
        "Energy Cyan",
        (0.015, 0.55, 0.78, 1),
        metallic=0.12,
        roughness=0.22,
        emission=(0.0, 0.72, 1.0, 1),
        emission_strength=5.0,
    ),
    "magenta": material(
        "Energy Magenta",
        (0.72, 0.025, 0.52, 1),
        metallic=0.1,
        roughness=0.24,
        emission=(1.0, 0.01, 0.55, 1),
        emission_strength=4.0,
    ),
    "crystal": material(
        "Crystal Core",
        (0.08, 0.32, 0.62, 1),
        metallic=0.12,
        roughness=0.18,
        emission=(0.0, 0.48, 1.0, 1),
        emission_strength=3.2,
    ),
    "rubber": material("Industrial Rubber", (0.018, 0.022, 0.028, 1), metallic=0.0, roughness=0.7),
}


def assign_material(obj: bpy.types.Object, mat: bpy.types.Material) -> None:
    if obj.type == "MESH":
        obj.data.materials.append(mat)


def apply_scale(obj: bpy.types.Object) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.select_set(False)


def bevel(obj: bpy.types.Object, width: float, segments: int = 2) -> None:
    if width <= 0 or obj.type != "MESH":
        return
    modifier = obj.modifiers.new(name="RobloxEdgeSoftening", type="BEVEL")
    modifier.width = width
    modifier.segments = segments
    modifier.limit_method = "ANGLE"
    modifier.angle_limit = math.radians(25)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    obj.select_set(False)


def add_box(
    collection: bpy.types.Collection,
    name: str,
    size_studs: tuple[float, float, float],
    location_studs: tuple[float, float, float],
    mat: bpy.types.Material,
    *,
    bevel_studs: float = 0.08,
    rotation: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(
        location=tuple(studs(v) for v in location_studs),
        rotation=rotation,
    )
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = tuple(studs(v) for v in size_studs)
    apply_scale(obj)
    bevel(obj, studs(bevel_studs))
    assign_material(obj, mat)
    move_to_collection(obj, collection)
    return obj


def add_cylinder(
    collection: bpy.types.Collection,
    name: str,
    radius_studs: float,
    depth_studs: float,
    location_studs: tuple[float, float, float],
    mat: bpy.types.Material,
    *,
    vertices: int = 16,
    bevel_studs: float = 0.04,
    rotation: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices,
        radius=studs(radius_studs),
        depth=studs(depth_studs),
        location=tuple(studs(v) for v in location_studs),
        rotation=rotation,
    )
    obj = bpy.context.object
    obj.name = name
    apply_scale(obj)
    bevel(obj, studs(bevel_studs), segments=2)
    assign_material(obj, mat)
    move_to_collection(obj, collection)
    return obj


def add_cone(
    collection: bpy.types.Collection,
    name: str,
    radius1_studs: float,
    radius2_studs: float,
    depth_studs: float,
    location_studs: tuple[float, float, float],
    mat: bpy.types.Material,
    *,
    vertices: int = 12,
    rotation: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cone_add(
        vertices=vertices,
        radius1=studs(radius1_studs),
        radius2=studs(radius2_studs),
        depth=studs(depth_studs),
        location=tuple(studs(v) for v in location_studs),
        rotation=rotation,
    )
    obj = bpy.context.object
    obj.name = name
    apply_scale(obj)
    assign_material(obj, mat)
    move_to_collection(obj, collection)
    return obj


def add_icosphere(
    collection: bpy.types.Collection,
    name: str,
    radius_studs: float,
    location_studs: tuple[float, float, float],
    mat: bpy.types.Material,
    *,
    subdivisions: int = 1,
    scale: tuple[float, float, float] = (1.0, 1.0, 1.0),
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_ico_sphere_add(
        subdivisions=subdivisions,
        radius=studs(radius_studs),
        location=tuple(studs(v) for v in location_studs),
    )
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    apply_scale(obj)
    assign_material(obj, mat)
    move_to_collection(obj, collection)
    return obj


def add_crystal(
    collection: bpy.types.Collection,
    name: str,
    radius_studs: float,
    height_studs: float,
    location_studs: tuple[float, float, float],
    mat: bpy.types.Material,
    *,
    sides: int = 6,
    rotation: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> bpy.types.Object:
    radius = studs(radius_studs)
    height = studs(height_studs)
    ring_z = -height * 0.28
    top_z = height * 0.5
    bottom_z = -height * 0.5
    vertices: list[tuple[float, float, float]] = [(0.0, 0.0, bottom_z)]
    for index in range(sides):
        angle = 2 * math.pi * index / sides
        vertices.append((radius * math.cos(angle), radius * math.sin(angle), ring_z))
    vertices.append((0.0, 0.0, top_z))
    top_index = len(vertices) - 1
    faces: list[tuple[int, int, int]] = []
    for index in range(sides):
        current = 1 + index
        nxt = 1 + ((index + 1) % sides)
        faces.append((0, nxt, current))
        faces.append((top_index, current, nxt))
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    obj.location = tuple(studs(v) for v in location_studs)
    obj.rotation_euler = rotation
    collection.objects.link(obj)
    assign_material(obj, mat)
    return obj


def add_root(collection: bpy.types.Collection, slug: str) -> bpy.types.Object:
    root = bpy.data.objects.new(f"{slug}__ROOT", None)
    root.empty_display_type = "CUBE"
    root.empty_display_size = studs(0.3)
    collection.objects.link(root)
    for obj in list(collection.objects):
        if obj != root and obj.parent is None:
            world = obj.matrix_world.copy()
            obj.parent = root
            obj.matrix_world = world
    return root


def new_asset(slug: str) -> bpy.types.Collection:
    collection = bpy.data.collections.new(f"ASSET_{slug}")
    bpy.context.scene.collection.children.link(collection)
    return collection


def build_cargo_crate() -> tuple[bpy.types.Collection, dict[str, Any]]:
    col = new_asset("cargo-crate")
    add_box(col, "CrateBody", (4.0, 4.0, 3.6), (0, 0, 1.9), MATS["navy"], bevel_studs=0.16)
    beam = 0.28
    for x in (-2.05, 2.05):
        for y in (-2.05, 2.05):
            add_box(col, f"VerticalFrame_{x}_{y}", (beam, beam, 3.9), (x, y, 1.95), MATS["orange"], bevel_studs=0.06)
    for z in (0.18, 3.72):
        add_box(col, f"FrameXFront_{z}", (4.35, beam, beam), (0, -2.05, z), MATS["orange"], bevel_studs=0.05)
        add_box(col, f"FrameXBack_{z}", (4.35, beam, beam), (0, 2.05, z), MATS["orange"], bevel_studs=0.05)
        add_box(col, f"FrameYLeft_{z}", (beam, 4.35, beam), (-2.05, 0, z), MATS["orange"], bevel_studs=0.05)
        add_box(col, f"FrameYRight_{z}", (beam, 4.35, beam), (2.05, 0, z), MATS["orange"], bevel_studs=0.05)
    add_box(col, "FrontPanel", (2.65, 0.15, 1.55), (0, -2.08, 2.0), MATS["dark_steel"], bevel_studs=0.07)
    add_box(col, "FrontEnergyBar", (1.75, 0.12, 0.18), (0, -2.18, 2.0), MATS["cyan"], bevel_studs=0.04)
    for x in (-1.55, 1.55):
        add_box(col, f"TopLatch_{x}", (0.38, 0.55, 0.18), (x, -1.25, 3.92), MATS["steel"], bevel_studs=0.05)
    add_root(col, "cargo-crate")
    return col, {
        "slug": "cargo-crate",
        "name": "NX-4 Cargo Crate",
        "category": "Environment",
        "description": "A compact loot or shipping crate with readable silhouette, protected corners, and a cyan status strip.",
        "accent": "#ff5a1f",
        "robloxUse": ["loot container", "cover prop", "warehouse dressing"],
    }


def build_energy_barrel() -> tuple[bpy.types.Collection, dict[str, Any]]:
    col = new_asset("energy-barrel")
    add_cylinder(col, "BarrelCore", 1.45, 4.4, (0, 0, 2.25), MATS["navy"], vertices=16, bevel_studs=0.09)
    for z in (0.22, 1.42, 3.08, 4.28):
        add_cylinder(col, f"Reinforcement_{z}", 1.58, 0.24, (0, 0, z), MATS["steel"], vertices=16, bevel_studs=0.04)
    for z in (1.72, 2.78):
        add_cylinder(col, f"EnergyBand_{z}", 1.515, 0.16, (0, 0, z), MATS["cyan"], vertices=16, bevel_studs=0.02)
    add_cylinder(col, "TopCap", 1.22, 0.20, (0, 0, 4.52), MATS["dark_steel"], vertices=12, bevel_studs=0.04)
    add_cylinder(col, "Valve", 0.28, 0.42, (0, 0, 4.78), MATS["orange"], vertices=10, bevel_studs=0.03)
    for side in (-1, 1):
        add_box(col, f"Handle_{side}", (0.22, 0.55, 1.35), (side * 1.56, 0, 2.28), MATS["orange"], bevel_studs=0.06)
    add_root(col, "energy-barrel")
    return col, {
        "slug": "energy-barrel",
        "name": "Flux Energy Barrel",
        "category": "Environment",
        "description": "A low-poly hazardous-energy barrel suitable for objectives, destructibles, or industrial set dressing.",
        "accent": "#00d9ff",
        "robloxUse": ["objective prop", "hazard", "industrial dressing"],
    }


def build_security_gate() -> tuple[bpy.types.Collection, dict[str, Any]]:
    col = new_asset("security-gate")
    add_box(col, "LeftPillar", (1.45, 2.15, 8.0), (-4.3, 0, 4.0), MATS["dark_steel"], bevel_studs=0.18)
    add_box(col, "RightPillar", (1.45, 2.15, 8.0), (4.3, 0, 4.0), MATS["dark_steel"], bevel_studs=0.18)
    add_box(col, "TopBeam", (10.0, 2.15, 1.35), (0, 0, 7.42), MATS["dark_steel"], bevel_studs=0.18)
    add_box(col, "LeftDoor", (3.45, 0.55, 6.25), (-1.78, 0, 3.2), MATS["navy"], bevel_studs=0.12)
    add_box(col, "RightDoor", (3.45, 0.55, 6.25), (1.78, 0, 3.2), MATS["navy"], bevel_studs=0.12)
    add_box(col, "DoorSeam", (0.16, 0.64, 5.7), (0, -0.02, 3.18), MATS["cyan"], bevel_studs=0.03)
    for x in (-4.3, 4.3):
        add_box(col, f"PillarLight_{x}", (0.18, 0.18, 5.0), (x, -1.12, 3.8), MATS["cyan"], bevel_studs=0.03)
        add_box(col, f"Foot_{x}", (2.15, 3.1, 0.38), (x, 0, 0.19), MATS["steel"], bevel_studs=0.08)
    add_box(col, "AccessPanel", (0.78, 0.20, 1.20), (3.95, -1.13, 3.6), MATS["orange"], bevel_studs=0.07)
    add_box(col, "HeaderLight", (5.2, 0.18, 0.22), (0, -1.12, 7.52), MATS["magenta"], bevel_studs=0.04)
    add_root(col, "security-gate")
    return col, {
        "slug": "security-gate",
        "name": "Aegis Security Gate",
        "category": "Architecture",
        "description": "A modular ten-stud sci-fi doorway with split doors, access panel, and emissive navigation strips.",
        "accent": "#ff2aa9",
        "robloxUse": ["level gate", "spawn entrance", "mission checkpoint"],
    }


def build_crystal_node() -> tuple[bpy.types.Collection, dict[str, Any]]:
    col = new_asset("crystal-node")
    add_cylinder(col, "BaseLower", 2.15, 0.55, (0, 0, 0.275), MATS["rubber"], vertices=8, bevel_studs=0.06)
    add_cylinder(col, "BaseUpper", 1.72, 0.48, (0, 0, 0.74), MATS["steel"], vertices=8, bevel_studs=0.05)
    add_cylinder(col, "EnergySocket", 1.25, 0.25, (0, 0, 1.08), MATS["cyan"], vertices=8, bevel_studs=0.03)
    add_crystal(col, "MainCrystal", 0.88, 4.8, (0, 0, 3.05), MATS["crystal"], sides=6, rotation=(0.04, -0.05, 0.12))
    add_crystal(col, "SideCrystalA", 0.50, 3.05, (1.05, 0.2, 2.12), MATS["crystal"], sides=5, rotation=(0.2, -0.28, 0.18))
    add_crystal(col, "SideCrystalB", 0.46, 2.62, (-0.95, 0.42, 1.88), MATS["magenta"], sides=5, rotation=(-0.14, 0.32, -0.1))
    add_crystal(col, "SideCrystalC", 0.34, 2.08, (0.15, -0.92, 1.62), MATS["crystal"], sides=5, rotation=(0.31, 0.08, 0.3))
    for angle in (0, math.pi / 2, math.pi, 3 * math.pi / 2):
        x = math.cos(angle) * 1.72
        y = math.sin(angle) * 1.72
        add_box(col, f"Clamp_{round(angle, 2)}", (0.34, 0.7, 0.78), (x, y, 0.9), MATS["orange"], bevel_studs=0.07, rotation=(0, 0, angle))
    add_root(col, "crystal-node")
    return col, {
        "slug": "crystal-node",
        "name": "Cryon Crystal Node",
        "category": "Resource",
        "description": "A faceted resource node with a reinforced octagonal socket and contrasting secondary crystal.",
        "accent": "#20c7ff",
        "robloxUse": ["mining node", "power source", "quest objective"],
    }


def build_beacon_lamp() -> tuple[bpy.types.Collection, dict[str, Any]]:
    col = new_asset("beacon-lamp")
    add_cylinder(col, "Base", 1.45, 0.45, (0, 0, 0.225), MATS["rubber"], vertices=12, bevel_studs=0.06)
    add_cylinder(col, "BaseRing", 1.15, 0.34, (0, 0, 0.56), MATS["orange"], vertices=12, bevel_studs=0.04)
    add_cylinder(col, "Pole", 0.34, 4.5, (0, 0, 2.85), MATS["steel"], vertices=10, bevel_studs=0.04)
    add_cylinder(col, "LampLower", 1.05, 0.30, (0, 0, 5.18), MATS["dark_steel"], vertices=10, bevel_studs=0.05)
    add_cylinder(col, "LampCore", 0.78, 1.55, (0, 0, 6.08), MATS["cyan"], vertices=10, bevel_studs=0.08)
    add_cone(col, "LampCap", 1.08, 0.45, 0.72, (0, 0, 7.22), MATS["orange"], vertices=10)
    for angle in (0, math.pi / 2, math.pi, 3 * math.pi / 2):
        x = math.cos(angle) * 0.92
        y = math.sin(angle) * 0.92
        add_box(col, f"Guard_{round(angle, 2)}", (0.16, 0.16, 1.92), (x, y, 6.05), MATS["dark_steel"], bevel_studs=0.03)
    add_box(col, "ControlBox", (0.95, 0.58, 1.25), (0, -0.58, 2.65), MATS["navy"], bevel_studs=0.10)
    add_box(col, "ControlIndicator", (0.46, 0.08, 0.16), (0, -0.9, 2.8), MATS["magenta"], bevel_studs=0.03)
    add_root(col, "beacon-lamp")
    return col, {
        "slug": "beacon-lamp",
        "name": "Pathfinder Beacon",
        "category": "Environment",
        "description": "A tall navigation beacon with a protected energy core and a readable interaction/control box.",
        "accent": "#00dbff",
        "robloxUse": ["checkpoint", "path lighting", "interaction marker"],
    }


def build_hover_drone() -> tuple[bpy.types.Collection, dict[str, Any]]:
    col = new_asset("hover-drone")
    add_icosphere(col, "DroneBody", 1.35, (0, 0, 2.85), MATS["navy"], subdivisions=2, scale=(1.15, 1.0, 0.58))
    add_icosphere(col, "DroneEyeHousing", 0.62, (0, -1.0, 2.82), MATS["dark_steel"], subdivisions=1, scale=(1.0, 0.45, 0.72))
    add_icosphere(col, "DroneEye", 0.34, (0, -1.31, 2.82), MATS["magenta"], subdivisions=2, scale=(1.0, 0.35, 1.0))
    arm_positions = ((1.85, 0.85), (-1.85, 0.85), (1.85, -0.85), (-1.85, -0.85))
    for index, (x, y) in enumerate(arm_positions):
        angle = math.atan2(y, x)
        length = math.sqrt(x * x + y * y)
        add_box(col, f"Arm_{index}", (length, 0.26, 0.24), (x / 2, y / 2, 2.9), MATS["steel"], bevel_studs=0.06, rotation=(0, 0, angle))
        add_cylinder(col, f"RotorHousing_{index}", 0.74, 0.20, (x, y, 2.95), MATS["dark_steel"], vertices=12, bevel_studs=0.03)
        add_cylinder(col, f"RotorGlow_{index}", 0.50, 0.12, (x, y, 3.08), MATS["cyan"], vertices=12, bevel_studs=0.02)
        add_cylinder(col, f"LandingPad_{index}", 0.34, 0.18, (x * 0.78, y * 0.78, 1.68), MATS["rubber"], vertices=10, bevel_studs=0.03)
        add_box(col, f"LandingStrut_{index}", (0.18, 0.18, 1.2), (x * 0.78, y * 0.78, 2.28), MATS["steel"], bevel_studs=0.03)
    add_box(col, "TopStripe", (1.8, 0.24, 0.18), (0, 0.15, 3.65), MATS["orange"], bevel_studs=0.04)
    add_root(col, "hover-drone")
    return col, {
        "slug": "hover-drone",
        "name": "Warden Hover Drone",
        "category": "Vehicle",
        "description": "A static four-rotor security drone prop with a strong central eye and simple collision-friendly structure.",
        "accent": "#ff2aa9",
        "robloxUse": ["enemy shell", "companion prop", "security decoration"],
    }


def collection_meshes(collection: bpy.types.Collection) -> list[bpy.types.Object]:
    return [obj for obj in collection.all_objects if obj.type == "MESH"]


def mesh_stats(collection: bpy.types.Collection) -> tuple[int, int]:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    triangles = 0
    vertices = 0
    for obj in collection_meshes(collection):
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        mesh.calc_loop_triangles()
        triangles += len(mesh.loop_triangles)
        vertices += len(mesh.vertices)
        evaluated.to_mesh_clear()
    return triangles, vertices


def collection_bounds(collection: bpy.types.Collection) -> tuple[Vector, Vector]:
    minimum = Vector((float("inf"),) * 3)
    maximum = Vector((float("-inf"),) * 3)
    found = False
    for obj in collection_meshes(collection):
        for corner in obj.bound_box:
            world = obj.matrix_world @ Vector(corner)
            minimum.x = min(minimum.x, world.x)
            minimum.y = min(minimum.y, world.y)
            minimum.z = min(minimum.z, world.z)
            maximum.x = max(maximum.x, world.x)
            maximum.y = max(maximum.y, world.y)
            maximum.z = max(maximum.z, world.z)
            found = True
    if not found:
        return Vector((0, 0, 0)), Vector((1, 1, 1))
    return minimum, maximum


def select_collection(collection: bpy.types.Collection) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    active = None
    for obj in collection.all_objects:
        obj.hide_set(False)
        obj.select_set(True)
        if active is None and obj.type == "MESH":
            active = obj
    bpy.context.view_layer.objects.active = active


def export_asset(collection: bpy.types.Collection, slug: str) -> None:
    select_collection(collection)
    glb_path = ASSET_DIR / f"{slug}.glb"
    fbx_path = ASSET_DIR / f"{slug}.fbx"
    bpy.ops.export_scene.gltf(
        filepath=str(glb_path),
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_animations=False,
        export_materials="EXPORT",
    )
    bpy.ops.export_scene.fbx(
        filepath=str(fbx_path),
        use_selection=True,
        axis_forward="-Z",
        axis_up="Y",
        apply_unit_scale=True,
        apply_scale_options="FBX_SCALE_UNITS",
        add_leaf_bones=False,
        bake_anim=False,
        mesh_smooth_type="FACE",
        path_mode="COPY",
        embed_textures=True,
    )


def look_at(obj: bpy.types.Object, target: Vector) -> None:
    direction = target - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def setup_render_scene() -> tuple[bpy.types.Object, list[bpy.types.Collection]]:
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "METERS"
    scene.unit_settings.scale_length = 1.0
    scene.render.resolution_x = 800
    scene.render.resolution_y = 600
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.image_settings.color_mode = "RGBA"
    try:
        scene.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        pass
    for engine in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "BLENDER_WORKBENCH"):
        try:
            scene.render.engine = engine
            break
        except Exception:
            continue
    if hasattr(scene, "eevee"):
        try:
            scene.eevee.taa_render_samples = 64
        except Exception:
            pass
    world = scene.world or bpy.data.worlds.new("ForgeWorld")
    scene.world = world
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (0.006, 0.012, 0.022, 1)
    background.inputs["Strength"].default_value = 0.22

    global_collection = bpy.data.collections.new("RENDER_STAGE")
    scene.collection.children.link(global_collection)

    ground_mat = material("Preview Ground", (0.012, 0.021, 0.034, 1), metallic=0.12, roughness=0.62)
    bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, -0.008))
    ground = bpy.context.object
    ground.name = "PreviewGround"
    assign_material(ground, ground_mat)
    move_to_collection(ground, global_collection)

    bpy.ops.object.camera_add(location=(5, -7, 5))
    camera = bpy.context.object
    camera.name = "PreviewCamera"
    camera.data.lens = 56
    camera.data.sensor_width = 36
    scene.camera = camera
    move_to_collection(camera, global_collection)

    def area_light(name: str, location: tuple[float, float, float], energy: float, size: float, colour: tuple[float, float, float]) -> None:
        data = bpy.data.lights.new(name=name, type="AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = size
        data.color = colour
        obj = bpy.data.objects.new(name, data)
        obj.location = location
        global_collection.objects.link(obj)
        look_at(obj, Vector((0, 0, 1.0)))

    area_light("KeyLight", (4.6, -6.2, 7.2), 1050, 4.0, (0.72, 0.88, 1.0))
    area_light("FillLight", (-4.2, -2.2, 4.5), 720, 3.5, (1.0, 0.35, 0.16))
    area_light("RimLight", (3.4, 4.7, 6.4), 980, 3.0, (0.16, 0.58, 1.0))
    return camera, [global_collection]


def render_preview(
    collection: bpy.types.Collection,
    all_assets: Iterable[bpy.types.Collection],
    camera: bpy.types.Object,
    slug: str,
) -> None:
    for candidate in all_assets:
        candidate.hide_render = candidate != collection
        candidate.hide_viewport = False
    minimum, maximum = collection_bounds(collection)
    center = (minimum + maximum) * 0.5
    dimensions = maximum - minimum
    max_dimension = max(dimensions.x, dimensions.y, dimensions.z)
    direction = Vector((1.45, -1.75, 1.12)).normalized()
    camera.location = center + direction * (max_dimension * 2.55 + studs(1.2))
    target = center + Vector((0, 0, dimensions.z * 0.04))
    look_at(camera, target)
    bpy.context.scene.render.filepath = str(PREVIEW_DIR / f"{slug}.png")
    bpy.ops.render.render(write_still=True)


def build_catalog(assets: list[tuple[bpy.types.Collection, dict[str, Any]]]) -> dict[str, Any]:
    output_assets: list[dict[str, Any]] = []
    for collection, metadata in assets:
        triangles, vertices = mesh_stats(collection)
        minimum, maximum = collection_bounds(collection)
        dimensions = maximum - minimum
        materials = sorted({slot.material.name for obj in collection_meshes(collection) for slot in obj.material_slots if slot.material})
        slug = metadata["slug"]
        output_assets.append(
            {
                **metadata,
                "stats": {
                    "triangles": triangles,
                    "vertices": vertices,
                    "meshObjects": len(collection_meshes(collection)),
                    "materials": len(materials),
                },
                "dimensionsStuds": [round(value / STUD_METRES, 2) for value in dimensions],
                "materials": materials,
                "files": {
                    "glb": f"assets/{slug}.glb",
                    "fbx": f"assets/{slug}.fbx",
                    "preview": f"previews/{slug}.png",
                },
            }
        )
    return {
        "pack": {
            "name": "Neon Salvage — Roblox Starter Pack",
            "version": "1.0.0",
            "description": "Six original low-poly sci-fi props generated procedurally in Blender for Roblox prototyping.",
            "license": "CC0-1.0",
            "generator": "blender/generate_assets.py",
            "blenderVersion": bpy.app.version_string,
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "studMetres": STUD_METRES,
            "sourceBlend": "source/neon-salvage-pack.blend",
            "bundle": "downloads/neon-salvage-pack.zip",
        },
        "assets": output_assets,
    }


def main() -> None:
    clear_scene()
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "METERS"
    scene.unit_settings.scale_length = 1.0

    assets = [
        build_cargo_crate(),
        build_energy_barrel(),
        build_security_gate(),
        build_crystal_node(),
        build_beacon_lamp(),
        build_hover_drone(),
    ]
    asset_collections = [collection for collection, _ in assets]

    camera, _ = setup_render_scene()
    for collection, metadata in assets:
        slug = metadata["slug"]
        export_asset(collection, slug)
        render_preview(collection, asset_collections, camera, slug)

    for collection in asset_collections:
        collection.hide_render = False
        collection.hide_viewport = False

    blend_path = SOURCE_DIR / "neon-salvage-pack.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), compress=True)

    catalog = build_catalog(assets)
    (OUT / "catalog.json").write_text(json.dumps(catalog, indent=2), encoding="utf-8")
    print(json.dumps({"status": "ok", "output": str(OUT), "assets": len(assets), "blender": bpy.app.version_string}))


if __name__ == "__main__":
    main()
