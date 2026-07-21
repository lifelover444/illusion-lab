import argparse
from array import array
import hashlib
import json
import math
import random
import shutil
import sys
from pathlib import Path

import bpy
from mathutils import Vector


SCENE_FILENAME = "wireframe-square-bipyramid-depth-rotation-illusion.blend"
RIG_NAME = "square-bipyramid-rotation-rig"
SHELL_NAME = "square-bipyramid-smoked-shell"
SURFACE_DUST_NAME = "square-bipyramid-surface-stardust"
EDGE_CRYSTALS_NAME = "square-bipyramid-edge-crystals"
INTERIOR_DUST_PREFIX = "square-bipyramid-interior-dust"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Create the wireframe square bipyramid depth rotation illusion."
    )
    parser.add_argument("--profile", choices=("preview", "final"), default="preview")
    parser.add_argument("--project-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--stills", action="store_true")
    script_args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(script_args)


def load_config():
    config_path = Path(__file__).resolve().parent / "square-bipyramid-config.json"
    return json.loads(config_path.read_text(encoding="utf-8"))


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for data_blocks in (
        bpy.data.meshes,
        bpy.data.curves,
        bpy.data.materials,
        bpy.data.cameras,
        bpy.data.lights,
        bpy.data.collections,
        bpy.data.worlds,
    ):
        for item in list(data_blocks):
            if item.users == 0:
                data_blocks.remove(item)


def make_collection(name):
    collection = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(collection)
    return collection


def subtract(a, b):
    return tuple(a[index] - b[index] for index in range(3))


def cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def dot(a, b):
    return sum(a[index] * b[index] for index in range(3))


def normalize(point):
    magnitude = math.sqrt(dot(point, point))
    if magnitude <= 1e-12:
        return (0.0, 0.0, 1.0)
    return tuple(component / magnitude for component in point)


def face_normal(face, vertices):
    a, b, c = (vertices[index] for index in face)
    return cross(subtract(b, a), subtract(c, a))


def face_centroid(face, vertices):
    return tuple(sum(vertices[index][axis] for index in face) / 3 for axis in range(3))


def orient_outward(face, vertices):
    if dot(face_normal(face, vertices), face_centroid(face, vertices)) > 0:
        return face
    return face[0], face[2], face[1]


def create_geometry(geometry):
    radius = geometry["waistRadius"]
    half_height = geometry["halfHeight"]
    phase = math.radians(geometry["initialPhaseDegrees"])
    vertices = [(0.0, 0.0, half_height), (0.0, 0.0, -half_height)]
    for index in range(4):
        angle = phase + index * math.tau / 4
        vertices.append((radius * math.cos(angle), radius * math.sin(angle), 0.0))

    faces = []
    edges = []
    waist_edges = []
    for index in range(4):
        current = 2 + index
        next_index = 2 + (index + 1) % 4
        faces.append(orient_outward((0, current, next_index), vertices))
        faces.append(orient_outward((1, next_index, current), vertices))
        edges.extend(((0, current), (1, current), (current, next_index)))
        waist_edges.append((current, next_index))
    return vertices, faces, edges, waist_edges


def make_emission_material(name, color, strength, alpha=1.0):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    material.diffuse_color = (*color, alpha)
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    emission = nodes.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value = (*color, alpha)
    emission.inputs["Strength"].default_value = strength
    links.new(emission.outputs[0], output.inputs[0])
    return material


def make_ambiguous_shell_material(style):
    material = bpy.data.materials.new("smoked-ambiguous-glass")
    material.use_nodes = True
    material.diffuse_color = (*style["faceColor"], style["faceAlpha"])
    if hasattr(material, "surface_render_method"):
        material.surface_render_method = "BLENDED"
    if hasattr(material, "use_transparency_overlap"):
        material.use_transparency_overlap = False
    material.show_transparent_back = True

    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    transparent = nodes.new("ShaderNodeBsdfTransparent")
    emission = nodes.new("ShaderNodeEmission")
    mix_shader = nodes.new("ShaderNodeMixShader")
    transparent.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    emission.inputs["Color"].default_value = (*style["faceColor"], 1.0)
    emission.inputs["Strength"].default_value = style["faceEmissionStrength"]
    mix_shader.inputs[0].default_value = style["faceAlpha"]
    links.new(transparent.outputs[0], mix_shader.inputs[1])
    links.new(emission.outputs[0], mix_shader.inputs[2])
    links.new(mix_shader.outputs[0], output.inputs[0])
    return material


