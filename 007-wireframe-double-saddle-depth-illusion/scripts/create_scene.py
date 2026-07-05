import argparse
import json
import math
import random
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def parse_args():
    parser = argparse.ArgumentParser(description="Create and optionally render the wireframe saddle depth illusion.")
    parser.add_argument("--profile", choices=("preview", "final"), default="preview")
    parser.add_argument("--project-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--render", action="store_true")
    script_args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return parser.parse_args(script_args)


def load_config():
    config_path = Path(__file__).resolve().parent / "saddle-config.json"
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


def make_emission_material(name, color, strength=1.0, alpha=1.0):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    material.diffuse_color = (color[0], color[1], color[2], alpha)
    material.blend_method = "BLEND" if alpha < 1 else "OPAQUE"
    material.show_transparent_back = True

    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    emission = nodes.new("ShaderNodeEmission")
    emission.name = "emission"
    emission.inputs["Color"].default_value = (color[0], color[1], color[2], alpha)
    emission.inputs["Strength"].default_value = strength
    links.new(emission.outputs[0], output.inputs[0])

    return material


def find_emission_node(material):
    for node in material.node_tree.nodes:
        if node.bl_idname == "ShaderNodeEmission":
            return node
    return None


def animate_emission_strength(material, keyframes):
    emission = find_emission_node(material)
    if emission is None:
        return

    strength_input = emission.inputs["Strength"]
    for frame, strength in keyframes:
        strength_input.default_value = strength
        strength_input.keyframe_insert(data_path="default_value", frame=frame)

    if material.node_tree.animation_data and material.node_tree.animation_data.action:
        for fcurve in material.node_tree.animation_data.action.fcurves:
            for keyframe in fcurve.keyframe_points:
                keyframe.interpolation = "BEZIER"


def create_rig(name, parent=None):
    rig = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(rig)
    rig.parent = parent
    return rig


def create_poly_curve(name, points, radius, material, collection, parent):
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 2
    curve.bevel_depth = radius
    curve.bevel_resolution = 3

    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for point, coordinates in zip(spline.points, points):
        point.co = (coordinates[0], coordinates[1], coordinates[2], 1.0)

    obj = bpy.data.objects.new(name, curve)
    obj.parent = parent
    obj.data.materials.append(material)
    collection.objects.link(obj)
    return obj


def create_curve_line(name, start, end, radius, material, collection, parent):
    create_poly_curve(name, (start, end), radius, material, collection, parent)


def saddle_point(geometry, x_ratio, y_ratio, z_offset=0):
    half = geometry["span"] / 2
    x = x_ratio * half
    y = y_ratio * half
    z = -geometry["saddleHeight"] * x_ratio * y_ratio + z_offset
    return (clean_zero(x), clean_zero(y), clean_zero(z))


def superellipse_boundary_point(angle, power=4.0):
    cosine = math.cos(angle)
    sine = math.sin(angle)
    x_ratio = math.copysign(abs(cosine) ** (2 / power), cosine)
    y_ratio = math.copysign(abs(sine) ** (2 / power), sine)
    return x_ratio, y_ratio


def clamp_ratio(value):
    return max(-0.98, min(0.98, value))


def constrain_to_superellipse(x_ratio, y_ratio, power=4.0, margin=0.985):
    total = abs(x_ratio) ** power + abs(y_ratio) ** power
    if total <= 1:
        return x_ratio, y_ratio

    scale = (1 / total) ** (1 / power) * margin
    return x_ratio * scale, y_ratio * scale


def create_saddle_vertices(geometry):
    grid_size = geometry["gridSize"]
    half = geometry["span"] / 2
    max_index = grid_size - 1
    rows = []

    for row in range(grid_size):
        y_ratio = 1 - row / max_index * 2
        y = y_ratio * half
        points = []
        for column in range(grid_size):
            x_ratio = column / max_index * 2 - 1
            x = x_ratio * half
            z = -geometry["saddleHeight"] * x_ratio * y_ratio
            points.append((clean_zero(x), clean_zero(y), clean_zero(z)))
        rows.append(points)

    return rows


