import argparse
import json
import math
import random
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def parse_args():
    parser = argparse.ArgumentParser(description="Create and optionally render the wireframe hyperboloid depth rotation illusion.")
    parser.add_argument("--profile", choices=("preview", "final"), default="preview")
    parser.add_argument("--project-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--render", action="store_true")
    script_args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return parser.parse_args(script_args)


def load_config():
    config_path = Path(__file__).resolve().parent / "hyperboloid-config.json"
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
    material.blend_method = "BLEND"
    material.show_transparent_back = True

    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    emission = nodes.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value = (color[0], color[1], color[2], alpha)
    emission.inputs["Strength"].default_value = strength
    links.new(emission.outputs[0], output.inputs[0])

    return material


def create_rig(name, parent=None):
    rig = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(rig)
    rig.parent = parent
    return rig


def create_poly_curve(name, points, radius, material, collection, parent, bevel_resolution=2):
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 2
    curve.bevel_depth = radius
    curve.bevel_resolution = bevel_resolution

    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for point, coordinates in zip(spline.points, points):
        point.co = (coordinates[0], coordinates[1], coordinates[2], 1.0)

    obj = bpy.data.objects.new(name, curve)
    obj.parent = parent
    obj.data.materials.append(material)
    collection.objects.link(obj)
    return obj


def degrees_to_radians(degrees):
    return degrees * math.pi / 180


def hyperboloid_point(geometry, theta, ratio, jitter=0, twist_sign=1):
    ring_radius = geometry["ringRadius"]
    height = geometry["height"]
    twist = degrees_to_radians(geometry["twistDegrees"])
    bottom = (
        ring_radius * math.cos(theta),
        ring_radius * math.sin(theta),
        -height / 2,
    )
    top_theta = theta + twist * twist_sign
    top = (
        ring_radius * math.cos(top_theta),
        ring_radius * math.sin(top_theta),
        height / 2,
    )
    x = bottom[0] + (top[0] - bottom[0]) * ratio
    y = bottom[1] + (top[1] - bottom[1]) * ratio
    z = bottom[2] + (top[2] - bottom[2]) * ratio

    if jitter:
        radial_length = max(0.0001, math.hypot(x, y))
        x += x / radial_length * jitter
        y += y / radial_length * jitter

    return x, y, z


def create_particle_materials(color_mode):
    if color_mode == "neutral-noise":
        palette = (
            ("hyperboloid-particle-soft-cyan", (0.52, 0.92, 1.0), 1.45),
            ("hyperboloid-particle-soft-mint", (0.58, 1.0, 0.76), 1.34),
            ("hyperboloid-particle-soft-gold", (1.0, 0.84, 0.42), 1.38),
            ("hyperboloid-particle-soft-lilac", (0.78, 0.64, 1.0), 1.32),
            ("hyperboloid-particle-soft-blue", (0.46, 0.64, 1.0), 1.3),
            ("hyperboloid-particle-soft-white", (0.88, 0.98, 1.0), 1.48),
        )
    else:
        palette = (
            ("hyperboloid-particle-cyan", (0.20, 0.92, 1.0), 1.9),
            ("hyperboloid-particle-green", (0.32, 1.0, 0.32), 1.72),
            ("hyperboloid-particle-gold", (1.0, 0.88, 0.22), 1.84),
            ("hyperboloid-particle-orange", (1.0, 0.44, 0.14), 1.68),
            ("hyperboloid-particle-violet", (0.58, 0.34, 1.0), 1.55),
            ("hyperboloid-particle-blue", (0.16, 0.42, 1.0), 1.5),
        )

    return [
        make_emission_material(name, color, strength, 0.88)
        for name, color, strength in palette
    ]


def create_heart_particle_materials():
    palette = (
        ("hyperboloid-heart-particle-rose", (1.0, 0.34, 0.62), 1.24),
        ("hyperboloid-heart-particle-soft-pink", (1.0, 0.54, 0.78), 1.16),
        ("hyperboloid-heart-particle-pale-pink", (1.0, 0.74, 0.88), 1.08),
    )

    return [
        make_emission_material(name, color, strength, 0.82)
        for name, color, strength in palette
    ]