def create_shell(vertices, faces, material, collection, parent):
    mesh = bpy.data.meshes.new(SHELL_NAME)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    for polygon in mesh.polygons:
        polygon.use_smooth = False
    obj = bpy.data.objects.new(SHELL_NAME, mesh)
    obj.parent = parent
    obj.data.materials.append(material)
    obj["source_vertex_count"] = len(vertices)
    obj["triangle_count"] = len(faces)
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
        point.co = (*coordinates, 1.0)
    obj = bpy.data.objects.new(name, curve)
    obj.parent = parent
    obj.data.materials.append(material)
    collection.objects.link(obj)
    return obj


def create_crystal_edges(vertices, edges, waist_edges, style, collection, parent):
    core_material = make_emission_material(
        "ice-edge-white-core",
        style["edgeCoreColor"],
        style["edgeCoreStrength"],
    )
    glow_material = make_emission_material(
        "ice-edge-blue-halo",
        style["edgeGlowColor"],
        style["edgeGlowStrength"],
    )
    waist_set = {tuple(edge) for edge in waist_edges}
    for index, edge in enumerate(edges):
        a, b = (vertices[vertex_index] for vertex_index in edge)
        line_scale = style["waistLineScale"] if tuple(edge) in waist_set else 1.0
        create_poly_curve(
            f"crystal-edge-glow-{index + 1:02d}",
            (a, b),
            style["edgeGlowRadius"] * line_scale,
            glow_material,
            collection,
            parent,
        )
        create_poly_curve(
            f"crystal-edge-core-{index + 1:02d}",
            (a, b),
            style["edgeCoreRadius"] * line_scale,
            core_material,
            collection,
            parent,
        )


def create_particle_materials(prefix, palette, strength_min, strength_max):
    materials = []
    denominator = max(1, len(palette) - 1)
    for index, color in enumerate(palette):
        ratio = index / denominator
        strength = strength_min + (strength_max - strength_min) * ratio
        materials.append(
            make_emission_material(
                f"{prefix}-{index + 1:02d}", tuple(color), strength, 0.94
            )
        )
    return materials


def create_particle_mesh(name, centers, materials, collection, parent):
    vertices = []
    faces = []
    material_indices = []
    for x, y, z, size, material_index in centers:
        base = len(vertices)
        vertices.extend(
            (
                (x + size, y, z),
                (x - size, y, z),
                (x, y + size, z),
                (x, y - size, z),
                (x, y, z + size),
                (x, y, z - size),
            )
        )
        faces.extend(
            (
                (base + 0, base + 2, base + 4),
                (base + 2, base + 1, base + 4),
                (base + 1, base + 3, base + 4),
                (base + 3, base + 0, base + 4),
                (base + 2, base + 0, base + 5),
                (base + 1, base + 2, base + 5),
                (base + 3, base + 1, base + 5),
                (base + 0, base + 3, base + 5),
            )
        )
        material_indices.extend([material_index] * 8)
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    obj.parent = parent
    for material in materials:
        obj.data.materials.append(material)
    for polygon, material_index in zip(obj.data.polygons, material_indices):
        polygon.material_index = material_index
    obj["particle_count"] = len(centers)
    collection.objects.link(obj)
    return obj


def random_barycentric(rng, edge_boost):
    if rng.random() < edge_boost:
        thin = rng.uniform(0.0, 0.035)
        split = rng.random() * (1.0 - thin)
        weights = [thin, split, 1.0 - thin - split]
        rng.shuffle(weights)
        return weights
    root = math.sqrt(rng.random())
    second = rng.random()
    return (1.0 - root, root * (1.0 - second), root * second)


def create_surface_stardust(vertices, faces, style, collection, parent):
    rng = random.Random(style["seed"])
    materials = create_particle_materials(
        "stardust",
        style["particlePalette"],
        style["particleStrengthMin"],
        style["particleStrengthMax"],
    )
    centers = []
    for _ in range(style["particleCount"]):
        face = faces[rng.randrange(len(faces))]
        a, b, c = (vertices[index] for index in face)
        weights = random_barycentric(rng, style["particleEdgeBoost"])
        normal = normalize(face_normal(face, vertices))
        jitter = rng.uniform(-style["particleJitter"], style["particleJitter"])
        point = tuple(
            a[axis] * weights[0]
            + b[axis] * weights[1]
            + c[axis] * weights[2]
            + normal[axis] * jitter
            for axis in range(3)
        )
        size_ratio = rng.random() ** 2.2
        size = style["particleSizeMin"] + (
            style["particleSizeMax"] - style["particleSizeMin"]
        ) * size_ratio
        material_index = rng.randrange(len(materials))
        centers.append((*point, size, material_index))
    return create_particle_mesh(
        SURFACE_DUST_NAME, centers, materials, collection, parent
    )


