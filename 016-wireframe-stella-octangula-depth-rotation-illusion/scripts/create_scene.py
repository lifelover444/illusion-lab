import argparse
from array import array
import colorsys
import hashlib
import json
import math
import random
import shutil
import sys
from pathlib import Path

import bpy
from mathutils import Vector


SCENE_FILENAME = "wireframe-stella-octangula-depth-rotation-illusion.blend"
RIG_NAME = "stella-octangula-rigid-rotation"
EDGE_PARTICLES_NAME = "stella-octangula-broken-edge-particles"
EDGE_HALO_PARTICLES_NAME = "stella-octangula-sparse-edge-halo-particles"
FACE_BASE_DUST_NAME = "stella-octangula-dark-slate-base-dust"
FACE_COLOR_GRAINS_NAME = "stella-octangula-mineral-aurora-color-grains"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Create the low-resolution wireframe stella octangula illusion."
    )
    parser.add_argument("--profile", choices=("preview",), default="preview")
    parser.add_argument("--project-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--stills", action="store_true")
    script_args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(script_args)


def load_config():
    config_path = Path(__file__).resolve().parent / "stella-octangula-config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if list(config["profiles"]) != ["preview"]:
        raise RuntimeError("Experiment 016 may define only the low-resolution preview profile.")
    profile = config["profiles"]["preview"]
    if profile["width"] != 360 or profile["height"] != 640:
        raise RuntimeError("Experiment 016 preview is fixed at 360x640.")
    return config


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


def add(a, b):
    return tuple(a[index] + b[index] for index in range(3))


def subtract(a, b):
    return tuple(a[index] - b[index] for index in range(3))


def scale(point, factor):
    return tuple(component * factor for component in point)


def dot(a, b):
    return sum(a[index] * b[index] for index in range(3))


def cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def magnitude(vector):
    return math.sqrt(dot(vector, vector))


def normalize(vector):
    length = magnitude(vector)
    if length <= 1e-12:
        raise RuntimeError("Cannot normalize a zero-length vector.")
    return scale(vector, 1 / length)


def distance(a, b):
    return magnitude(subtract(b, a))


def point_key(point):
    return tuple(round(0.0 if abs(component) < 1e-11 else component, 10) for component in point)


def canonical_edge(edge):
    return tuple(sorted(edge))


def display_basis():
    return (
        (1 / math.sqrt(2), -1 / math.sqrt(2), 0.0),
        (1 / math.sqrt(6), 1 / math.sqrt(6), -2 / math.sqrt(6)),
        (1 / math.sqrt(3), 1 / math.sqrt(3), 1 / math.sqrt(3)),
    )


def transform_to_display(point):
    e_x, e_y, e_z = display_basis()
    return dot(point, e_x), dot(point, e_y), dot(point, e_z)


def face_normal(face, vertices):
    a, b, c = (vertices[index] for index in face)
    return cross(subtract(b, a), subtract(c, a))


def face_centroid(face, vertices):
    return tuple(sum(vertices[index][axis] for index in face) / 3 for axis in range(3))


def orient_outward(face, vertices):
    if dot(face_normal(face, vertices), face_centroid(face, vertices)) > 0:
        return face
    return face[0], face[2], face[1]


def triangle_area(a, b, c):
    return magnitude(cross(subtract(b, a), subtract(c, a))) / 2


def complete_edges(indices):
    return [
        (indices[first], indices[second])
        for first in range(len(indices))
        for second in range(first + 1, len(indices))
    ]


def tetra_faces(indices, vertices):
    candidates = (
        (indices[0], indices[1], indices[2]),
        (indices[0], indices[3], indices[1]),
        (indices[0], indices[2], indices[3]),
        (indices[1], indices[3], indices[2]),
    )
    return [orient_outward(face, vertices) for face in candidates]


def intersect_segments(start_a, end_a, start_b, end_b, tolerance=1e-10):
    u = subtract(end_a, start_a)
    v = subtract(end_b, start_b)
    w = subtract(start_a, start_b)
    uu = dot(u, u)
    uv = dot(u, v)
    vv = dot(v, v)
    uw = dot(u, w)
    vw = dot(v, w)
    denominator = uu * vv - uv * uv
    if abs(denominator) <= tolerance * max(1, uu * vv):
        return None
    t_a = (uv * vw - vv * uw) / denominator
    t_b = (uu * vw - uv * uw) / denominator
    if not tolerance < t_a < 1 - tolerance or not tolerance < t_b < 1 - tolerance:
        return None
    point_a = add(start_a, scale(u, t_a))
    point_b = add(start_b, scale(v, t_b))
    if distance(point_a, point_b) > tolerance:
        return None
    return {"point": scale(add(point_a, point_b), 0.5), "tA": t_a, "tB": t_b}


def find_intersections(vertices, edges_a, edges_b):
    intersections = []
    for edge_a in edges_a:
        for edge_b in edges_b:
            match = intersect_segments(
                vertices[edge_a[0]],
                vertices[edge_a[1]],
                vertices[edge_b[0]],
                vertices[edge_b[1]],
            )
            if match:
                intersections.append({**match, "edgeA": edge_a, "edgeB": edge_b})
    return intersections


def sign_label(sign):
    return "+" if sign > 0 else "-"


