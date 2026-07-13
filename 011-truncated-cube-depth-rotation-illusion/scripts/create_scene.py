import argparse
import json
import math
import random
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def parse_args():
    parser = argparse.ArgumentParser(description="Create the truncated cube depth illusion.")
    parser.add_argument("--profile", choices=("preview", "final"), default="preview")
    parser.add_argument("--project-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--stills", action="store_true")
    script_args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return parser.parse_args(script_args)


def load_config():
    path = Path(__file__).resolve().parent / "truncated-cube-config.json"
    return json.loads(path.read_text(encoding="utf-8"))


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


def make_translucent_emission_material(name, color, strength, opacity):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    material.diffuse_color = (*color, opacity)
    material.surface_render_method = "BLENDED"
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    emission = nodes.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value = (*color, 1.0)
    emission.inputs["Strength"].default_value = strength
    transparent = nodes.new("ShaderNodeBsdfTransparent")
    mix = nodes.new("ShaderNodeMixShader")
    mix.inputs[0].default_value = opacity
    links.new(transparent.outputs[0], mix.inputs[1])
    links.new(emission.outputs[0], mix.inputs[2])
    links.new(mix.outputs[0], output.inputs[0])
    return material


def signs():
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                yield sx, sy, sz


def corner_triangle(sx, sy, sz, geometry):
    half = geometry["edgeLength"] / 2
    inset = half - geometry["cutDepth"]
    return (
        (sx * inset, sy * half, sz * half),
        (sx * half, sy * inset, sz * half),
        (sx * half, sy * half, sz * inset),
    )


def point_size(rng, geometry):
    return rng.uniform(geometry["pointSizeMin"], geometry["pointSizeMax"])


def face_coordinates(axis, sign, u, v, half):
    if axis == "x":
        return sign * half, u, v
    if axis == "y":
        return u, sign * half, v
    return u, v, sign * half


def create_large_face_points(geometry):
    rng = random.Random(geometry["seed"])
    points = []
    half = geometry["edgeLength"] / 2
    clip_limit = geometry["edgeLength"] - geometry["cutDepth"]
    target_count = geometry["largeFacePointCount"]
    trench_width = geometry["edgeTrenchWidth"]
    trench_reduction = geometry["edgeTrenchDensityReduction"]

    for axis in ("x", "y", "z"):
        for sign in (-1, 1):
            accepted = 0
            while accepted < target_count:
                u = rng.uniform(-half, half)
                v = rng.uniform(-half, half)
                if abs(u) + abs(v) > clip_limit:
                    continue
                boundary_distance = min(
                    half - abs(u),
                    half - abs(v),
                    (clip_limit - abs(u) - abs(v)) / math.sqrt(2),
                )
                if boundary_distance < trench_width and rng.random() < trench_reduction:
                    continue
                x, y, z = face_coordinates(axis, sign, u, v, half)
                points.append((x, y, z, point_size(rng, geometry)))
                accepted += 1
    return points


def create_triangle_points(geometry):
    rng = random.Random(geometry["seed"] + 9011)
    points = []
    per_face = geometry["trianglePointCount"]
    altitude = geometry["cutDepth"] * math.sqrt(3 / 2)
    trench_width = geometry["edgeTrenchWidth"]
    trench_reduction = geometry["edgeTrenchDensityReduction"]
    for sx, sy, sz in signs():
        a, b, c = corner_triangle(sx, sy, sz, geometry)
        accepted = 0
        while accepted < per_face:
            u = rng.random()
            v = rng.random()
            if u + v > 1:
                u = 1 - u
                v = 1 - v
            boundary_distance = min(1 - u - v, u, v) * altitude
            if boundary_distance < trench_width and rng.random() < trench_reduction:
                continue
            point = tuple(
                a[index] + u * (b[index] - a[index]) + v * (c[index] - a[index])
                for index in range(3)
            )
            points.append((*point, point_size(rng, geometry)))
            accepted += 1
    return points


def main_cube_edges(geometry):
    half = geometry["edgeLength"] / 2
    inset = half - geometry["cutDepth"]
    edges = []

    for fixed_axis in range(3):
        moving_axes = [axis for axis in range(3) if axis != fixed_axis]
        for first_sign in (-1, 1):
            for second_sign in (-1, 1):
                start = [0.0, 0.0, 0.0]
                end = [0.0, 0.0, 0.0]
                start[fixed_axis] = -inset
                end[fixed_axis] = inset
                start[moving_axes[0]] = end[moving_axes[0]] = first_sign * half
                start[moving_axes[1]] = end[moving_axes[1]] = second_sign * half
                edges.append((tuple(start), tuple(end)))
    return edges


def cut_face_edges(geometry):
    edges = []
    for sx, sy, sz in signs():
        triangle = corner_triangle(sx, sy, sz, geometry)
        edges.extend(
            (
                (triangle[0], triangle[1]),
                (triangle[1], triangle[2]),
                (triangle[2], triangle[0]),
            )
        )
    return edges


