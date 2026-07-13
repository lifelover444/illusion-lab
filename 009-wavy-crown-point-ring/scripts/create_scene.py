import argparse
import json
import math
import random
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def parse_args():
    parser = argparse.ArgumentParser(description="Create the wavy crown point ring illusion.")
    parser.add_argument("--profile", choices=("preview", "final"), default="preview")
    parser.add_argument("--project-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--stills", action="store_true")
    script_args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return parser.parse_args(script_args)


def load_config():
    config_path = Path(__file__).resolve().parent / "wavy-crown-config.json"
    return json.loads(config_path.read_text(encoding="utf-8"))


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for data_blocks in (
        bpy.data.meshes,
        bpy.data.materials,
        bpy.data.cameras,
        bpy.data.lights,
        bpy.data.collections,
    ):
        for item in list(data_blocks):
            if item.users == 0:
                data_blocks.remove(item)


def make_collection(name):
    collection = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(collection)
    return collection


def make_emission_material(name, color, strength):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    material.diffuse_color = (*color, 1.0)
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    emission = nodes.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value = (*color, 1.0)
    emission.inputs["Strength"].default_value = strength
    links.new(emission.outputs[0], output.inputs[0])
    return material


def create_wavy_crown_points(geometry):
    rng = random.Random(geometry["seed"])
    points = []
    phase = math.radians(geometry["wavePhaseDegrees"])
    major_segments = geometry["majorSegments"]
    radial_segments = geometry["radialSegments"]

    for major_index in range(major_segments):
        for radial_index in range(radial_segments):
            stagger = 0.5 if radial_index % 2 else 0.0
            major_jitter = rng.uniform(-0.28, 0.28)
            radial_jitter = rng.uniform(-0.30, 0.30)
            major_angle = (
                major_index + stagger + major_jitter
            ) / major_segments * math.tau
            radial_ratio = (
                radial_index + 0.5 + radial_jitter
            ) / radial_segments
            radial_offset = (
                radial_ratio * 2 - 1
            ) * geometry["bandHalfWidth"]
            radial_distance = geometry["majorRadius"] + radial_offset
            x = radial_distance * math.cos(major_angle)
            y = radial_distance * math.sin(major_angle)
            z = (
                geometry["waveHeight"]
                * math.cos(geometry["waveCount"] * major_angle + phase)
                + rng.uniform(
                    -geometry["bandHalfThickness"],
                    geometry["bandHalfThickness"],
                )
            )
            size = rng.uniform(geometry["pointSizeMin"], geometry["pointSizeMax"])
            points.append((x, y, z, size))
    return points


def create_point_cloud_mesh(name, points, materials, collection, parent):
    vertices = []
    faces = []
    for x, y, z, size in points:
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

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    obj.parent = parent
    obj.data.materials.append(materials[0])
    collection.objects.link(obj)
    return obj


def look_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def configure_camera(style):
    camera_data = bpy.data.cameras.new("orthographic-camera")
    camera = bpy.data.objects.new("orthographic-camera", camera_data)
    azimuth = math.radians(style["cameraAzimuthDegrees"])
    elevation = math.radians(style["cameraElevationDegrees"])
    distance = style["cameraDistance"]
    horizontal_distance = distance * math.cos(elevation)
    camera.location = (
        horizontal_distance * math.cos(azimuth),
        horizontal_distance * math.sin(azimuth),
        distance * math.sin(elevation),
    )
    look_at(camera, (0, 0, style["cameraTargetZ"]))
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = style["orthographicScale"]
    bpy.context.scene.collection.objects.link(camera)
    bpy.context.scene.camera = camera


def configure_render(profile, style, output_path):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = profile["width"]
    scene.render.resolution_y = profile["height"]
    scene.render.resolution_percentage = 100
    scene.render.fps = profile["fps"]
    scene.frame_start = 1
    scene.frame_end = round(profile["fps"] * profile["seconds"])
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "MEDIUM"
    scene.render.ffmpeg.ffmpeg_preset = "GOOD"
    scene.render.ffmpeg.gopsize = profile["fps"]
    scene.render.filepath = str(output_path)

    world = bpy.data.worlds.new("black-world")
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (*style["backgroundColor"], 1.0)
    background.inputs["Strength"].default_value = 0.0
    scene.world = world

    try:
        scene.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        scene.view_settings.look = "Medium High Contrast"
    scene.use_nodes = True
    tree = scene.node_tree
    tree.nodes.clear()
    render_layers = tree.nodes.new("CompositorNodeRLayers")
    glare = tree.nodes.new("CompositorNodeGlare")
    glare.glare_type = "FOG_GLOW"
    glare.quality = "MEDIUM"
    glare.threshold = style["glowThreshold"]
    glare.size = style["glowSize"]
    composite = tree.nodes.new("CompositorNodeComposite")
    tree.links.new(render_layers.outputs[0], glare.inputs[0])
    tree.links.new(glare.outputs[0], composite.inputs[0])


def set_linear_interpolation(obj):
    if obj.animation_data and obj.animation_data.action:
        for fcurve in obj.animation_data.action.fcurves:
            for keyframe in fcurve.keyframe_points:
                keyframe.interpolation = "LINEAR"


def animate_rotation(rig, profile, style):
    start_frame = bpy.context.scene.frame_start
    loop_frame = bpy.context.scene.frame_end + 1
    turns = profile["seconds"] / style["rotationCycleSeconds"]
    rig.rotation_euler = (0, 0, 0)
    rig.keyframe_insert(data_path="rotation_euler", frame=start_frame)
    rig.rotation_euler = (0, 0, turns * math.tau)
    rig.keyframe_insert(data_path="rotation_euler", frame=loop_frame)
    set_linear_interpolation(rig)


def render_stills(project_root, profile, style):
    scene = bpy.context.scene
    scene.render.image_settings.file_format = "PNG"
    cycle_frames = round(profile["fps"] * style["rotationCycleSeconds"])
    frames = [1 + round(cycle_frames * phase / 4) for phase in range(5)]
    for index, frame in enumerate(frames, start=1):
        scene.frame_set(frame)
        scene.render.filepath = str(
            project_root / "output" / f"wavy-crown-preview-frame-{index:03d}.png"
        )
        bpy.ops.render.render(write_still=True)


def main():
    args = parse_args()
    config = load_config()
    profile = config["profiles"][args.profile]
    geometry = config["geometry"]
    style = config["style"]
    project_root = Path(args.project_root)
    output_path = project_root / profile["output"]
    blend_path = project_root / "scene" / "wavy-crown-point-ring.blend"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    blend_path.parent.mkdir(parents=True, exist_ok=True)

    clear_scene()
    collection = make_collection("wavy-crown-point-ring")
    rotation_rig = bpy.data.objects.new("wavy-crown-rotation-rig", None)
    collection.objects.link(rotation_rig)
    point_material = make_emission_material(
        "cool-white-points", style["pointColor"], style["emissionStrength"]
    )
    points = create_wavy_crown_points(geometry)
    create_point_cloud_mesh(
        "wavy-crown-point-cloud",
        points,
        [point_material],
        collection,
        rotation_rig,
    )
    configure_camera(style)
    configure_render(profile, style, output_path)
    animate_rotation(rotation_rig, profile, style)
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

    if args.stills:
        render_stills(project_root, profile, style)
    elif args.render:
        bpy.ops.render.render(animation=True)


if __name__ == "__main__":
    main()