def create_geometry(geometry):
    a = geometry["cubeHalfExtent"]
    if a <= 0:
        raise RuntimeError("cubeHalfExtent must be positive.")
    signs_a = ((1, 1, 1), (1, -1, -1), (-1, 1, -1), (-1, -1, 1))
    signs_b = ((-1, -1, -1), (-1, 1, 1), (1, -1, 1), (1, 1, -1))
    signs = signs_a + signs_b
    source_vertices = [(sx * a, sy * a, sz * a) for sx, sy, sz in signs]
    vertices = [transform_to_display(point) for point in source_vertices]
    labels = [
        f"P({sign_label(sx)},{sign_label(sy)},{sign_label(sz)})"
        for sx, sy, sz in signs
    ]
    tetra_a = (0, 1, 2, 3)
    tetra_b = (4, 5, 6, 7)
    edges_a = complete_edges(tetra_a)
    edges_b = complete_edges(tetra_b)
    faces_a = tetra_faces(tetra_a, vertices)
    faces_b = tetra_faces(tetra_b, vertices)
    intersections = find_intersections(vertices, edges_a, edges_b)
    return {
        "sourceVertices": source_vertices,
        "vertices": vertices,
        "labels": labels,
        "tetraA": tetra_a,
        "tetraB": tetra_b,
        "edgesA": edges_a,
        "edgesB": edges_b,
        "edges": edges_a + edges_b,
        "facesA": faces_a,
        "facesB": faces_b,
        "faces": faces_a + faces_b,
        "intersections": intersections,
    }


def make_emission_material(name, color, strength, alpha=1.0):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    material.diffuse_color = (*color, alpha)
    if alpha < 1.0 and hasattr(material, "surface_render_method"):
        try:
            material.surface_render_method = "BLENDED"
        except TypeError:
            material.surface_render_method = "DITHERED"
    if hasattr(material, "use_transparency_overlap"):
        material.use_transparency_overlap = False
    material.show_transparent_back = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    emission = nodes.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value = (*color, 1.0)
    emission.inputs["Strength"].default_value = strength
    if alpha >= 1.0:
        links.new(emission.outputs[0], output.inputs[0])
    else:
        transparent = nodes.new("ShaderNodeBsdfTransparent")
        mix_shader = nodes.new("ShaderNodeMixShader")
        mix_shader.inputs[0].default_value = alpha
        links.new(transparent.outputs[0], mix_shader.inputs[1])
        links.new(emission.outputs[0], mix_shader.inputs[2])
        links.new(mix_shader.outputs[0], output.inputs[0])
    return material


def create_particle_materials(prefix, palette, strength_min, strength_max, alpha=1.0):
    materials = []
    denominator = max(1, len(palette) - 1)
    for index, color in enumerate(palette):
        ratio = index / denominator
        strength = strength_min + (strength_max - strength_min) * ratio
        materials.append(
            make_emission_material(f"{prefix}-{index + 1:02d}", color, strength, alpha)
        )
    return materials


def spectral_palette(gradient, style_name):
    style = gradient["styles"][style_name]
    palette = []
    for index in range(gradient["bandCount"]):
        hue = (index + 0.5) / gradient["bandCount"]
        color = colorsys.hsv_to_rgb(hue, style["saturation"], style["value"])
        white_mix = style["whiteMix"]
        palette.append(
            tuple(component * (1 - white_mix) + white_mix for component in color)
        )
    return palette


def gradient_projection_bounds(vertices, gradient):
    direction = normalize(tuple(gradient["direction"]))
    projections = [dot(point, direction) for point in vertices]
    minimum = min(projections)
    maximum = max(projections)
    if maximum - minimum <= 1e-12:
        raise RuntimeError("The spectral-gradient projection span must be nonzero.")
    return direction, minimum, maximum


def spectral_material_index(point, gradient, projection_bounds):
    direction, minimum, maximum = projection_bounds
    position = (dot(point, direction) - minimum) / (maximum - minimum)
    hue = (
        gradient["phase"] + gradient["cyclesAcrossObject"] * position
    ) % 1.0
    return min(gradient["bandCount"] - 1, int(hue * gradient["bandCount"]))


def create_particle_mesh(name, centers, materials, collection, parent, role):
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
    obj["motion"] = "RIGID_LOCKED"
    obj["role"] = role
    collection.objects.link(obj)
    return obj


def random_barycentric(rng):
    root = math.sqrt(rng.random())
    second = rng.random()
    return 1 - root, root * (1 - second), root * second


def sample_triangle(rng, a, b, c):
    weights = random_barycentric(rng)
    return tuple(
        a[axis] * weights[0] + b[axis] * weights[1] + c[axis] * weights[2]
        for axis in range(3)
    )


def allocate_by_area(total_count, areas):
    total_area = sum(areas)
    exact = [total_count * area / total_area for area in areas]
    counts = [math.floor(value) for value in exact]
    missing = total_count - sum(counts)
    ranking = sorted(
        range(len(areas)), key=lambda index: exact[index] - counts[index], reverse=True
    )
    for index in ranking[:missing]:
        counts[index] += 1
    return counts


def weighted_material_index(rng, weights):
    if not weights or any(weight < 0 for weight in weights):
        raise RuntimeError("Particle palette weights must be nonnegative and nonempty.")
    total = sum(weights)
    if total <= 0:
        raise RuntimeError("Particle palette weights must have positive total weight.")
    selection = rng.random() * total
    cumulative = 0.0
    for index, weight in enumerate(weights):
        cumulative += weight
        if selection <= cumulative:
            return index
    return len(weights) - 1


def balanced_material_indices(count, weights, rng):
    indices = []
    for material_index, material_count in enumerate(allocate_by_area(count, weights)):
        indices.extend([material_index] * material_count)
    rng.shuffle(indices)
    return indices