def clean_zero(value):
    return 0 if abs(value) < 1e-12 else value


def create_saddle_wireframe(geometry, style, collection, parent):
    rows = create_saddle_vertices(geometry)
    grid_size = geometry["gridSize"]
    guide_material = make_emission_material(
        "saddle-faint-grid-guides",
        (0.35, 0.86, 1.0),
        max(0.05, style["gridGuideAlpha"] * 0.72),
        style["gridGuideAlpha"],
    )

    if style["gridGuideAlpha"] <= 0.05:
        return rows, (guide_material,)

    guide_indices = sorted(set((0, grid_size // 2, grid_size - 1)))
    for row_index in guide_indices:
        create_poly_curve(
            f"saddle-guide-row-{row_index:02d}",
            rows[row_index],
            style["lineCoreRadius"],
            guide_material,
            collection,
            parent,
        )

    for column in guide_indices:
        column_points = [rows[row][column] for row in range(grid_size)]
        create_poly_curve(
            f"saddle-guide-column-{column:02d}",
            column_points,
            style["lineCoreRadius"],
            guide_material,
            collection,
            parent,
        )

    return rows, (guide_material,)


def create_particle_mesh(name, centers, materials, collection, parent):
    vertices = []
    faces = []
    face_material_indices = []

    for center in centers:
        x, y, z, size, material_index = center
        base = len(vertices)
        vertices.extend([
            (x + size, y, z),
            (x - size, y, z),
            (x, y + size, z),
            (x, y - size, z),
            (x, y, z + size),
            (x, y, z - size),
        ])
        faces.extend([
            (base + 0, base + 2, base + 4),
            (base + 2, base + 1, base + 4),
            (base + 1, base + 3, base + 4),
            (base + 3, base + 0, base + 4),
            (base + 2, base + 0, base + 5),
            (base + 1, base + 2, base + 5),
            (base + 3, base + 1, base + 5),
            (base + 0, base + 3, base + 5),
        ])
        face_material_indices.extend([material_index] * 8)

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()

    obj = bpy.data.objects.new(name, mesh)
    obj.parent = parent
    for material in materials:
        obj.data.materials.append(material)
    for polygon, material_index in zip(obj.data.polygons, face_material_indices):
        polygon.material_index = material_index
    collection.objects.link(obj)
    return obj


def create_particle_materials(color_mode):
    if color_mode == "neutral-noise":
        palette = (
            ("saddle-particle-soft-cyan", (0.52, 0.92, 1.0), 1.45),
            ("saddle-particle-soft-mint", (0.58, 1.0, 0.76), 1.36),
            ("saddle-particle-soft-gold", (1.0, 0.84, 0.42), 1.4),
            ("saddle-particle-soft-lilac", (0.78, 0.64, 1.0), 1.34),
            ("saddle-particle-soft-blue", (0.46, 0.64, 1.0), 1.32),
            ("saddle-particle-soft-white", (0.86, 0.96, 1.0), 1.42),
        )
    else:
        palette = (
            ("saddle-particle-cyan", (0.20, 0.92, 1.0), 1.9),
            ("saddle-particle-green", (0.32, 1.0, 0.32), 1.72),
            ("saddle-particle-gold", (1.0, 0.88, 0.22), 1.84),
            ("saddle-particle-orange", (1.0, 0.44, 0.14), 1.68),
            ("saddle-particle-violet", (0.58, 0.34, 1.0), 1.55),
            ("saddle-particle-blue", (0.16, 0.42, 1.0), 1.5),
        )
    return [
        make_emission_material(name, color, strength, 0.88)
        for name, color, strength in palette
    ]


def color_bucket_for_point(x_ratio, y_ratio, z_ratio, layer_count, color_mode, dither=0):
    if color_mode == "neutral-noise":
        value = max(0, min(0.999999, dither))
        return int(value * layer_count)

    if color_mode == "height-radial":
        radial = min(1, (abs(x_ratio) ** 4 + abs(y_ratio) ** 4) ** 0.25)
        height = (z_ratio + 1) / 2
        value = max(0, min(1, 0.62 * height + 0.38 * radial + dither))
        return min(layer_count - 1, max(0, round(value * (layer_count - 1))))

    angle_ratio = (math.atan2(y_ratio, x_ratio) / math.tau + 1) % 1
    height_bias = (z_ratio + 1) * 0.12
    return int(((angle_ratio + height_bias + dither) % 1) * layer_count) % layer_count


def sample_inside_superellipse(rng, power=4.0):
    while True:
        x_ratio = rng.uniform(-1, 1)
        y_ratio = rng.uniform(-1, 1)
        if abs(x_ratio) ** power + abs(y_ratio) ** power <= 1:
            return x_ratio, y_ratio


def sample_edge_superellipse(rng):
    angle = rng.uniform(0, math.tau)
    x_ratio, y_ratio = superellipse_boundary_point(angle)
    inward = rng.uniform(0, 0.085)
    return x_ratio * (1 - inward), y_ratio * (1 - inward)


def create_saddle_particles(geometry, style, collection, parent, seed_offset=0):
    rng = random.Random(style["seed"] + seed_offset)
    centers = []
    materials = create_particle_materials(style["colorMode"])

    for _ in range(style["particleCount"]):
        if rng.random() < style["edgeParticleBoost"]:
            x_ratio, y_ratio = sample_edge_superellipse(rng)
            size_boost = 1.22
        else:
            x_ratio, y_ratio = sample_inside_superellipse(rng)
            size_boost = 1.0

        z_offset = rng.uniform(-style["particleJitter"], style["particleJitter"])
        x, y, z = saddle_point(geometry, x_ratio, y_ratio, z_offset)
        z_ratio = max(-1, min(1, z / max(geometry["saddleHeight"], 0.001)))
        size = rng.uniform(style["particleSizeMin"], style["particleSizeMax"]) * size_boost
        material_index = color_bucket_for_point(
            x_ratio,
            y_ratio,
            z_ratio,
            len(materials),
            style["colorMode"],
            rng.random() if style["colorMode"] == "neutral-noise" else rng.uniform(-0.075, 0.075),
        )
        centers.append((x, y, z, size, material_index))

    particle_rig = create_rig("saddle-depth-dust-rig", parent)
    create_particle_mesh("saddle-depth-dust", centers, materials, collection, particle_rig)
    return particle_rig


def create_highlight_curves(geometry, style, collection, parent):
    highlight_rig = create_rig("saddle-highlight-curves-rig", parent)
    outline_glow = make_emission_material("saddle-outline-neutral-glow", (0.74, 0.96, 1.0), 1.35, 0.9)
    outline_core = make_emission_material("saddle-outline-neutral-core", (0.92, 1.0, 0.94), 1.08, 0.94)
    ridge_materials = (
        make_emission_material("saddle-ridge-gold", (1.0, 0.82, 0.20), 2.15, 0.95),
        make_emission_material("saddle-ridge-cyan", (0.28, 0.95, 1.0), 1.95, 0.92),
        make_emission_material("saddle-ridge-violet", (0.62, 0.42, 1.0), 1.35, 0.82),
        make_emission_material("saddle-ridge-green", (0.44, 1.0, 0.42), 1.2, 0.78),
        make_emission_material("saddle-ridge-orange", (1.0, 0.45, 0.15), 1.38, 0.82),
    )

    outline_points = []
    for index in range(style["outlineSampleCount"] + 1):
        angle = index / style["outlineSampleCount"] * math.tau
        x_ratio, y_ratio = superellipse_boundary_point(angle)
        outline_points.append(saddle_point(geometry, x_ratio, y_ratio, 0.006))

    create_poly_curve(
        "saddle-outline-glow",
        outline_points,
        style["outlineGlowRadius"],
        outline_glow,
        collection,
        highlight_rig,
    )
    create_poly_curve(
        "saddle-outline-core",
        outline_points,
        style["outlineCoreRadius"],
        outline_core,
        collection,
        highlight_rig,
    )

    def make_curve_points(kind):
        points = []
        samples = style["ridgeSampleCount"]
        for index in range(samples):
            t = -0.96 + index / (samples - 1) * 1.92
            bend = math.sin((t + 1) * math.pi)
            if kind == "high-diagonal":
                x_ratio, y_ratio = t, clamp_ratio(-t + 0.24 * bend)
            elif kind == "low-diagonal":
                x_ratio, y_ratio = t, clamp_ratio(t - 0.24 * bend)
            elif kind == "center-x":
                x_ratio, y_ratio = t, 0
            elif kind == "center-y":
                x_ratio, y_ratio = 0, t
            else:
                x_ratio = t
                y_ratio = 0.42 * math.sin((t + 1) * math.pi)
            x_ratio, y_ratio = constrain_to_superellipse(x_ratio, y_ratio)
            points.append(saddle_point(geometry, x_ratio, y_ratio, 0.012))
        return points

    curve_kinds = ("high-diagonal", "low-diagonal", "s-curve", "center-x", "center-y")
    for index, kind in enumerate(curve_kinds[:style["ridgeCurveCount"]]):
        create_poly_curve(
            f"saddle-{kind}-glow",
            make_curve_points(kind),
            style["ridgeGlowRadius"] if index < 2 else style["lineGlowRadius"],
            ridge_materials[index],
            collection,
            highlight_rig,
        )
        create_poly_curve(
            f"saddle-{kind}-core",
            make_curve_points(kind),
            style["ridgeCoreRadius"] if index < 2 else style["lineCoreRadius"],
            ridge_materials[index],
            collection,
            highlight_rig,
        )

    return highlight_rig, ridge_materials[0]


def create_center_pulse(style, collection, parent):
    pulse_alpha = style.get("centerPulseAlpha", 0.46)
    pulse_material = make_emission_material("saddle-center-pulse", (0.9, 0.98, 1.0), 0.22 * pulse_alpha, pulse_alpha)
    pulse_rig = create_rig("saddle-center-pulse-rig", parent)

    if pulse_alpha <= 0:
        return pulse_rig, pulse_material

    for ring_index, radius in enumerate((0.13, 0.21)):
        points = []
        for index in range(65):
            angle = index / 64 * math.tau
            points.append((math.cos(angle) * radius, math.sin(angle) * radius, 0))

        create_poly_curve(
            f"saddle-center-pulse-ring-{ring_index}",
            points,
            0.00115,
            pulse_material,
            collection,
            pulse_rig,
        )

    return pulse_rig, pulse_material


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
    camera_data.type = style["cameraProjection"]
    camera_data.ortho_scale = style["orthographicScale"]
    bpy.context.scene.collection.objects.link(camera)
    bpy.context.scene.camera = camera


def configure_render(profile, output_path):
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
    scene.world = bpy.data.worlds.new("black-world")
    scene.world.color = (0, 0, 0)

    try:
        scene.view_settings.view_transform = "Standard"
        scene.view_settings.look = "Medium High Contrast"
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

    scene.use_nodes = True
    tree = scene.node_tree
    tree.nodes.clear()
    render_layers = tree.nodes.new("CompositorNodeRLayers")
    glare = tree.nodes.new("CompositorNodeGlare")
    glare.glare_type = "FOG_GLOW"
    glare.quality = "MEDIUM"
    glare.threshold = 0.8
    glare.size = 3
    composite = tree.nodes.new("CompositorNodeComposite")
    tree.links.new(render_layers.outputs[0], glare.inputs[0])
    tree.links.new(glare.outputs[0], composite.inputs[0])


def set_fcurve_interpolation(obj, interpolation):
    if obj.animation_data and obj.animation_data.action:
        for fcurve in obj.animation_data.action.fcurves:
            for keyframe in fcurve.keyframe_points:
                keyframe.interpolation = interpolation


def animate_scene(rotation_rig, surface_rigs, pulse_rigs, pulse_materials, profile, style):
    scene = bpy.context.scene
    start_frame = scene.frame_start
    quarter_frame = start_frame + profile["fps"] * style["rotationCycleSeconds"] / 2
    midpoint_frame = start_frame + profile["fps"] * style["rotationCycleSeconds"]
    three_quarter_frame = start_frame + profile["fps"] * style["rotationCycleSeconds"] * 1.5
    loop_frame = scene.frame_end + 1
    total_rotation_degrees = profile["seconds"] / style["rotationCycleSeconds"] * 360

    rotation_rig.rotation_euler = (0, 0, 0)
    rotation_rig.keyframe_insert(data_path="rotation_euler", frame=start_frame)
    rotation_rig.rotation_euler = (0, 0, math.radians(total_rotation_degrees))
    rotation_rig.keyframe_insert(data_path="rotation_euler", frame=loop_frame)
    set_fcurve_interpolation(rotation_rig, "LINEAR")

    for surface_rig in surface_rigs:
        for frame, degrees in (
            (start_frame, 0),
            (quarter_frame, style["rockDegrees"]),
            (midpoint_frame, 0),
            (three_quarter_frame, -style["rockDegrees"]),
            (loop_frame, 0),
        ):
            surface_rig.rotation_euler = (math.radians(degrees), 0, 0)
            surface_rig.keyframe_insert(data_path="rotation_euler", frame=frame)

        set_fcurve_interpolation(surface_rig, "BEZIER")

    for pulse_rig in pulse_rigs:
        for frame, scale in (
            (start_frame, 0.55),
            (quarter_frame, 1.05),
            (midpoint_frame, 0.66),
            (three_quarter_frame, 1.0),
            (loop_frame, 0.55),
        ):
            pulse_rig.scale = (scale, scale, scale)
            pulse_rig.keyframe_insert(data_path="scale", frame=frame)

        set_fcurve_interpolation(pulse_rig, "BEZIER")

    for pulse_material in pulse_materials:
        animate_emission_strength(
            pulse_material,
            (
                (start_frame, style["edgePulseStrength"]),
                (quarter_frame, 0.38),
                (midpoint_frame, 0.78),
                (three_quarter_frame, 0.38),
                (loop_frame, style["edgePulseStrength"]),
            ),
        )


def create_model_instance(instance, geometry, style, collection, rotation_rig):
    instance_rig = create_rig(f"{instance['name']}-instance-rig", rotation_rig)
    instance_rig.location = (0, 0, instance["zOffset"])
    instance_rig.rotation_euler = (
        math.radians(instance["rotationXDegrees"]),
        math.radians(instance.get("rotationYDegrees", 0)),
        math.radians(instance.get("rotationZDegrees", 0)),
    )

    surface_rig = create_rig(f"{instance['name']}-surface-rig", instance_rig)
    create_saddle_wireframe(geometry, style, collection, surface_rig)
    create_saddle_particles(
        geometry,
        style,
        collection,
        surface_rig,
        instance.get("seedOffset", 0),
    )
    create_highlight_curves(geometry, style, collection, surface_rig)
    pulse_rig, pulse_material = create_center_pulse(style, collection, surface_rig)
    return surface_rig, pulse_rig, pulse_material


def main():
    args = parse_args()
    config = load_config()
    profile = config["profiles"][args.profile]
    geometry = config["geometry"]
    style = config["style"]
    composition = config["composition"]
    project_root = Path(args.project_root)
    output_path = project_root / profile["output"]
    blend_path = project_root / "scene" / "wireframe-double-saddle-depth-illusion.blend"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    blend_path.parent.mkdir(parents=True, exist_ok=True)

    clear_scene()
    collection = make_collection("wireframe-double-saddle-depth-illusion")
    rotation_rig = create_rig("saddle-rotation-rig")
    surface_rigs = []
    pulse_rigs = []
    pulse_materials = []

    for instance in composition["modelInstances"]:
        surface_rig, pulse_rig, pulse_material = create_model_instance(
            instance,
            geometry,
            style,
            collection,
            rotation_rig,
        )
        surface_rigs.append(surface_rig)
        pulse_rigs.append(pulse_rig)
        pulse_materials.append(pulse_material)

    configure_camera(style)
    configure_render(profile, output_path)
    animate_scene(rotation_rig, surface_rigs, pulse_rigs, pulse_materials, profile, style)

    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

    if args.render:
        bpy.ops.render.render(animation=True)


if __name__ == "__main__":
    main()