def create_main_edge_points(geometry):
    rng = random.Random(geometry["seed"] + 120)
    points = []
    slots = geometry["mainEdgeSlotCount"]
    keep_ratio = geometry["mainEdgeKeepRatio"]
    for start, end in main_cube_edges(geometry):
        for index in range(slots):
            if rng.random() > keep_ratio:
                continue
            t = (index + 0.5 + rng.uniform(-0.24, 0.24)) / slots
            point = tuple(
                start[axis] + t * (end[axis] - start[axis])
                for axis in range(3)
            )
            size = rng.uniform(
                geometry["mainEdgePointSizeMin"],
                geometry["mainEdgePointSizeMax"],
            )
            points.append((*point, size))
    return points


def create_main_edge_halo_points(main_points, geometry):
    stride = geometry["mainEdgeHaloStride"]
    multiplier = geometry["mainEdgeHaloSizeMultiplier"]
    return [
        (x, y, z, size * multiplier)
        for index, (x, y, z, size) in enumerate(main_points)
        if index % stride == 0
    ]


def create_cut_edge_star_points(geometry):
    rng = random.Random(geometry["seed"] + 240)
    ordinary = []
    stars = []
    count = geometry["cutEdgePointCount"]
    for start, end in cut_face_edges(geometry):
        for index in range(count):
            t = (index + 0.5 + rng.uniform(-0.3, 0.3)) / count
            point = tuple(
                start[axis] + t * (end[axis] - start[axis])
                for axis in range(3)
            )
            base_size = point_size(rng, geometry)
            if index == count // 2:
                stars.append(
                    (*point, base_size * geometry["cutEdgeStarSizeMultiplier"])
                )
                continue
            center_weight = 1 - abs(t * 2 - 1)
            ordinary.append((*point, base_size * (0.72 + 0.28 * center_weight)))
    return ordinary, stars


def rotate_x(point, angle):
    x, y, z, size = point
    return (
        x,
        y * math.cos(angle) - z * math.sin(angle),
        y * math.sin(angle) + z * math.cos(angle),
        size,
    )


def rotate_z(point, angle):
    x, y, z, size = point
    return (
        x * math.cos(angle) - y * math.sin(angle),
        x * math.sin(angle) + y * math.cos(angle),
        z,
        size,
    )


def present_points(points, geometry):
    tilt = math.radians(geometry["presentationTiltXDegrees"])
    turn = math.radians(geometry["presentationTurnZDegrees"])
    return [rotate_z(rotate_x(point, tilt), turn) for point in points]