def create_face_particle_layer(
    name, material_prefix, role, vertices, faces, layer, collection, parent, seed
):
    rng = random.Random(seed)
    uses_spectral_gradient = layer.get("colorMode") == "OBJECT_SPACE_SPECTRAL"
    if not uses_spectral_gradient and len(layer["palette"]) != len(layer["paletteWeights"]):
        raise RuntimeError("Each surface-particle color needs one palette weight.")
    materials = create_particle_materials(
        material_prefix,
        layer["palette"],
        layer["strengthMin"],
        layer["strengthMax"],
    )
    counts = allocate_by_area(
        layer["count"],
        [triangle_area(*(vertices[index] for index in face)) for face in faces],
    )
    centers = []
    for face, count in zip(faces, counts):
        a, b, c = (vertices[index] for index in face)
        normal = normalize(face_normal(face, vertices))
        balanced_indices = (
            balanced_material_indices(count, layer["paletteWeights"], rng)
            if layer.get("balancedPerFace") and not uses_spectral_gradient
            else None
        )
        for particle_index in range(count):
            point = sample_triangle(rng, a, b, c)
            offset = rng.uniform(-layer["normalJitter"], layer["normalJitter"])
            point = add(point, scale(normal, offset))
            size_ratio = rng.random() ** layer["sizeExponent"]
            size = layer["sizeMin"] + (layer["sizeMax"] - layer["sizeMin"]) * size_ratio
            if uses_spectral_gradient:
                material_index = spectral_material_index(
                    point, layer["gradient"], layer["gradientProjectionBounds"]
                )
            elif balanced_indices is not None:
                material_index = balanced_indices[particle_index]
            else:
                material_index = weighted_material_index(rng, layer["paletteWeights"])
            centers.append((*point, size, material_index))
    rng.shuffle(centers)
    obj = create_particle_mesh(name, centers, materials, collection, parent, role)
    obj["face_counts"] = counts
    obj["sampling"] = "AREA_WEIGHTED_EQUAL_DENSITY"
    if uses_spectral_gradient:
        obj["palette_distribution"] = "OBJECT_SPACE_SPECTRAL"
    else:
        obj["palette_distribution"] = (
            "BALANCED_PER_FACE" if layer.get("balancedPerFace") else "WEIGHTED_RANDOM"
        )
    return obj


def create_face_surface(vertices, faces, style, collection, parent):
    layers = style["faceParticleLayers"]
    gradient = style["spectralGradient"]
    projection_bounds = gradient_projection_bounds(vertices, gradient)
    if sum(layer["count"] for layer in layers.values()) != style["faceParticleCount"]:
        raise RuntimeError("Face-particle layer counts must match faceParticleCount.")

    def prepared(layer):
        return {
            **layer,
            "palette": spectral_palette(gradient, layer["gradientStyle"]),
            "gradient": gradient,
            "gradientProjectionBounds": projection_bounds,
            "strengthMin": layer["strength"],
            "strengthMax": layer["strength"],
        }

    base_dust = create_face_particle_layer(
        FACE_BASE_DUST_NAME,
        "shared-object-space-spectral-base-dust",
        "object-space-spectral-base-dust",
        vertices,
        faces,
        prepared(layers["baseDust"]),
        collection,
        parent,
        style["seed"] + 1601,
    )
    color_grains = create_face_particle_layer(
        FACE_COLOR_GRAINS_NAME,
        "shared-object-space-spectral-color-grain",
        "object-space-spectral-color-grains",
        vertices,
        faces,
        prepared(layers["colorGrains"]),
        collection,
        parent,
        style["seed"] + 1701,
    )
    return base_dust, color_grains


def create_edge_particles(vertices, edges, style, collection, parent):
    rng = random.Random(style["seed"] + 404)
    if style["edgeParticleCount"] % len(edges) != 0:
        raise RuntimeError("Edge particles must divide equally across all twelve edges.")
    particles_per_edge = style["edgeParticleCount"] // len(edges)
    slots_per_edge = style["edgeParticleSlotsPerEdge"]
    if particles_per_edge > slots_per_edge:
        raise RuntimeError("Edge particle count cannot exceed the available broken-line slots.")
    gradient = style["spectralGradient"]
    palette = spectral_palette(gradient, "edge")
    projection_bounds = gradient_projection_bounds(vertices, gradient)
    materials = create_particle_materials(
        "shared-object-space-spectral-edge-particle",
        palette,
        style["edgeParticleStrength"],
        style["edgeParticleStrength"],
    )
    centers = []
    edge_counts = []
    for edge in edges:
        a, b = (vertices[index] for index in edge)
        chosen_slots = sorted(rng.sample(range(slots_per_edge), particles_per_edge))
        edge_counts.append(len(chosen_slots))
        for slot in chosen_slots:
            ratio = (slot + 0.5 + rng.uniform(-0.24, 0.24)) / slots_per_edge
            point = tuple(a[axis] + (b[axis] - a[axis]) * ratio for axis in range(3))
            size = rng.uniform(
                style["edgeParticleSizeMin"], style["edgeParticleSizeMax"]
            )
            material_index = spectral_material_index(point, gradient, projection_bounds)
            centers.append((*point, size, material_index))
    halo_centers = [
        (x, y, z, size * style["edgeHaloSizeMultiplier"], material_index)
        for index, (x, y, z, size, material_index) in enumerate(centers)
        if index % style["edgeHaloStride"] == 0
    ]
    rng.shuffle(centers)
    rng.shuffle(halo_centers)
    particles = create_particle_mesh(
        EDGE_PARTICLES_NAME,
        centers,
        materials,
        collection,
        parent,
        "broken-edge-particles",
    )
    particles["edge_counts"] = edge_counts
    particles["slots_per_edge"] = slots_per_edge
    particles["palette_distribution"] = "OBJECT_SPACE_SPECTRAL"

    if not style["edgeHaloInheritsParticleColor"]:
        raise RuntimeError("Every sparse halo particle must inherit its edge particle color.")
    halo_materials = create_particle_materials(
        "shared-object-space-spectral-edge-halo-particle",
        spectral_palette(gradient, "halo"),
        style["edgeHaloStrength"],
        style["edgeHaloStrength"],
        style["edgeHaloOpacity"],
    )
    halo = create_particle_mesh(
        EDGE_HALO_PARTICLES_NAME,
        halo_centers,
        halo_materials,
        collection,
        parent,
        "sparse-edge-halo-particles",
    )
    return particles, halo