def create_edge_crystals(vertices, edges, style, collection, parent):
    rng = random.Random(style["seed"] + 404)
    materials = create_particle_materials(
        "edge-crystal",
        style["edgePalette"],
        style["particleStrengthMax"] * 0.9,
        style["edgeCoreStrength"],
    )
    centers = []
    for index in range(style["edgeCrystalCount"]):
        edge = edges[index % len(edges)]
        a, b = (vertices[vertex_index] for vertex_index in edge)
        ratio = rng.random()
        jitter = style["edgeCrystalJitter"]
        point = tuple(
            a[axis] + (b[axis] - a[axis]) * ratio + rng.uniform(-jitter, jitter)
            for axis in range(3)
        )
        size = rng.uniform(style["edgeCrystalSizeMin"], style["edgeCrystalSizeMax"])
        centers.append((*point, size, rng.randrange(len(materials))))
    return create_particle_mesh(
        EDGE_CRYSTALS_NAME, centers, materials, collection, parent
    )


def sample_interior_point(rng, geometry, boundary_padding):
    half_height = geometry["halfHeight"]
    half_side = geometry["waistRadius"] / math.sqrt(2)
    limit = 1.0 - boundary_padding
    orientation = math.radians(geometry["initialPhaseDegrees"]) - math.pi / 4
    cosine = math.cos(orientation)
    sine = math.sin(orientation)

    while True:
        local_x = rng.uniform(-half_side * limit, half_side * limit)
        local_y = rng.uniform(-half_side * limit, half_side * limit)
        z = rng.uniform(-half_height * limit, half_height * limit)
        normalized_radius = max(abs(local_x), abs(local_y)) / half_side
        normalized_height = abs(z) / half_height
        if normalized_radius + normalized_height <= limit:
            return (
                local_x * cosine - local_y * sine,
                local_x * sine + local_y * cosine,
                z,
            )


def create_interior_dust(geometry, style, collection, parent):
    dust = style["interiorDust"]
    if sum(layer["count"] for layer in dust["layers"]) != dust["count"]:
        raise RuntimeError("Interior dust layer counts must add up to the total count.")

    layer_rigs = []
    for layer_index, layer in enumerate(dust["layers"]):
        rng = random.Random(style["seed"] + 9001 + layer_index * 137)
        rig = bpy.data.objects.new(f"{INTERIOR_DUST_PREFIX}-{layer['name']}-rig", None)
        rig.parent = parent
        collection.objects.link(rig)
        materials = create_particle_materials(
            f"interior-{layer['name']}",
            dust["palette"],
            dust["strengthMin"] * layer["strengthScale"],
            dust["strengthMax"] * layer["strengthScale"],
        )
        centers = []
        for _ in range(layer["count"]):
            point = sample_interior_point(rng, geometry, dust["boundaryPadding"])
            size_ratio = rng.random() ** 2.5
            size = (
                dust["sizeMin"]
                + (dust["sizeMax"] - dust["sizeMin"]) * size_ratio
            ) * layer["sizeScale"]
            centers.append((*point, size, rng.randrange(len(materials))))
        obj = create_particle_mesh(
            f"{INTERIOR_DUST_PREFIX}-{layer['name']}",
            centers,
            materials,
            collection,
            rig,
        )
        obj["dust_layer"] = layer["name"]
        layer_rigs.append((rig, layer))
    return layer_rigs


def animate_interior_dust(layer_rigs, profile, style):
    frame_start = bpy.context.scene.frame_start
    frame_end = bpy.context.scene.frame_end
    loop_span = frame_end - frame_start
    turns = profile["seconds"] / style["rotationCycleSeconds"]
    for rig, layer in layer_rigs:
        phase = math.radians(layer["phaseDegrees"])
        angular_amplitude = math.radians(layer["angularDriftDegrees"])
        signal = (
            f"sin({math.tau:.15f} * {turns:.15f} * "
            f"(frame - {frame_start}) / {loop_span} + {phase:.15f})"
        )
        rotation_driver = rig.driver_add("rotation_euler", 2).driver
        rotation_driver.expression = f"{angular_amplitude:.15f} * {signal}"
        vertical_driver = rig.driver_add("location", 2).driver
        vertical_driver.expression = f"{layer['verticalBob']:.15f} * {signal}"
        rig["loop_span_frames"] = loop_span
        rig["turns"] = turns
        rig["angular_drift_degrees"] = layer["angularDriftDegrees"]
        rig["vertical_bob"] = layer["verticalBob"]


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
    look_at(camera, style["cameraTarget"])
    camera_data.type = style["cameraProjection"]
    camera_data.ortho_scale = style["orthographicScale"]
    bpy.context.scene.collection.objects.link(camera)
    bpy.context.scene.camera = camera
    return camera


