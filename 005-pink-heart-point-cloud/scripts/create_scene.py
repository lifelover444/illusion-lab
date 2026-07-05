import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


HEART_X_LIMIT = 1.35
HEART_Y_MIN = -1.15
HEART_Y_MAX = 1.25


def parse_args():
    parser = argparse.ArgumentParser(description="Create and optionally render the pink heart point cloud illusion.")
    parser.add_argument("--profile", choices=("preview", "final"), default="preview")
    parser.add_argument("--project-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--render", action="store_true")
    script_args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return parser.parse_args(script_args)


def load_config():
    config_path = Path(__file__).resolve().parent / "heart-config.json"
    return json.loads(config_path.read_text(encoding="utf-8"))


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()

    for data_block in (
        bpy.data.meshes,
        bpy.data.curves,
        bpy.data.materials,
        bpy.data.cameras,
        bpy.data.lights,
        bpy.data.collections,
    ):
        for item in list(data_block):
            if item.users == 0:
                data_block.remove(item)


def make_collection(name):
    collection = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(collection)
    return collection


def make_emission_material(name, color, strength=1.0):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    material.diffuse_color = (color[0], color[1], color[2], 1.0)

    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    emission = nodes.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value = (color[0], color[1], color[2], 1.0)
    emission.inputs["Strength"].default_value = strength
    links.new(emission.outputs[0], output.inputs[0])

    return material


def create_rig(name, collection):
    rig = bpy.data.objects.new(name, None)
    collection.objects.link(rig)
    return rig


def mulberry32(seed):
    state = seed & 0xFFFFFFFF

    def random():
        nonlocal state
        state = (state + 0x6D2B79F5) & 0xFFFFFFFF
        value = state
        value = ((value ^ (value >> 15)) * (value | 1)) & 0xFFFFFFFF
        value ^= (value + ((value ^ (value >> 7)) * (value | 61))) & 0xFFFFFFFF
        return ((value ^ (value >> 14)) & 0xFFFFFFFF) / 4294967296

    return random


def random_between(random, minimum, maximum):
    return minimum + (maximum - minimum) * random()


def is_inside_heart(x, y):
    return (x * x + y * y - 1) ** 3 - x * x * y ** 3 <= 0


def create_heart_points(geometry_config):
    random = mulberry32(geometry_config["seed"])
    points = []
    attempts = 0
    max_attempts = geometry_config["count"] * 180
    normalized_y_center = (HEART_Y_MIN + HEART_Y_MAX) / 2

    while len(points) < geometry_config["count"] and attempts < max_attempts:
        attempts += 1
        normalized_x = random_between(random, -HEART_X_LIMIT, HEART_X_LIMIT)
        normalized_y = random_between(random, HEART_Y_MIN, HEART_Y_MAX)

        if not is_inside_heart(normalized_x, normalized_y):
            continue

        center_bias = 1 - min(1, abs(normalized_x) / HEART_X_LIMIT)
        depth_jitter = random_between(random, -0.5, 0.5)
        x = normalized_x / HEART_X_LIMIT * geometry_config["width"] / 2
        y = (normalized_y - normalized_y_center) / (HEART_Y_MAX - HEART_Y_MIN) * geometry_config["height"]
        y += geometry_config["lobeLift"]
        depth = depth_jitter * geometry_config["depth"] * (0.62 + center_bias * 0.38)
        size = random_between(random, geometry_config["pointSizeMin"], geometry_config["pointSizeMax"])
        points.append((x, depth, y, size, center_bias))

    if len(points) != geometry_config["count"]:
        raise RuntimeError(f"Generated {len(points)} heart points after {attempts} attempts.")

    return points