def look_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def configure_camera(style):
    camera_data = bpy.data.cameras.new("orthographic-camera")
    camera = bpy.data.objects.new("orthographic-camera", camera_data)
    azimuth = math.radians(style["cameraAzimuthDegrees"])
    elevation = math.radians(style["cameraElevationDegrees"])
    distance_value = style["cameraDistance"]
    horizontal = distance_value * math.cos(elevation)
    camera.location = (
        horizontal * math.cos(azimuth),
        horizontal * math.sin(azimuth),
        distance_value * math.sin(elevation),
    )
    look_at(camera, style["cameraTarget"])
    camera_data.type = style["cameraProjection"]
    camera_data.ortho_scale = style["orthographicScale"]
    camera_data.lens = 50
    camera_data.clip_start = 0.1
    camera_data.clip_end = 100
    bpy.context.scene.collection.objects.link(camera)
    bpy.context.scene.camera = camera
    return camera


def configure_render(profile, style, output_path):
    if profile["width"] != 360 or profile["height"] != 640:
        raise RuntimeError("High-resolution rendering is outside experiment 016 scope.")
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.eevee.taa_render_samples = profile["samples"]
    scene.eevee.taa_samples = min(profile["samples"], 16)
    scene.render.resolution_x = profile["width"]
    scene.render.resolution_y = profile["height"]
    scene.render.resolution_percentage = 100
    scene.render.pixel_aspect_x = 1.0
    scene.render.pixel_aspect_y = 1.0
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
    frame_count = round(profile["fps"] * profile["seconds"])
    scene.frame_end = scene.frame_start + frame_count - 1
    scene["frame_count"] = frame_count
    scene["conceptual_loop_frame"] = scene.frame_start + frame_count

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


def animate_rotation(rig, profile, style, geometry):
    scene = bpy.context.scene
    frame_count = scene["frame_count"]
    loop_frame = scene["conceptual_loop_frame"]
    turns = profile["seconds"] / style["rotationCycleSeconds"]
    if turns != 2:
        raise RuntimeError("The preview must contain exactly two complete turns.")
    initial_phase = math.radians(geometry["initialPhaseDegrees"])
    rig.rotation_euler = (0.0, 0.0, initial_phase)
    rig.keyframe_insert(data_path="rotation_euler", frame=scene.frame_start)
    final_video_angle = initial_phase + turns * math.tau * (frame_count - 1) / frame_count
    rig.rotation_euler = (0.0, 0.0, final_video_angle)
    rig.keyframe_insert(data_path="rotation_euler", frame=scene.frame_end)
    rig.rotation_euler = (0.0, 0.0, initial_phase)
    rig.keyframe_insert(data_path="rotation_euler", frame=loop_frame)
    rig["frame_count_without_duplicate_tail"] = frame_count
    rig["conceptual_loop_frame"] = loop_frame
    rig["turns"] = turns
    rig["initial_phase_degrees"] = geometry["initialPhaseDegrees"]
    set_linear_interpolation(rig)