def configure_render(profile, style, output_path):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.eevee.taa_render_samples = profile["samples"]
    scene.eevee.taa_samples = min(profile["samples"], 16)
    scene.render.resolution_x = profile["width"]
    scene.render.resolution_y = profile["height"]
    scene.render.resolution_percentage = 100
    scene.render.fps = profile["fps"]
    scene.render.fps_base = 1.0
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.color_depth = "8"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "MEDIUM"
    scene.render.ffmpeg.ffmpeg_preset = "GOOD"
    scene.render.ffmpeg.gopsize = profile["fps"]
    scene.render.filepath = str(output_path)
    scene.render.film_transparent = False
    scene.frame_start = 1
    scene.frame_end = round(profile["fps"] * profile["seconds"])

    world = bpy.data.worlds.new("pure-black-world")
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (*style["backgroundColor"], 1.0)
    background.inputs["Strength"].default_value = 0.0
    scene.world = world

    scene.view_settings.view_transform = "Standard"
    try:
        scene.view_settings.look = "Medium High Contrast"
    except TypeError:
        pass
    scene.view_settings.exposure = 0.0
    scene.view_settings.gamma = 1.0

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
    loop_frame = scene.frame_end
    penultimate_frame = loop_frame - 1
    loop_span = loop_frame - scene.frame_start
    turns = profile["seconds"] / style["rotationCycleSeconds"]
    rig.rotation_euler = (0.0, 0.0, 0.0)
    rig.keyframe_insert(data_path="rotation_euler", frame=scene.frame_start)
    penultimate_angle = turns * math.tau * (
        (penultimate_frame - scene.frame_start) / loop_span
    )
    rig.rotation_euler = (0.0, 0.0, penultimate_angle)
    rig.keyframe_insert(data_path="rotation_euler", frame=penultimate_frame)
    rig.rotation_euler = (0.0, 0.0, 0.0)
    rig.keyframe_insert(data_path="rotation_euler", frame=loop_frame)
    set_linear_interpolation(rig)


