import argparse
import colorsys
import json
import math
import random
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def parse_args():
    parser = argparse.ArgumentParser(description="Create and optionally render the wireframe hourglass illusion.")
    parser.add_argument("--profile", choices=("preview", "final"), default="preview")
    parser.add_argument("--project-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--render", action="store_true")
    script_args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return parser.parse_args(script_args)


def load_config():
    config_path = Path(__file__).resolve().parent / "hourglass-config.json"
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
    material.blend_method = "OPAQUE"
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


def create_curve_line(name, start, end, radius, material, collection, parent):
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 1
    curve.bevel_depth = radius
    curve.bevel_resolution = 3

    spline = curve.splines.new("POLY")
    spline.points.add(1)
    spline.points[0].co = (start[0], start[1], start[2], 1.0)
    spline.points[1].co = (end[0], end[1], end[2], 1.0)

    obj = bpy.data.objects.new(name, curve)
    obj.parent = parent
    obj.data.materials.append(material)
    collection.objects.link(obj)
    return obj


def create_poly_curve(name, points, radius, material, collection, parent):
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 2
    curve.bevel_depth = radius
    curve.bevel_resolution = 2

    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for point, coordinates in zip(spline.points, points):
        point.co = (coordinates[0], coordinates[1], coordinates[2], 1.0)

    obj = bpy.data.objects.new(name, curve)
    obj.parent = parent
    obj.data.materials.append(material)
    collection.objects.link(obj)
    return obj


def create_rig(name, parent=None):
    rig = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(rig)
    rig.parent = parent
    return rig


def create_ring(sides, radius, z, phase_degrees):
    phase = math.radians(phase_degrees)
    return [
        (
            radius * math.cos(phase + index * math.tau / sides),
            radius * math.sin(phase + index * math.tau / sides),
            z,
        )
        for index in range(sides)
    ]


def create_pyramid_geometry(geometry_config, direction, phase_degrees):
    sides = geometry_config["sides"]
    base_z = geometry_config["pyramidHeight"] if direction == "up" else -geometry_config["pyramidHeight"]
    vertices = [(0, 0, 0)] + create_ring(
        sides,
        geometry_config["baseRadius"],
        base_z,
        phase_degrees,
    )
    edges = []

    def add_ring(start, label):
        for index in range(sides):
            edges.append((start + index, start + ((index + 1) % sides), label))

    add_ring(1, "base-rim")
    for index in range(sides):
        edges.append((0, 1 + index, "apex-to-base"))
    return vertices, edges


def create_wireframe(vertices, edges, style, collection, parent):
    core_material = make_emission_material("white-hot-line-core", (0.92, 0.96, 1.0), 2.8, 1.0)

    for index, (start_index, end_index, label) in enumerate(edges):
        hue = (0.53 + index * 0.047) % 1.0
        color = colorsys.hsv_to_rgb(hue, 0.42, 1.0)
        glow_material = make_emission_material(f"color-glow-{index:02d}", color, 1.55, 1.0)
        start = vertices[start_index]
        end = vertices[end_index]

        create_curve_line(
            f"{label}-{index:02d}-glow",
            start,
            end,
            style["lineGlowRadius"],
            glow_material,
            collection,
            parent,
        )
        create_curve_line(
            f"{label}-{index:02d}-core",
            start,
            end,
            style["lineCoreRadius"],
            core_material,
            collection,
            parent,
        )


def create_particle_mesh(name, centers, size_range, material, collection, parent):
    vertices = []
    faces = []

    for center in centers:
        size = center[3]
        x, y, z = center[:3]
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

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()

    obj = bpy.data.objects.new(name, mesh)
    obj.parent = parent
    obj.data.materials.append(material)
    collection.objects.link(obj)
    return obj