def validate_geometry(compound, geometry):
    vertices = compound["vertices"]
    edges = compound["edges"]
    faces = compound["faces"]
    if len(vertices) != 8 or len(edges) != 12 or len(faces) != 8:
        raise RuntimeError("The compound must contain 8 external vertices, 12 edges, and 8 faces.")
    if len({point_key(point) for point in vertices}) != 8:
        raise RuntimeError("All eight external vertices must be unique.")
    if set(compound["tetraA"]) & set(compound["tetraB"]):
        raise RuntimeError("The tetrahedra may not share external vertices.")
    for indices, tetra_edges, tetra_faces_value in (
        (compound["tetraA"], compound["edgesA"], compound["facesA"]),
        (compound["tetraB"], compound["edgesB"], compound["facesB"]),
    ):
        if len(indices) - len(tetra_edges) + len(tetra_faces_value) != 2:
            raise RuntimeError("Each tetrahedron must have Euler characteristic 2.")
        degree = {index: 0 for index in indices}
        for first, second in tetra_edges:
            if first not in degree or second not in degree:
                raise RuntimeError("A-B connecting edges are forbidden.")
            degree[first] += 1
            degree[second] += 1
        if set(degree.values()) != {3}:
            raise RuntimeError("Every tetrahedron vertex must have degree three.")

    expected_edge_length = 2 * math.sqrt(2) * geometry["cubeHalfExtent"]
    if any(abs(distance(vertices[a], vertices[b]) - expected_edge_length) > 1e-10 for a, b in edges):
        raise RuntimeError("All twelve edges must have length 2*sqrt(2)*a.")
    expected_area = 2 * math.sqrt(3) * geometry["cubeHalfExtent"] ** 2
    for face in faces:
        a, b, c = (vertices[index] for index in face)
        if abs(triangle_area(a, b, c) - expected_area) > 1e-10:
            raise RuntimeError("All eight large triangular faces must be equal and equilateral.")
        if dot(face_normal(face, vertices), face_centroid(face, vertices)) <= 1e-10:
            raise RuntimeError("Every tetrahedron face normal must point outward.")

    e_x, e_y, e_z = display_basis()
    if any(abs(magnitude(axis) - 1) > 1e-12 for axis in (e_x, e_y, e_z)):
        raise RuntimeError("The display basis must use unit vectors.")
    if any(abs(value) > 1e-12 for value in (dot(e_x, e_y), dot(e_x, e_z), dot(e_y, e_z))):
        raise RuntimeError("The display basis must be orthogonal.")
    if distance(cross(e_x, e_y), e_z) > 1e-12:
        raise RuntimeError("The display basis must be right-handed.")
    mapped_diagonal = transform_to_display((1.0, 1.0, 1.0))
    if distance(mapped_diagonal, (0.0, 0.0, math.sqrt(3))) > 1e-12:
        raise RuntimeError("The (1,1,1) diagonal must map exactly to world +Z.")

    a = geometry["cubeHalfExtent"]
    z_values = sorted(point[2] for point in vertices)
    expected_z = [-math.sqrt(3) * a] + [-a / math.sqrt(3)] * 3 + [a / math.sqrt(3)] * 3 + [math.sqrt(3) * a]
    if any(abs(actual - expected) > 1e-10 for actual, expected in zip(z_values, expected_z)):
        raise RuntimeError("The transformed vertices do not occupy the required four Z levels.")

    intersections = compound["intersections"]
    if len(intersections) != 6 or len({point_key(item["point"]) for item in intersections}) != 6:
        raise RuntimeError("Exactly six unique internal A-B edge intersections are required.")
    expected_centers = {
        point_key(transform_to_display(point))
        for point in ((a, 0, 0), (-a, 0, 0), (0, a, 0), (0, -a, 0), (0, 0, a), (0, 0, -a))
    }
    if {point_key(item["point"]) for item in intersections} != expected_centers:
        raise RuntimeError("Intersections must equal the six transformed cube-face centers.")
    vertex_keys = {point_key(point) for point in vertices}
    for intersection in intersections:
        if abs(intersection["tA"] - 0.5) > 1e-10 or abs(intersection["tB"] - 0.5) > 1e-10:
            raise RuntimeError("Each A-B intersection must bisect both edges.")
        if point_key(intersection["point"]) in vertex_keys:
            raise RuntimeError("Internal intersections may not be promoted to external vertices.")