def validate_scene_contract(vertices, faces, edges, style):
    shell = bpy.data.objects.get(SHELL_NAME)
    dust = bpy.data.objects.get(SURFACE_DUST_NAME)
    crystals = bpy.data.objects.get(EDGE_CRYSTALS_NAME)
    interior_objects = [
        obj
        for obj in bpy.data.objects
        if obj.type == "MESH" and obj.name.startswith(INTERIOR_DUST_PREFIX)
    ]
    interior_rigs = [
        obj
        for obj in bpy.data.objects
        if obj.type == "EMPTY" and obj.name.startswith(INTERIOR_DUST_PREFIX)
    ]
    curve_objects = [obj for obj in bpy.data.objects if obj.type == "CURVE"]
    if len(vertices) != 6 or len(faces) != 8 or len(edges) != 12:
        raise RuntimeError("Square bipyramid geometry must be 6 vertices, 8 faces, 12 edges.")
    if shell is None or len(shell.data.vertices) != 6 or len(shell.data.polygons) != 8:
        raise RuntimeError("The scene must contain one complete eight-face transparent shell.")
    if dust is None or dust.get("particle_count") != style["particleCount"]:
        raise RuntimeError("Surface stardust count does not match the render contract.")
    if crystals is None or crystals.get("particle_count") != style["edgeCrystalCount"]:
        raise RuntimeError("Edge crystal count does not match the render contract.")
    if len(interior_objects) != len(style["interiorDust"]["layers"]):
        raise RuntimeError("Every interior dust layer must have one particle mesh.")
    if sum(obj.get("particle_count", 0) for obj in interior_objects) != style[
        "interiorDust"
    ]["count"]:
        raise RuntimeError("Interior dust count does not match the render contract.")
    if len(interior_rigs) != len(style["interiorDust"]["layers"]):
        raise RuntimeError("Every interior dust layer must have one drift rig.")
    if any(
        rig.animation_data is None or len(rig.animation_data.drivers) != 2
        for rig in interior_rigs
    ):
        raise RuntimeError("Every interior dust rig must have looping rotation and bob drivers.")
    if len(curve_objects) != len(edges) * 2:
        raise RuntimeError("Every structural edge must have one core and one glow curve.")
    if len(bpy.data.lights) != 0:
        raise RuntimeError("Directional lights would weaken the ambiguous rotation illusion.")
    if bpy.context.scene.camera.data.type != "ORTHO":
        raise RuntimeError("The illusion requires an orthographic camera.")


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_contact_sheet(still_paths, output_path):
    images = [bpy.data.images.load(str(path), check_existing=False) for path in still_paths]
    width = images[0].size[0]
    height = images[0].size[1]
    sheet_width = width * len(images)
    sheet_pixels = array("f", [0.0]) * (sheet_width * height * 4)
    pixel_hashes = {}
    for image_index, image in enumerate(images):
        source_pixels = array("f", [0.0]) * (width * height * 4)
        image.pixels.foreach_get(source_pixels)
        pixel_hashes[still_paths[image_index].stem] = hashlib.sha256(
            source_pixels.tobytes()
        ).hexdigest()
        row_length = width * 4
        for row in range(height):
            source_start = row * row_length
            destination_start = (row * sheet_width + image_index * width) * 4
            sheet_pixels[destination_start : destination_start + row_length] = source_pixels[
                source_start : source_start + row_length
            ]
    sheet = bpy.data.images.new(
        "square-bipyramid-contact-sheet",
        width=sheet_width,
        height=height,
        alpha=False,
        float_buffer=False,
    )
    sheet.pixels.foreach_set(sheet_pixels)
    sheet.filepath_raw = str(output_path)
    sheet.file_format = "PNG"
    sheet.save()
    for image in images:
        bpy.data.images.remove(image)
    bpy.data.images.remove(sheet)
    return pixel_hashes


def write_inspection(
    project_root,
    profile,
    style,
    geometry,
    vertices,
    faces,
    edges,
    still_paths,
    pixel_hashes,
    loop_endpoint_hashes,
):
    inspection = {
        "geometry": {
            "uniqueVertexCount": len(vertices),
            "uniqueTriangleCount": len(faces),
            "structuralEdgeCount": len(edges),
            "waistRadius": geometry["waistRadius"],
            "halfHeight": geometry["halfHeight"],
        },
        "surface": {
            "renderMode": "ambiguous-crystal-stardust",
            "faceAlpha": style["faceAlpha"],
            "surfaceParticleCount": style["particleCount"],
            "edgeCrystalCount": style["edgeCrystalCount"],
            "interiorDustCount": style["interiorDust"]["count"],
            "interiorDustLayers": [
                {
                    "name": layer["name"],
                    "count": layer["count"],
                    "angularDriftDegrees": layer["angularDriftDegrees"],
                    "verticalBob": layer["verticalBob"],
                    "phaseDegrees": layer["phaseDegrees"],
                }
                for layer in style["interiorDust"]["layers"]
            ],
            "curveObjectCount": len([obj for obj in bpy.data.objects if obj.type == "CURVE"]),
        },
        "scene": {
            "lightCount": len(bpy.data.lights),
            "cameraType": bpy.context.scene.camera.data.type,
            "cameraElevationDegrees": style["cameraElevationDegrees"],
            "orthographicScale": bpy.context.scene.camera.data.ortho_scale,
        },
        "animation": {
            "frameStart": bpy.context.scene.frame_start,
            "frameEnd": bpy.context.scene.frame_end,
            "loopFrame": bpy.context.scene.frame_end,
            "rotationCycleSeconds": style["rotationCycleSeconds"],
            "totalTurns": profile["seconds"] / style["rotationCycleSeconds"],
            "interpolation": "LINEAR",
            "firstFramePixelHash": loop_endpoint_hashes["start"],
            "lastFramePixelHash": loop_endpoint_hashes["end"],
            "firstFrameMatchesLastFrame": loop_endpoint_hashes["start"]
            == loop_endpoint_hashes["end"],
        },
        "stills": {
            "fileHashes": {path.stem: sha256(path) for path in still_paths},
            "pixelHashes": pixel_hashes,
            "zeroMatches360": pixel_hashes["phase-000"] == pixel_hashes["phase-360"],
            "contactSheet": "output/stills/square-bipyramid-contact-sheet.png",
        },
    }
    inspection_path = project_root / "output" / "inspection.json"
    inspection_path.write_text(json.dumps(inspection, indent=2), encoding="utf-8")