def create_particles(geometry_config, style, collection, top_parent, bottom_parent, bridge_parent, profile):
    height = geometry_config["pyramidHeight"]
    base_radius = geometry_config["baseRadius"]
    min_size = style["particleSizeMin"]
    max_size = style["particleSizeMax"]
    start_frame = 1
    midpoint_frame = start_frame + profile["fps"] * style["rotationCycleSeconds"]
    loop_frame = profile["fps"] * profile["seconds"] + 1

    materials = [
        make_emission_material("spiral-dust-cyan", (0.46, 0.95, 1.0), 3.6, 0.88),
        make_emission_material("spiral-dust-magenta", (1.0, 0.45, 0.95), 3.15, 0.82),
        make_emission_material("spiral-dust-gold", (1.0, 0.86, 0.42), 3.0, 0.8),
    ]
    trail_materials = [
        make_emission_material("spiral-trail-cyan", (0.35, 0.92, 1.0), 1.1, 0.5),
        make_emission_material("spiral-trail-magenta", (1.0, 0.35, 0.95), 0.95, 0.45),
    ]
    bridge_material = make_emission_material("apex-bridge-sparks", (0.74, 0.98, 1.0), 4.1, 0.9)
    bridge_line_material = make_emission_material("apex-bridge-dashes", (0.9, 0.78, 1.0), 2.0, 0.72)
    pulse_material = make_emission_material("apex-contact-pulse", (0.9, 0.98, 1.0), 0.45, 0.7)

    def animate_rotation(rig, turns, phase=0):
        rig.rotation_euler = (0, 0, math.radians(phase))
        rig.keyframe_insert(data_path="rotation_euler", frame=start_frame)
        rig.rotation_euler = (0, 0, math.radians(phase + 360 * turns))
        rig.keyframe_insert(data_path="rotation_euler", frame=loop_frame)
        set_fcurve_interpolation(rig, "LINEAR")

    def create_spiral_layer(name_prefix, parent, direction, layer_index, layer_count, seed_offset):
        local_rng = random.Random(style["seed"] + seed_offset)
        centers = []
        count = max(1, style["particleCount"] // (2 * layer_count))
        arm_count = style["spiralArmCount"]
        direction_sign = 1 if direction == "up" else -1
        layer_ratio = (layer_index + 1) / (layer_count + 1)
        radial_ratio = 0.2 + 0.46 * layer_ratio
        layer_phase = layer_index * math.tau / layer_count

        for index in range(count):
            progress = (index + local_rng.random() * 0.85) / count
            progress = min(0.94, max(0.08, progress))
            distance_from_apex = height * progress
            z = direction_sign * distance_from_apex
            radius_at_z = base_radius * progress
            arm = index % arm_count
            jitter = local_rng.uniform(-style["spiralJitterRadians"], style["spiralJitterRadians"])
            angle = (
                arm * math.tau / arm_count
                + progress * style["spiralTurns"] * math.tau * direction_sign
                + layer_phase
                + jitter
            )
            radial = radius_at_z * local_rng.uniform(radial_ratio * 0.84, radial_ratio * 1.12)
            x = math.cos(angle) * radial
            y = math.sin(angle) * radial
            size = local_rng.uniform(min_size, max_size)
            centers.append((x, y, z, size))

        layer_rig = create_rig(f"{name_prefix}-spiral-layer-{layer_index}", parent)
        create_particle_mesh(
            f"{name_prefix}-spiral-dust-{layer_index}",
            centers,
            (min_size, max_size),
            materials[layer_index % len(materials)],
            collection,
            layer_rig,
        )
        turns = style["spiralLocalTurns"] * (1 if layer_index % 2 == 0 else -0.72) * direction_sign
        animate_rotation(layer_rig, turns, phase=layer_index * 27)
        return layer_rig

    def create_spiral_trails(name_prefix, parent, direction, seed_offset):
        direction_sign = 1 if direction == "up" else -1
        trail_rig = create_rig(f"{name_prefix}-spiral-trails-rig", parent)
        local_rng = random.Random(style["seed"] + seed_offset)

        for arm in range(style["spiralArmCount"]):
            points = []
            arm_phase = arm * math.tau / style["spiralArmCount"] + local_rng.uniform(-0.12, 0.12)
            for index in range(style["spiralTrailSamples"]):
                progress = 0.12 + index / (style["spiralTrailSamples"] - 1) * 0.78
                distance_from_apex = height * progress
                radius_at_z = base_radius * progress
                angle = (
                    arm_phase
                    + progress * style["spiralTurns"] * math.tau * direction_sign
                    + 0.18 * math.sin(progress * math.tau * 2)
                )
                radial = radius_at_z * style["spiralTrailRadiusRatio"]
                points.append((
                    math.cos(angle) * radial,
                    math.sin(angle) * radial,
                    direction_sign * distance_from_apex,
                ))

            create_poly_curve(
                f"{name_prefix}-spiral-trail-{arm}",
                points,
                style["spiralTrailLineRadius"],
                trail_materials[arm % len(trail_materials)],
                collection,
                trail_rig,
            )

        animate_rotation(trail_rig, style["spiralTrailLocalTurns"] * direction_sign, phase=13)

    def build_local_particles(name_prefix, parent, direction, seed_offset):
        layer_count = len(materials)
        for layer_index in range(layer_count):
            create_spiral_layer(
                name_prefix,
                parent,
                direction,
                layer_index,
                layer_count,
                seed_offset + layer_index * 31,
            )
        create_spiral_trails(name_prefix, parent, direction, seed_offset + 97)

    def create_bridge_particles():
        bridge_rig = create_rig("apex-particle-bridge-rig", bridge_parent)
        centers = []
        rng = random.Random(style["seed"] + 701)

        for index in range(style["bridgeParticleCount"]):
            progress = index / max(1, style["bridgeParticleCount"] - 1)
            centered_z = progress - 0.5
            angle = progress * style["bridgeTwistTurns"] * math.tau + rng.uniform(-0.38, 0.38)
            radius = style["bridgeRadius"] * rng.uniform(0.18, 1.0)
            size = rng.uniform(min_size * 1.08, max_size * 1.26)
            centers.append((
                math.cos(angle) * radius,
                math.sin(angle) * radius,
                centered_z,
                size,
            ))

        create_particle_mesh(
            "apex-particle-bridge-sparks",
            centers,
            (min_size, max_size),
            bridge_material,
            collection,
            bridge_rig,
        )

        for index in range(style["bridgeSegmentCount"]):
            progress = (index + 0.5) / style["bridgeSegmentCount"]
            z_center = progress - 0.5
            half_length = rng.uniform(0.012, 0.026)
            angle = progress * style["bridgeTwistTurns"] * math.tau
            radius = style["bridgeRadius"] * rng.uniform(0.42, 0.94)
            x = math.cos(angle) * radius
            y = math.sin(angle) * radius
            create_curve_line(
                f"apex-bridge-dash-{index:02d}",
                (x, y, z_center - half_length),
                (x, y, z_center + half_length),
                style["bridgeLineRadius"],
                bridge_line_material,
                collection,
                bridge_rig,
            )

        for frame, length in (
            (start_frame, style["bridgeMinLength"]),
            (midpoint_frame, geometry_config["maxApexSeparation"]),
            (loop_frame, style["bridgeMinLength"]),
        ):
            bridge_rig.scale = (1, 1, length)
            bridge_rig.keyframe_insert(data_path="scale", frame=frame)

        bridge_rig.rotation_euler = (0, 0, 0)
        bridge_rig.keyframe_insert(data_path="rotation_euler", frame=start_frame)
        bridge_rig.rotation_euler = (0, 0, math.radians(360 * style["bridgeLocalTurns"]))
        bridge_rig.keyframe_insert(data_path="rotation_euler", frame=loop_frame)
        set_fcurve_interpolation(bridge_rig, "BEZIER")

    def create_contact_pulse():
        pulse_rig = create_rig("apex-contact-pulse-rig", bridge_parent)
        for index in range(style["pulseRingCount"]):
            radius = style["pulseRingRadius"] * (1 + index * 0.48)
            points = []
            for segment in range(style["pulseRingSamples"] + 1):
                angle = segment / style["pulseRingSamples"] * math.tau
                points.append((math.cos(angle) * radius, math.sin(angle) * radius, 0))

            create_poly_curve(
                f"apex-contact-pulse-ring-{index}",
                points,
                style["pulseRingLineRadius"],
                pulse_material,
                collection,
                pulse_rig,
            )

        for frame, scale in (
            (start_frame, 0.35),
            (start_frame + profile["fps"], 1.0),
            (midpoint_frame, 0.55),
            (loop_frame - profile["fps"], 0.7),
            (loop_frame, 0.35),
        ):
            pulse_rig.scale = (scale, scale, scale)
            pulse_rig.keyframe_insert(data_path="scale", frame=frame)

        animate_emission_strength(
            pulse_material,
            (
                (start_frame, style["pulseMaxStrength"]),
                (start_frame + profile["fps"], style["pulseMinStrength"]),
                (midpoint_frame, style["pulseMinStrength"] * 0.65),
                (loop_frame - profile["fps"], style["pulseMinStrength"]),
                (loop_frame, style["pulseMaxStrength"] * 1.08),
            ),
        )
        animate_rotation(pulse_rig, style["pulseLocalTurns"], phase=0)

    build_local_particles("top-pyramid", top_parent, "up", 11)
    build_local_particles("bottom-pyramid", bottom_parent, "down", 29)
    create_bridge_particles()
    create_contact_pulse()


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
    glare.threshold = 0.82
    glare.size = 3
    composite = tree.nodes.new("CompositorNodeComposite")
    tree.links.new(render_layers.outputs[0], glare.inputs[0])
    tree.links.new(glare.outputs[0], composite.inputs[0])


def set_fcurve_interpolation(obj, interpolation):
    if obj.animation_data and obj.animation_data.action:
        for fcurve in obj.animation_data.action.fcurves:
            for keyframe in fcurve.keyframe_points:
                keyframe.interpolation = interpolation


def animate_rig(rotation_rig, top_rig, bottom_rig, profile, geometry_config, style):
    scene = bpy.context.scene
    start_frame = scene.frame_start
    midpoint_frame = start_frame + profile["fps"] * style["rotationCycleSeconds"]
    loop_frame = scene.frame_end + 1
    total_rotation_degrees = profile["seconds"] / style["rotationCycleSeconds"] * 360
    max_gap = geometry_config["maxApexSeparation"]

    rotation_rig.rotation_euler = (0, 0, 0)
    rotation_rig.keyframe_insert(data_path="rotation_euler", frame=start_frame)
    rotation_rig.rotation_euler = (0, 0, math.radians(total_rotation_degrees))
    rotation_rig.keyframe_insert(data_path="rotation_euler", frame=loop_frame)
    set_fcurve_interpolation(rotation_rig, "LINEAR")

    for frame, gap in (
        (start_frame, 0),
        (midpoint_frame, max_gap),
        (loop_frame, 0),
    ):
        top_rig.location = (0, 0, gap / 2)
        bottom_rig.location = (0, 0, -gap / 2)
        top_rig.keyframe_insert(data_path="location", frame=frame)
        bottom_rig.keyframe_insert(data_path="location", frame=frame)

    set_fcurve_interpolation(top_rig, "BEZIER")
    set_fcurve_interpolation(bottom_rig, "BEZIER")


def main():
    args = parse_args()
    config = load_config()
    profile = config["profiles"][args.profile]
    style = config["style"]
    project_root = Path(args.project_root)
    output_path = project_root / profile["output"]
    blend_path = project_root / "scene" / "wireframe-hourglass-illusion.blend"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    blend_path.parent.mkdir(parents=True, exist_ok=True)

    clear_scene()
    collection = make_collection("wireframe-hourglass")
    rotation_rig = bpy.data.objects.new("hourglass-rotation-rig", None)
    top_rig = bpy.data.objects.new("top-inverted-square-pyramid-rig", None)
    bottom_rig = bpy.data.objects.new("bottom-upright-square-pyramid-rig", None)
    bpy.context.scene.collection.objects.link(rotation_rig)
    bpy.context.scene.collection.objects.link(top_rig)
    bpy.context.scene.collection.objects.link(bottom_rig)
    top_rig.parent = rotation_rig
    bottom_rig.parent = rotation_rig

    top_vertices, top_edges = create_pyramid_geometry(
        config["geometry"],
        "up",
        config["geometry"]["topPhaseDegrees"],
    )
    bottom_vertices, bottom_edges = create_pyramid_geometry(
        config["geometry"],
        "down",
        config["geometry"]["bottomPhaseDegrees"],
    )
    create_wireframe(top_vertices, top_edges, style, collection, top_rig)
    create_wireframe(bottom_vertices, bottom_edges, style, collection, bottom_rig)
    create_particles(config["geometry"], style, collection, top_rig, bottom_rig, rotation_rig, profile)
    configure_camera(style)
    configure_render(profile, output_path)
    animate_rig(rotation_rig, top_rig, bottom_rig, profile, config["geometry"], style)

    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

    if args.render:
        bpy.ops.render.render(animation=True)


if __name__ == "__main__":
    main()