def create_point_cloud_mesh(name, points, material, collection, parent):
    vertices = []
    faces = []
    for x, y, z, size in points:
        base = len(vertices)
        vertices.extend(
            [
                (x + size, y, z),
                (x - size, y, z),
                (x, y + size, z),
                (x, y - size, z),
                (x, y, z + size),
                (x, y, z - size),
            ]
        )
        faces.extend(
            [
                (base + 0, base + 2, base + 4),
                (base + 2, base + 1, base + 4),
                (base + 1, base + 3, base + 4),
                (base + 3, base + 0, base + 4),
                (base + 2, base + 0, base + 5),
                (base + 1, base + 2, base + 5),
                (base + 3, base + 1, base + 5),
                (base + 0, base + 3, base + 5),
            ]
        )

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    obj.parent = parent
    obj.data.materials.append(material)
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
    horizontal = distance * math.cos(elevation)
    camera.location = (
        horizontal * math.cos(azimuth),
        horizontal * math.sin(azimuth),
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
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "MEDIUM"
    scene.render.ffmpeg.ffmpeg_preset = "GOOD"
    scene.render.ffmpeg.gopsize = profile["fps"]
    scene.render.filepath = str(output_path)
    scene.render.film_transparent = False
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.color_depth = "8"
    scene.render.fps_base = 1.0
    scene.render.image_settings.compression = 15
    scene.frame_start = 1
    scene.frame_end = round(profile["fps"] * profile["seconds"])

    world = bpy.data.worlds.new("near-black-world")
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (*style["backgroundColor"], 1.0)
    background.inputs["Strength"].default_value = 0.02
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
    glare.quality = "HIGH"
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
    scene = bpy.context.scene
    loop_frame = scene.frame_end + 1
    turns = profile["seconds"] / style["rotationCycleSeconds"]
    rig.rotation_euler = (0, 0, 0)
    rig.keyframe_insert(data_path="rotation_euler", frame=scene.frame_start)
    rig.rotation_euler = (0, 0, turns * math.tau)
    rig.keyframe_insert(data_path="rotation_euler", frame=loop_frame)
    set_linear_interpolation(rig)


def animate_material_breath(material, profile, base, amount, cycle_seconds):
    emission = next(
        node for node in material.node_tree.nodes if node.bl_idname == "ShaderNodeEmission"
    )
    strength = emission.inputs["Strength"]
    fps = profile["fps"]
    cycle_count = round(profile["seconds"] / cycle_seconds)

    for cycle in range(cycle_count):
        start = 1 + round(cycle * cycle_seconds * fps)
        quarter = cycle_seconds * fps / 4
        for phase, factor in ((0, 1), (1, 1 + amount), (2, 1), (3, 1 - amount)):
            strength.default_value = base * factor
            strength.keyframe_insert("default_value", frame=start + round(phase * quarter))

    strength.default_value = base
    strength.keyframe_insert(
        "default_value", frame=1 + round(profile["seconds"] * fps)
    )
    if material.node_tree.animation_data and material.node_tree.animation_data.action:
        for fcurve in material.node_tree.animation_data.action.fcurves:
            for keyframe in fcurve.keyframe_points:
                keyframe.interpolation = "BEZIER"
                keyframe.handle_left_type = "AUTO_CLAMPED"
                keyframe.handle_right_type = "AUTO_CLAMPED"


def render_stills(project_root, profile, style):
    scene = bpy.context.scene
    scene.render.image_settings.file_format = "PNG"
    cycle_frames = round(profile["fps"] * style["rotationCycleSeconds"])
    frames = [1 + round(cycle_frames * phase / 8) for phase in range(9)]
    for index, frame in enumerate(frames, start=1):
        scene.frame_set(frame)
        scene.render.filepath = str(
            project_root / "output" / f"truncated-cube-preview-frame-{index:03d}.png"
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
    blend_path = project_root / "scene" / "truncated-cube-depth-rotation-illusion.blend"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    blend_path.parent.mkdir(parents=True, exist_ok=True)

    clear_scene()
    collection = make_collection("truncated-cube-depth-illusion")
    rotation_rig = bpy.data.objects.new("truncated-cube-rotation-rig", None)
    collection.objects.link(rotation_rig)
    material = make_emission_material(
        "shared-cool-white-points", style["pointColor"], style["emissionStrength"]
    )
    edge_material = make_emission_material(
        "broken-cool-lavender-edge-filament",
        style["mainEdgeColor"],
        style["mainEdgeEmissionStrength"],
    )
    halo_material = make_translucent_emission_material(
        "sparse-main-edge-halo",
        style["mainEdgeHaloColor"],
        style["mainEdgeHaloEmissionStrength"],
        style["mainEdgeHaloOpacity"],
    )
    cut_edge_material = make_emission_material(
        "cut-edge-fading-beads",
        style["cutEdgeColor"],
        style["cutEdgeEmissionStrength"],
    )
    cut_edge_star_material = make_emission_material(
        "cut-edge-center-stars",
        style["cutEdgeColor"],
        style["cutEdgeStarEmissionStrength"],
    )
    main_edge_points = create_main_edge_points(geometry)
    cut_edge_points, cut_edge_stars = create_cut_edge_star_points(geometry)

    point_groups = (
        ("large-octagonal-faces", create_large_face_points(geometry), material),
        ("triangular-cut-faces", create_triangle_points(geometry), material),
        ("cut-edge-fading-beads", cut_edge_points, cut_edge_material),
        ("cut-edge-center-stars", cut_edge_stars, cut_edge_star_material),
        ("broken-main-edge-filaments", main_edge_points, edge_material),
        (
            "sparse-main-edge-halo",
            create_main_edge_halo_points(main_edge_points, geometry),
            halo_material,
        ),
    )
    for name, points, point_material in point_groups:
        create_point_cloud_mesh(
            name,
            present_points(points, geometry),
            point_material,
            collection,
            rotation_rig,
        )

    configure_camera(style)
    configure_render(profile, style, output_path)
    animate_rotation(rotation_rig, profile, style)
    animate_material_breath(
        edge_material,
        profile,
        style["mainEdgeEmissionStrength"],
        style["edgeBreathAmount"],
        style["edgeBreathCycleSeconds"],
    )
    animate_material_breath(
        halo_material,
        profile,
        style["mainEdgeHaloEmissionStrength"],
        style["edgeBreathAmount"],
        style["edgeBreathCycleSeconds"],
    )
    for cut_material, base in (
        (cut_edge_material, style["cutEdgeEmissionStrength"]),
        (cut_edge_star_material, style["cutEdgeStarEmissionStrength"]),
    ):
        animate_material_breath(
            cut_material,
            profile,
            base,
            style["cutEdgeBreathAmount"],
            style["edgeBreathCycleSeconds"],
        )
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

    if args.stills:
        render_stills(project_root, profile, style)
    elif args.render:
        bpy.ops.render.render(animation=True)


if __name__ == "__main__":
    main()