def render_stills(project_root, rig, profile, style, geometry, vertices, faces, edges):
    scene = bpy.context.scene
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.frame_set(scene.frame_start)
    still_directory = project_root / "output" / "stills"
    still_directory.mkdir(parents=True, exist_ok=True)
    still_paths = []
    fcurves = list(rig.animation_data.action.fcurves)
    mute_states = [fcurve.mute for fcurve in fcurves]
    for fcurve in fcurves:
        fcurve.mute = True
    try:
        zero_phase_path = None
        for phase in style["phaseDegrees"]:
            still_path = still_directory / f"phase-{phase:03d}.png"
            if phase == 360:
                if zero_phase_path is None:
                    raise RuntimeError("The 0-degree phase must precede 360 degrees.")
                shutil.copyfile(zero_phase_path, still_path)
            else:
                rig.rotation_euler = (0.0, 0.0, math.radians(phase))
                bpy.context.view_layer.update()
                scene.render.filepath = str(still_path)
                bpy.ops.render.render(write_still=True)
                if phase == 0:
                    zero_phase_path = still_path
            still_paths.append(still_path)
    finally:
        for fcurve, mute_state in zip(fcurves, mute_states):
            fcurve.mute = mute_state
        scene.frame_set(scene.frame_start)

    contact_sheet_path = still_directory / "square-bipyramid-contact-sheet.png"
    pixel_hashes = build_contact_sheet(still_paths, contact_sheet_path)
    if pixel_hashes["phase-000"] != pixel_hashes["phase-360"]:
        raise RuntimeError("The 0-degree and 360-degree stills must be pixel-identical.")
    loop_endpoint_hashes = {}
    for label, frame in (("start", scene.frame_start), ("end", scene.frame_end)):
        scene.frame_set(frame)
        endpoint_path = still_directory / f"loop-{label}-frame.png"
        scene.render.filepath = str(endpoint_path)
        bpy.ops.render.render(write_still=True)
        image = bpy.data.images.load(str(endpoint_path), check_existing=False)
        pixels = array("f", [0.0]) * (image.size[0] * image.size[1] * 4)
        image.pixels.foreach_get(pixels)
        loop_endpoint_hashes[label] = hashlib.sha256(pixels.tobytes()).hexdigest()
        bpy.data.images.remove(image)
    if loop_endpoint_hashes["start"] != loop_endpoint_hashes["end"]:
        raise RuntimeError("The rendered first and last animation frames must be pixel-identical.")
    write_inspection(
        project_root,
        profile,
        style,
        geometry,
        vertices,
        faces,
        edges,
        still_paths,
        pixel_hashes,
        loop_endpoint_hashes,
    )


def main():
    args = parse_args()
    config = load_config()
    profile = config["profiles"][args.profile]
    geometry = config["geometry"]
    style = config["style"]
    project_root = Path(args.project_root)
    output_path = project_root / profile["output"]
    blend_path = project_root / "scene" / SCENE_FILENAME
    output_path.parent.mkdir(parents=True, exist_ok=True)
    blend_path.parent.mkdir(parents=True, exist_ok=True)

    clear_scene()
    collection = make_collection("wireframe-square-bipyramid-depth-rotation-illusion")
    rig = bpy.data.objects.new(RIG_NAME, None)
    collection.objects.link(rig)
    vertices, faces, edges, waist_edges = create_geometry(geometry)
    create_shell(
        vertices,
        faces,
        make_ambiguous_shell_material(style),
        collection,
        rig,
    )
    create_crystal_edges(vertices, edges, waist_edges, style, collection, rig)
    create_surface_stardust(vertices, faces, style, collection, rig)
    create_edge_crystals(vertices, edges, style, collection, rig)
    interior_dust_rigs = create_interior_dust(geometry, style, collection, rig)
    configure_camera(style)
    configure_render(profile, style, output_path)
    animate_rotation(rig, profile, style)
    animate_interior_dust(interior_dust_rigs, profile, style)
    validate_scene_contract(vertices, faces, edges, style)
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

    if args.stills:
        render_stills(project_root, rig, profile, style, geometry, vertices, faces, edges)
    elif args.render:
        bpy.ops.render.render(animation=True)


if __name__ == "__main__":
    main()