def create_ring_particle_materials():
    palette = (
        ("hyperboloid-ring-particle-warm-white", (1.0, 0.92, 0.96), 0.96),
        ("hyperboloid-ring-particle-pale-rose", (1.0, 0.70, 0.84), 0.86),
        ("hyperboloid-ring-particle-soft-blush", (1.0, 0.54, 0.74), 0.74),
        ("hyperboloid-ring-particle-dim-pink", (0.82, 0.42, 0.58), 0.58),
    )

    return [
        make_emission_material(name, color, strength, 0.78)
        for name, color, strength in palette
    ]


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


def create_hyperboloid_particles(geometry, style, collection, parent):
    rng = random.Random(style["seed"])
    centers = []
    materials = create_particle_materials(style["colorMode"])

    for _ in range(style["particleCount"]):
        theta = rng.random() * math.tau
        if rng.random() < style["edgeParticleBoost"]:
            ratio = rng.choice((rng.uniform(0, 0.065), rng.uniform(0.935, 1)))
            size_boost = 1.18
        else:
            ratio = rng.random()
            size_boost = 1.0

        jitter = rng.uniform(-style["particleJitter"], style["particleJitter"])
        x, y, z = hyperboloid_point(geometry, theta, ratio, jitter)
        material_index = int(rng.random() * len(materials)) % len(materials)
        size = rng.uniform(style["particleSizeMin"], style["particleSizeMax"]) * size_boost
        centers.append((x, y, z, size, material_index))

    particle_rig = create_rig("hyperboloid-depth-dust-rig", parent)
    create_particle_mesh("hyperboloid-depth-dust", centers, materials, collection, particle_rig)
    return particle_rig


def create_hyperboloid_guide_particles(geometry, style, collection, parent):
    if style.get("continuousSideRibs", True):
        return None

    rng = random.Random(style["seed"] + 2718)
    centers = []
    materials = create_particle_materials(style["colorMode"])
    guide_count = style["guideRibCount"]
    point_count = style["guideRibParticleCount"]
    size_scale = style["guideRibParticleSizeScale"]

    for family_index, family in enumerate(style["guideRibFamilies"]):
        twist_sign = 1 if family == "positive" else -1
        family_offset = family_index / max(1, len(style["guideRibFamilies"])) * math.tau / guide_count
        for rib_index in range(guide_count):
            theta = rib_index / guide_count * math.tau + family_offset
            for point_index in range(point_count):
                ratio = 0.055 + point_index / max(1, point_count - 1) * 0.89
                jitter = rng.uniform(-style["guideRibJitter"], style["guideRibJitter"])
                x, y, z = hyperboloid_point(geometry, theta, ratio, jitter, twist_sign)
                material_index = int(rng.random() * len(materials)) % len(materials)
                base_size = rng.uniform(style["particleSizeMin"], style["particleSizeMax"])
                centers.append((x, y, z, base_size * size_scale, material_index))

    guide_rig = create_rig("hyperboloid-dotted-guide-rib-rig", parent)
    create_particle_mesh("hyperboloid-dotted-guide-ribs", centers, materials, collection, guide_rig)
    return guide_rig


def heart_outline_point(t):
    x = 16 * math.sin(t) ** 3 / 17
    y = (
        13 * math.cos(t)
        - 5 * math.cos(2 * t)
        - 2 * math.cos(3 * t)
        - math.cos(4 * t)
    ) / 17
    return x, y


def is_inside_heart(x, y):
    y = y + 0.08
    return (x * x + y * y - 1) ** 3 - x * x * y ** 3 <= 0


def heart_surface_point(geometry, style, theta_center, x, y, rng):
    ratio = style["heartCenterRatio"] + y * style["heartVerticalSpan"]
    ratio = min(0.86, max(0.18, ratio))
    theta = theta_center + x * style["heartAngularSpan"]
    jitter = rng.uniform(-style["heartJitter"], style["heartJitter"])
    return hyperboloid_point(geometry, theta, ratio, jitter)