def validate_scene_contract(compound, style, rig):
    edge_particles = bpy.data.objects.get(EDGE_PARTICLES_NAME)
    edge_halo_particles = bpy.data.objects.get(EDGE_HALO_PARTICLES_NAME)
    face_base_dust = bpy.data.objects.get(FACE_BASE_DUST_NAME)
    face_color_grains = bpy.data.objects.get(FACE_COLOR_GRAINS_NAME)
    curve_objects = [obj for obj in bpy.data.objects if obj.type == "CURVE"]
    mesh_objects = [obj for obj in bpy.data.objects if obj.type == "MESH"]
    gradient = style["spectralGradient"]
    if not style["showBackEdges"] or not style["sameMaterialForBothTetrahedra"]:
        raise RuntimeError("Every edge from both tetrahedra must remain equally visible.")
    if not style["continuousIntersectionEdges"] or style["overUnderCues"]:
        raise RuntimeError("Intersection edges must remain continuous without over/under cues.")
    if style["largeFacePanels"] or style["edgeCurves"]:
        raise RuntimeError("Continuous edge curves and transparent face panels are forbidden.")
    if not style["particleSurface"]:
        raise RuntimeError("The 011-style surface must be assembled from opaque particles.")
    if style["solidNonconvexShell"]:
        raise RuntimeError("A reconstructed 24-face nonconvex shell remains forbidden.")
    if style["directionalLighting"] or len(bpy.data.lights) != 0:
        raise RuntimeError("Directional lighting and shadows are forbidden.")
    if style["depthColorGradient"] or style["independentParticleMotion"]:
        raise RuntimeError("Depth color and independent particle motion are forbidden.")
    if style["vertexAccents"] or style["intersectionAccents"]:
        raise RuntimeError("Large vertex and intersection accents are forbidden.")
    if style["interiorDustCount"] != 0:
        raise RuntimeError("Interior dust is disabled for the approved sparse treatment.")
    if gradient["mode"] != "OBJECT_SPACE_LINEAR_CYCLIC":
        raise RuntimeError("The reference treatment requires one object-space cyclic gradient.")
    if gradient["bandCount"] < 18 or gradient["cyclesAcrossObject"] <= 0:
        raise RuntimeError("The spectral field needs enough bands and a positive cycle count.")
    if not gradient["sameFieldForAllParticles"]:
        raise RuntimeError("Both tetrahedra and all particle layers must share one gradient field.")
    if gradient["cameraDriven"] or gradient["depthDriven"] or gradient["animated"]:
        raise RuntimeError("The gradient may not depend on camera, depth, or time.")
    if curve_objects:
        raise RuntimeError("No directly drawn curve object may remain in the particle treatment.")
    if any(
        obj is None
        for obj in (edge_particles, edge_halo_particles, face_base_dust, face_color_grains)
    ):
        raise RuntimeError("Edge, inherited halo, base dust, and color-grain meshes are required.")
    if edge_particles.get("particle_count") != style["edgeParticleCount"]:
        raise RuntimeError("Edge-particle count does not match the low-resolution contract.")
    if len(set(edge_particles.get("edge_counts"))) != 1:
        raise RuntimeError("All twelve edges must receive equal particle counts.")
    if edge_particles.get("palette_distribution") != "OBJECT_SPACE_SPECTRAL":
        raise RuntimeError("Every edge must sample the shared object-space spectral field.")
    if len(edge_particles.data.materials) != gradient["bandCount"]:
        raise RuntimeError("The edge mesh must expose every spectral gradient band.")
    expected_halo_count = math.ceil(style["edgeParticleCount"] / style["edgeHaloStride"])
    if edge_halo_particles.get("particle_count") != expected_halo_count:
        raise RuntimeError("Sparse edge-halo particle count does not match its stride.")
    if not style["edgeHaloInheritsParticleColor"]:
        raise RuntimeError("Edge halo colors must inherit the three-color edge palette.")
    if len(edge_halo_particles.data.materials) != gradient["bandCount"]:
        raise RuntimeError("The sparse halo must expose the same hue bands as the edges.")
    layers = style["faceParticleLayers"]
    if sum(layer["count"] for layer in layers.values()) != style["faceParticleCount"]:
        raise RuntimeError("Opaque face-particle layers do not match the approved total.")
    for obj, layer_name in (
        (face_base_dust, "baseDust"),
        (face_color_grains, "colorGrains"),
    ):
        layer = layers[layer_name]
        if obj.get("particle_count") != layer["count"]:
            raise RuntimeError(f"{layer_name} count does not match its layer contract.")
        if max(obj.get("face_counts")) - min(obj.get("face_counts")) > 1:
            raise RuntimeError(f"Equal-area faces may differ by at most one {layer_name} particle.")
        if layer["colorMode"] != "OBJECT_SPACE_SPECTRAL":
            raise RuntimeError(f"{layer_name} must sample the object-space spectral field.")
        if obj.get("palette_distribution") != "OBJECT_SPACE_SPECTRAL":
            raise RuntimeError(f"Every large face must share the {layer_name} gradient field.")
        if len(obj.data.materials) != gradient["bandCount"]:
            raise RuntimeError(f"Every face must expose all {layer_name} gradient bands.")
    visible_objects = [edge_particles, edge_halo_particles, face_base_dust, face_color_grains]
    if any(obj.parent != rig for obj in visible_objects):
        raise RuntimeError("Every visible element must be a direct child of the single rigid rig.")
    if any(obj.animation_data is not None for obj in visible_objects):
        raise RuntimeError("Visible elements may not animate independently.")
    if set(mesh_objects) != {
        edge_particles,
        edge_halo_particles,
        face_base_dust,
        face_color_grains,
    }:
        raise RuntimeError("Only particle meshes may exist in the 011-style treatment.")
    if bpy.context.scene.camera.data.type != "ORTHO":
        raise RuntimeError("The illusion requires an orthographic camera.")


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pixel_hash(path):
    image = bpy.data.images.load(str(path), check_existing=False)
    pixels = array("f", [0.0]) * (image.size[0] * image.size[1] * 4)
    image.pixels.foreach_get(pixels)
    digest = hashlib.sha256(pixels.tobytes()).hexdigest()
    bpy.data.images.remove(image)
    return digest