def create_point_cloud_mesh(name, points, materials, collection, parent):
    vertices = []
    faces = []
    material_indices = []

    for point in points:
        x, y, z, size, center_bias = point
        base = len(vertices)
        vertices.extend([
            (x + size, y, z),
            (x - size, y, z),
            (x, y + size, z),
            (x, y - size, z),
            (x, y, z + size),
            (x, y, z - size),
        ])
        point_faces = [
            (base + 0, base + 2, base + 4),
            (base + 2, base + 1, base + 4),
            (base + 1, base + 3, base + 4),
            (base + 3, base + 0, base + 4),
            (base + 2, base + 0, base + 5),
            (base + 1, base + 2, base + 5),
            (base + 3, base + 1, base + 5),
            (base + 0, base + 3, base + 5),
        ]
        faces.extend(point_faces)
        material_indices.extend([1 if center_bias > 0.72 else 0] * len(point_faces))

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()

    obj = bpy.data.objects.new(name, mesh)
    obj.parent = parent
    for material in materials:
        obj.data.materials.append(material)
    for polygon, material_index in zip(obj.data.polygons, material_indices):
        polygon.material_index = material_index
    collection.objects.link(obj)
    return obj


def look_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def configure_camera(style):
    camera_data = bpy.data.cameras.new("orthographic-camera")
    camera = bpy.data.objects.new("orthographic-camera", camera_data)
    camera.location = (0, -style["cameraDistance"], 0.12)
    look_at(camera, (0, 0, style["cameraTargetZ"]))
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = style["orthographicScale"]
    bpy.context.scene.collection.objects.link(camera)
    bpy.context.scene.camera = camera


def configure_world(style):
    world = bpy.data.worlds.new("soft-pink-world")
    bpy.context.scene.world = world
    world.color = tuple(style["backgroundColor"])
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    if background is not None:
        background.inputs["Color"].default_value = (*style["backgroundColor"], 1.0)
        background.inputs["Strength"].default_value = style["worldStrength"]


def configure_render(profile, style, output_path):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.eevee.taa_render_samples = profile["samples"]
    scene.eevee.taa_samples = max(8, min(profile["samples"], 16))
    scene.frame_start = 1
    scene.frame_end = profile["fps"] * profile["seconds"]
    scene.render.fps = profile["fps"]
    scene.render.resolution_x = profile["width"]
    scene.render.resolution_y = profile["height"]
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False

    configure_world(style)

    try:
        scene.view_settings.view_transform = "Standard"
        scene.view_settings.look = "None"
        scene.view_settings.exposure = 0
        scene.view_settings.gamma = 1
    except TypeError:
        pass

    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "MEDIUM"
    scene.render.ffmpeg.ffmpeg_preset = "GOOD"
    scene.render.ffmpeg.gopsize = profile["fps"]
    scene.render.filepath = str(output_path)


def set_fcurve_interpolation(obj, interpolation):
    if obj.animation_data and obj.animation_data.action:
        for fcurve in obj.animation_data.action.fcurves:
            for keyframe in fcurve.keyframe_points:
                keyframe.interpolation = interpolation


def animate_rotation(rig, profile, style):
    scene = bpy.context.scene
    start_frame = scene.frame_start
    loop_frame = scene.frame_end + 1
    total_rotation_degrees = profile["seconds"] / style["rotationCycleSeconds"] * 360

    rig.rotation_euler = (0, 0, 0)
    rig.keyframe_insert(data_path="rotation_euler", frame=start_frame)
    rig.rotation_euler = (0, 0, math.radians(total_rotation_degrees))
    rig.keyframe_insert(data_path="rotation_euler", frame=loop_frame)
    set_fcurve_interpolation(rig, "LINEAR")


def main():
    args = parse_args()
    config = load_config()
    profile = config["profiles"][args.profile]
    geometry = config["geometry"]
    style = config["style"]
    project_root = Path(args.project_root)
    output_path = project_root / profile["output"]
    blend_path = project_root / "scene" / "pink-heart-point-cloud.blend"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    blend_path.parent.mkdir(parents=True, exist_ok=True)

    clear_scene()
    collection = make_collection("pink-heart-point-cloud")
    rotation_rig = create_rig("heart-rotation-rig", collection)
    heart_material = make_emission_material("pink-heart-emission", style["heartColor"], style["emissionStrength"])
    core_material = make_emission_material("pink-heart-core-emission", style["heartCoreColor"], style["emissionStrength"] * 1.08)
    points = create_heart_points(geometry)
    create_point_cloud_mesh("heart-point-cloud", points, [heart_material, core_material], collection, rotation_rig)
    configure_camera(style)
    configure_render(profile, style, output_path)
    animate_rotation(rotation_rig, profile, style)

    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

    if args.render:
        bpy.ops.render.render(animation=True)


if __name__ == "__main__":
    main()