def create_hyperboloid_heart_particles(geometry, style, collection, parent):
    if not style.get("heartPattern", False):
        return None

    rng = random.Random(style["seed"] + 4311)
    centers = []
    materials = create_heart_particle_materials()
    base_theta = math.radians(style["heartCenterThetaDegrees"])
    pair_count = style["heartPairCount"]
    outline_count = style["heartOutlineParticleCount"]
    fill_count = style["heartFillParticleCount"]
    size_scale = style["heartParticleSizeScale"]

    for pair_index in range(pair_count):
        theta_center = base_theta + pair_index * math.tau / pair_count

        for point_index in range(outline_count):
            t = point_index / outline_count * math.tau
            x, y = heart_outline_point(t)
            px, py, pz = heart_surface_point(geometry, style, theta_center, x, y, rng)
            material_index = int(rng.random() * len(materials)) % len(materials)
            base_size = rng.uniform(style["particleSizeMin"], style["particleSizeMax"])
            centers.append((px, py, pz, base_size * size_scale * 1.18, material_index))

        accepted = 0
        attempts = 0
        while accepted < fill_count and attempts < fill_count * 20:
            attempts += 1
            x = rng.uniform(-0.92, 0.92)
            y = rng.uniform(-0.78, 0.9)
            if not is_inside_heart(x, y):
                continue

            px, py, pz = heart_surface_point(geometry, style, theta_center, x, y, rng)
            material_index = int(rng.random() * len(materials)) % len(materials)
            base_size = rng.uniform(style["particleSizeMin"], style["particleSizeMax"])
            centers.append((px, py, pz, base_size * size_scale, material_index))
            accepted += 1

    heart_rig = create_rig("hyperboloid-pink-heart-pattern-rig", parent)
    create_particle_mesh("hyperboloid-pink-heart-pattern", centers, materials, collection, heart_rig)
    return heart_rig


def create_ring_curve(name, geometry, ratio, style, collection, parent, core_material, glow_material, alpha_scale=1):
    points = [
        hyperboloid_point(geometry, index / 160 * math.tau, ratio, 0)
        for index in range(161)
    ]
    create_poly_curve(
        f"{name}-glow",
        points,
        style["ringGlowRadius"] * alpha_scale,
        glow_material,
        collection,
        parent,
    )
    create_poly_curve(
        f"{name}-core",
        points,
        style["ringCoreRadius"] * alpha_scale,
        core_material,
        collection,
        parent,
    )


def create_ring_particle_rim(geometry, style, collection, parent):
    if style.get("ringStyle") != "soft-pink-particle-rim":
        return None

    rng = random.Random(style["seed"] + 808)
    materials = create_ring_particle_materials()
    centers = []
    point_count = style["ringParticleCount"]

    for ratio in (0, 1):
        z_jitter_sign = -1 if ratio == 0 else 1
        for point_index in range(point_count):
            theta = point_index / point_count * math.tau + rng.uniform(-0.006, 0.006)
            radial_jitter = rng.uniform(-style["ringParticleRadialJitter"], style["ringParticleRadialJitter"])
            x, y, z = hyperboloid_point(geometry, theta, ratio, radial_jitter)
            z += z_jitter_sign * rng.uniform(-style["ringParticleVerticalJitter"], style["ringParticleVerticalJitter"])
            size = rng.uniform(style["ringParticleSizeMin"], style["ringParticleSizeMax"])
            material_roll = rng.random()
            if material_roll < 0.45:
                material_index = 0
            elif material_roll < 0.74:
                material_index = 1
            elif material_roll < 0.93:
                material_index = 2
            else:
                material_index = 3
            centers.append((x, y, z, size, material_index))

    rim_rig = create_rig("hyperboloid-soft-pink-ring-particles-rig", parent)
    create_particle_mesh("hyperboloid-soft-pink-ring-particles", centers, materials, collection, rim_rig)
    return rim_rig