def build_contact_sheet(image_paths, output_path, columns, sheet_name):
    images = [bpy.data.images.load(str(path), check_existing=False) for path in image_paths]
    width = images[0].size[0]
    height = images[0].size[1]
    rows = math.ceil(len(images) / columns)
    sheet_width = width * columns
    sheet_height = height * rows
    sheet_pixels = array("f", [0.0]) * (sheet_width * sheet_height * 4)
    hashes = {}
    for image_index, image in enumerate(images):
        source_pixels = array("f", [0.0]) * (width * height * 4)
        image.pixels.foreach_get(source_pixels)
        hashes[image_paths[image_index].stem] = hashlib.sha256(source_pixels.tobytes()).hexdigest()
        column = image_index % columns
        row_from_top = image_index // columns
        destination_row = rows - 1 - row_from_top
        row_length = width * 4
        for source_row in range(height):
            source_start = source_row * row_length
            target_y = destination_row * height + source_row
            destination_start = (target_y * sheet_width + column * width) * 4
            sheet_pixels[destination_start : destination_start + row_length] = source_pixels[
                source_start : source_start + row_length
            ]
    sheet = bpy.data.images.new(
        sheet_name,
        width=sheet_width,
        height=sheet_height,
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
    return hashes


def phase_label(phase):
    return f"{int(phase):03d}" if float(phase).is_integer() else f"{phase:05.1f}".replace(".", "p")


def render_png(scene, path):
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def project_point(point, rotation_degrees, style):
    angle = math.radians(rotation_degrees)
    cosine = math.cos(angle)
    sine = math.sin(angle)
    rotated = (
        point[0] * cosine - point[1] * sine,
        point[0] * sine + point[1] * cosine,
        point[2],
    )
    elevation = math.radians(style["cameraElevationDegrees"])
    azimuth = math.radians(style["cameraAzimuthDegrees"])
    view_from = (
        math.cos(elevation) * math.cos(azimuth),
        math.cos(elevation) * math.sin(azimuth),
        math.sin(elevation),
    )
    right = normalize((-view_from[1], view_from[0], 0.0))
    up = cross(view_from, right)
    return dot(rotated, right), dot(rotated, up)


def projection_coverage(vertices, style, profile):
    maximum_width = 0.0
    maximum_height = 0.0
    for phase in range(360):
        projected = [project_point(point, phase, style) for point in vertices]
        xs = [point[0] for point in projected]
        ys = [point[1] for point in projected]
        maximum_width = max(maximum_width, max(xs) - min(xs))
        maximum_height = max(maximum_height, max(ys) - min(ys))
    return {
        "maximumProjectedWidth": maximum_width,
        "horizontalCapacity": style["orthographicScale"] * profile["width"] / profile["height"],
        "maximumProjectedHeight": maximum_height,
        "verticalCapacity": style["orthographicScale"],
        "maximumVerticalOccupancy": maximum_height / style["orthographicScale"],
    }


def serializable_intersections(intersections):
    return [
        {
            "point": list(item["point"]),
            "edgeA": list(item["edgeA"]),
            "edgeB": list(item["edgeB"]),
            "tA": item["tA"],
            "tB": item["tB"],
        }
        for item in intersections
    ]


def write_inspection(
    project_root,
    profile,
    style,
    geometry,
    compound,
    phase_paths,
    phase_hashes,
    motion_paths,
    motion_hashes,
    loop_hashes,
):
    inspection = {
        "geometry": {
            "externalVertexCount": len(compound["vertices"]),
            "structuralEdgeCount": len(compound["edges"]),
            "largeTriangleFaceCount": len(compound["faces"]),
            "tetraA": {"vertices": 4, "edges": 6, "faces": 4, "euler": 2},
            "tetraB": {"vertices": 4, "edges": 6, "faces": 4, "euler": 2},
            "sharedExternalVertexCount": 0,
            "abConnectingEdgeCount": 0,
            "cubeHalfExtent": geometry["cubeHalfExtent"],
            "edgeLength": 2 * math.sqrt(2) * geometry["cubeHalfExtent"],
            "largeTriangleArea": 2 * math.sqrt(3) * geometry["cubeHalfExtent"] ** 2,
            "displayBasis": [list(axis) for axis in display_basis()],
            "worldRotationAxis": "Z",
            "sourceDiagonalMappedToWorldZ": [1, 1, 1],
            "threefoldSymmetry": True,
            "intersectionCount": len(compound["intersections"]),
            "intersectionsAreStructuralVertices": False,
            "intersectionsSplitEdges": False,
            "intersections": serializable_intersections(compound["intersections"]),
        },
        "renderContract": {
            "resolution": [profile["width"], profile["height"]],
            "fps": profile["fps"],
            "seconds": profile["seconds"],
            "samples": profile["samples"],
            "profileNames": ["preview"],
            "highResolutionProfileExists": False,
            "highResolutionRenderAttempted": False,
            "cameraType": bpy.context.scene.camera.data.type,
            "cameraAzimuthDegrees": style["cameraAzimuthDegrees"],
            "cameraElevationDegrees": style["cameraElevationDegrees"],
            "orthographicScale": style["orthographicScale"],
            "lightCount": len(bpy.data.lights),
            "showBackEdges": style["showBackEdges"],
            "sameMaterialForBothTetrahedra": style["sameMaterialForBothTetrahedra"],
            "continuousIntersectionEdges": style["continuousIntersectionEdges"],
            "overUnderCues": style["overUnderCues"],
            "largeFacePanels": style["largeFacePanels"],
            "edgeCurves": style["edgeCurves"],
            "particleSurface": style["particleSurface"],
            "solidNonconvexShell": style["solidNonconvexShell"],
            "edgeCurveCount": len([obj for obj in bpy.data.objects if obj.type == "CURVE"]),
            "facePanelObjectPresent": False,
            "edgeParticleCount": style["edgeParticleCount"],
            "edgeParticleSlotsPerEdge": style["edgeParticleSlotsPerEdge"],
            "spectralGradient": {
                "mode": style["spectralGradient"]["mode"],
                "direction": style["spectralGradient"]["direction"],
                "cyclesAcrossObject": style["spectralGradient"]["cyclesAcrossObject"],
                "phase": style["spectralGradient"]["phase"],
                "bandCount": style["spectralGradient"]["bandCount"],
                "sameFieldForAllParticles": style["spectralGradient"][
                    "sameFieldForAllParticles"
                ],
                "cameraDriven": style["spectralGradient"]["cameraDriven"],
                "depthDriven": style["spectralGradient"]["depthDriven"],
                "animated": style["spectralGradient"]["animated"],
            },
            "edgePaletteDistribution": "OBJECT_SPACE_SPECTRAL",
            "edgeHaloParticleCount": math.ceil(
                style["edgeParticleCount"] / style["edgeHaloStride"]
            ),
            "edgeHaloInheritsParticleColor": style["edgeHaloInheritsParticleColor"],
            "faceParticleCount": style["faceParticleCount"],
            "faceParticleLayers": {
                name: {
                    "count": layer["count"],
                    "colorMode": layer["colorMode"],
                    "gradientStyle": layer["gradientStyle"],
                    "strength": layer["strength"],
                    "sizeRange": [layer["sizeMin"], layer["sizeMax"]],
                    "distribution": "OBJECT_SPACE_SPECTRAL",
                }
                for name, layer in style["faceParticleLayers"].items()
            },
            "faceParticlesOpaque": True,
            "interiorDustCount": style["interiorDustCount"],
            "vertexAccents": style["vertexAccents"],
            "intersectionAccents": style["intersectionAccents"],
            "independentParticleMotion": style["independentParticleMotion"],
            "projectionCoverage": projection_coverage(compound["vertices"], style, profile),
        },
        "animation": {
            "frameStart": bpy.context.scene.frame_start,
            "frameEnd": bpy.context.scene.frame_end,
            "frameCount": bpy.context.scene["frame_count"],
            "conceptualLoopFrame": bpy.context.scene["conceptual_loop_frame"],
            "initialPhaseDegrees": geometry["initialPhaseDegrees"],
            "rotationCycleSeconds": style["rotationCycleSeconds"],
            "totalTurns": profile["seconds"] / style["rotationCycleSeconds"],
            "interpolation": "LINEAR",
            "videoContainsDuplicateTailFrame": False,
            "firstFramePixelHash": loop_hashes["start"],
            "conceptualLoopFramePixelHash": loop_hashes["next"],
            "firstMatchesConceptualLoopFrame": loop_hashes["start"] == loop_hashes["next"],
        },
        "stills": {
            "files": [str(path.relative_to(project_root)) for path in phase_paths],
            "fileHashes": {path.stem: sha256(path) for path in phase_paths},
            "pixelHashes": phase_hashes,
            "zeroMatches360": phase_hashes["phase-000"] == phase_hashes["phase-360"],
            "contactSheet": "output/stills/stella-octangula-contact-sheet.png",
        },
        "motionContact": {
            "sampleCount": len(motion_paths),
            "pixelHashes": motion_hashes,
            "contactSheet": "output/stella-octangula-motion-contact-sheet.png",
        },
    }
    inspection_path = project_root / "output" / "inspection.json"
    inspection_path.write_text(json.dumps(inspection, indent=2), encoding="utf-8")


def render_stills(project_root, rig, profile, style, geometry, compound):
    scene = bpy.context.scene
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    still_directory = project_root / "output" / "stills"
    motion_directory = still_directory / "motion"
    still_directory.mkdir(parents=True, exist_ok=True)
    motion_directory.mkdir(parents=True, exist_ok=True)

    phase_paths = []
    action = rig.animation_data.action
    rig.animation_data.action = None
    try:
        zero_phase_path = None
        for phase in style["phaseDegrees"]:
            label = phase_label(phase)
            still_path = still_directory / f"phase-{label}.png"
            if phase == 360:
                if zero_phase_path is None:
                    raise RuntimeError("The 0-degree phase must precede 360 degrees.")
                shutil.copyfile(zero_phase_path, still_path)
            else:
                rig.rotation_euler = (0.0, 0.0, math.radians(phase))
                bpy.context.view_layer.update()
                render_png(scene, still_path)
                if phase == 0:
                    zero_phase_path = still_path
            phase_paths.append(still_path)
    finally:
        rig.animation_data.action = action
        scene.frame_set(scene.frame_start)

    phase_contact_path = still_directory / "stella-octangula-contact-sheet.png"
    phase_hashes = build_contact_sheet(
        phase_paths,
        phase_contact_path,
        len(phase_paths),
        "stella-octangula-phase-contact-sheet",
    )
    if phase_hashes["phase-000"] != phase_hashes["phase-360"]:
        raise RuntimeError("The 0-degree and 360-degree stills must be pixel-identical.")

    motion_paths = []
    frames_per_cycle = round(profile["fps"] * style["rotationCycleSeconds"])
    for index in range(style["motionContactFrameCount"]):
        frame = scene.frame_start + round(index * frames_per_cycle / style["motionContactFrameCount"])
        scene.frame_set(frame)
        motion_path = motion_directory / f"motion-{index + 1:03d}-frame-{frame:03d}.png"
        render_png(scene, motion_path)
        motion_paths.append(motion_path)
    motion_contact_path = project_root / "output" / "stella-octangula-motion-contact-sheet.png"
    motion_hashes = build_contact_sheet(
        motion_paths,
        motion_contact_path,
        style["motionContactColumns"],
        "stella-octangula-motion-contact-sheet",
    )

    loop_hashes = {}
    for label, frame in (("start", scene.frame_start), ("next", scene["conceptual_loop_frame"])):
        scene.frame_set(frame)
        endpoint_path = still_directory / f"loop-{label}-frame.png"
        render_png(scene, endpoint_path)
        loop_hashes[label] = pixel_hash(endpoint_path)
    if loop_hashes["start"] != loop_hashes["next"]:
        raise RuntimeError("The conceptual frame after the video must match frame one.")

    write_inspection(
        project_root,
        profile,
        style,
        geometry,
        compound,
        phase_paths,
        phase_hashes,
        motion_paths,
        motion_hashes,
        loop_hashes,
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
    collection = make_collection("wireframe-stella-octangula-depth-rotation-illusion")
    rig = bpy.data.objects.new(RIG_NAME, None)
    collection.objects.link(rig)
    compound = create_geometry(geometry)
    validate_geometry(compound, geometry)
    create_edge_particles(compound["vertices"], compound["edges"], style, collection, rig)
    create_face_surface(compound["vertices"], compound["faces"], style, collection, rig)
    configure_camera(style)
    configure_render(profile, style, output_path)
    animate_rotation(rig, profile, style, geometry)
    validate_scene_contract(compound, style, rig)

    if not args.stills and not args.render:
        bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    elif args.stills:
        render_stills(project_root, rig, profile, style, geometry, compound)
    else:
        bpy.ops.render.render(animation=True)


if __name__ == "__main__":
    main()