def create_hyperboloid_wireframe(geometry, style, collection, parent):
    wire_rig = create_rig("hyperboloid-wireframe-rig", parent)
    ring_glow = make_emission_material("hyperboloid-ring-soft-pink-glow", (1.0, 0.54, 0.76), 0.22, 0.42)
    ring_core = make_emission_material("hyperboloid-ring-pink-white-core", (1.0, 0.88, 0.94), 0.42, 0.46)
    faint_glow = make_emission_material(
        "hyperboloid-faint-ring-glow",
        (0.58, 0.9, 1.0),
        0.58,
        style["faintRingAlpha"],
    )
    faint_core = make_emission_material(
        "hyperboloid-faint-ring-core",
        (0.86, 0.98, 1.0),
        0.72,
        style["faintRingAlpha"],
    )

    create_ring_curve("hyperboloid-bottom-ring", geometry, 0, style, collection, wire_rig, ring_core, ring_glow, 1)
    if style.get("waistRingVisible", True):
        create_ring_curve("hyperboloid-waist-ring", geometry, 0.5, style, collection, wire_rig, ring_core, ring_glow, style["waistRingScale"])
    create_ring_curve("hyperboloid-top-ring", geometry, 1, style, collection, wire_rig, ring_core, ring_glow, 1)
    create_ring_particle_rim(geometry, style, collection, wire_rig)

    for index, ratio in enumerate(geometry["latitudeRingRatios"]):
        if abs(ratio - 0.5) < 0.0001:
            continue
        create_ring_curve(
            f"hyperboloid-latitude-ring-{index:02d}",
            geometry,
            ratio,
            style,
            collection,
            wire_rig,
            faint_core,
            faint_glow,
            0.58,
        )

    return wire_rig


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
    glare.threshold = 0.78
    glare.size = 3
    composite = tree.nodes.new("CompositorNodeComposite")
    tree.links.new(render_layers.outputs[0], glare.inputs[0])
    tree.links.new(glare.outputs[0], composite.inputs[0])


def set_fcurve_interpolation(obj, interpolation):
    if obj.animation_data and obj.animation_data.action:
        for fcurve in obj.animation_data.action.fcurves:
            for keyframe in fcurve.keyframe_points:
                keyframe.interpolation = interpolation


def animate_scene(rotation_rig, profile, style):
    scene = bpy.context.scene
    start_frame = scene.frame_start
    loop_frame = scene.frame_end + 1
    total_rotation_degrees = profile["seconds"] / style["rotationCycleSeconds"] * 360

    rotation_rig.rotation_euler = (0, 0, 0)
    rotation_rig.keyframe_insert(data_path="rotation_euler", frame=start_frame)
    rotation_rig.rotation_euler = (0, 0, math.radians(total_rotation_degrees))
    rotation_rig.keyframe_insert(data_path="rotation_euler", frame=loop_frame)
    set_fcurve_interpolation(rotation_rig, "LINEAR")


def main():
    args = parse_args()
    config = load_config()
    profile = config["profiles"][args.profile]
    geometry = config["geometry"]
    style = config["style"]
    project_root = Path(args.project_root)
    output_path = project_root / profile["output"]
    blend_path = project_root / "scene" / "wireframe-hyperboloid-depth-rotation-illusion.blend"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    blend_path.parent.mkdir(parents=True, exist_ok=True)

    clear_scene()
    collection = make_collection("wireframe-hyperboloid-depth-rotation-illusion")
    rotation_rig = create_rig("hyperboloid-rotation-rig")

    create_hyperboloid_wireframe(geometry, style, collection, rotation_rig)
    create_hyperboloid_particles(geometry, style, collection, rotation_rig)
    create_hyperboloid_guide_particles(geometry, style, collection, rotation_rig)
    create_hyperboloid_heart_particles(geometry, style, collection, rotation_rig)
    configure_camera(style)
    configure_render(profile, output_path)
    animate_scene(rotation_rig, profile, style)

    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

    if args.render:
        bpy.ops.render.render(animation=True)


if __name__ == "__main__":
    main()
