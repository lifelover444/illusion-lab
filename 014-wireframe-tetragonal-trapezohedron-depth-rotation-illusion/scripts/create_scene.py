import argparse
from array import array
import bisect
import hashlib
import json
import math
import random
import shutil
import sys
from pathlib import Path

import bpy
from mathutils import Vector


SCENE_FILENAME = "wireframe-tetragonal-trapezohedron-depth-rotation-illusion.blend"
RIG_NAME = "tetragonal-trapezohedron-rigid-rotation"
FACE_DUST_NAME = "tetragonal-trapezohedron-face-stardust"
FACE_PANEL_NAME = "tetragonal-trapezohedron-transparent-face-panel"
GUIDE_LINE_PREFIX = "tetragonal-trapezohedron-ghost-guide"
EDGE_FILAMENT_NAME = "tetragonal-trapezohedron-broken-edge-filaments"
EDGE_HALO_NAME = "tetragonal-trapezohedron-sparse-edge-halo"
AXIAL_STAR_STREAM_PREFIX = "tetragonal-trapezohedron-axial-star-stream"
GALAXY_DUST_PREFIX = "tetragonal-trapezohedron-galaxy-dust"
VERTEX_CRYSTALS_NAME = "tetragonal-trapezohedron-vertex-crystals"
SILHOUETTE_MASK_NAME = "tetragonal-trapezohedron-silhouette-mask"
ROOT_COLLECTION_NAME = "wireframe-tetragonal-trapezohedron-depth-rotation-illusion"
SURFACE_COLLECTION_NAME = "surface-depth-layer"
EDGE_DETAIL_COLLECTION_NAME = "depth-independent-edge-detail-layer"
GUIDE_COLLECTION_NAME = "depth-independent-guide-mask-layer"
SILHOUETTE_COLLECTION_NAME = "outer-silhouette-mask-layer"
SURFACE_VIEW_LAYER_NAME = "Surface"
EDGE_DETAIL_VIEW_LAYER_NAME = "EdgeDetail"
GUIDE_VIEW_LAYER_NAME = "GuideMask"
SILHOUETTE_VIEW_LAYER_NAME = "SilhouetteMask"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Create the wireframe tetragonal trapezohedron depth illusion."
    )
    parser.add_argument("--profile", choices=("preview", "final"), default="preview")
    parser.add_argument("--project-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--stills", action="store_true")
    script_args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(script_args)


def load_config():
    config_path = Path(__file__).resolve().parent / "tetragonal-trapezohedron-config.json"
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


def make_collection(name, parent=None):
    collection = bpy.data.collections.new(name)
    if parent is None:
        bpy.context.scene.collection.children.link(collection)
    else:
        parent.children.link(collection)
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


def magnitude(vector):
    return math.sqrt(dot(vector, vector))


def normalize(vector):
    length = magnitude(vector)
    if length <= 1e-12:
        return (0.0, 0.0, 1.0)
    return tuple(component / length for component in vector)


def face_normal(face, vertices):
    a, b, c = (vertices[index] for index in face[:3])
    return cross(subtract(b, a), subtract(c, a))


def face_centroid(face, vertices):
    return tuple(sum(vertices[index][axis] for index in face) / 4 for axis in range(3))


def orient_outward(face, vertices):
    if dot(face_normal(face, vertices), face_centroid(face, vertices)) > 0:
        return face
    return face[0], face[3], face[2], face[1]


def triangle_area(a, b, c):
    return magnitude(cross(subtract(b, a), subtract(c, a))) / 2


def quad_area(face, vertices):
    a, b, c, d = (vertices[index] for index in face)
    return triangle_area(a, b, c) + triangle_area(a, c, d)


def face_planarity_error(face, vertices):
    a, b, c, d = (vertices[index] for index in face)
    normal = cross(subtract(b, a), subtract(c, a))
    return abs(dot(normal, subtract(d, a))) / magnitude(normal)


def canonical_edge(edge):
    return tuple(sorted(edge))


def create_geometry(geometry):
    if abs(geometry["lowerRingTwistDegrees"] - 45) > 1e-12:
        raise RuntimeError("The regular tetragonal trapezohedron requires a 45-degree twist.")
    radius = geometry["waistRadius"]
    half_height = geometry["halfHeight"]
    belt_half_height = half_height * (3 - 2 * math.sqrt(2))
    phase = math.radians(geometry["initialPhaseDegrees"])
    twist = math.radians(geometry["lowerRingTwistDegrees"])
    vertices = [(0.0, 0.0, half_height), (0.0, 0.0, -half_height)]
    for index in range(4):
        angle = phase + index * math.tau / 4
        vertices.append(
            (radius * math.cos(angle), radius * math.sin(angle), belt_half_height)
        )
    for index in range(4):
        angle = phase + twist + index * math.tau / 4
        vertices.append(
            (radius * math.cos(angle), radius * math.sin(angle), -belt_half_height)
        )

    faces = []
    edges = []
    belt_edges = []
    for index in range(4):
        upper = 2 + index
        next_upper = 2 + (index + 1) % 4
        lower = 6 + index
        next_lower = 6 + (index + 1) % 4
        edges.extend(((0, upper), (1, lower), (lower, upper), (lower, next_upper)))
        belt_edges.extend(((lower, upper), (lower, next_upper)))
        faces.append(orient_outward((0, upper, lower, next_upper), vertices))
        faces.append(orient_outward((1, lower, next_upper, next_lower), vertices))
    return vertices, faces, edges, belt_edges, belt_half_height


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


def make_face_panel_material(style):
    panel = style["facePanel"]
    material = bpy.data.materials.new("uniform-dark-ice-blue-face-panel")
    material.use_nodes = True
    material.diffuse_color = (*panel["color"], panel["alpha"])
    material.surface_render_method = panel["renderMethod"]
    material.use_transparency_overlap = panel["transparencyOverlap"]
    material.show_transparent_back = panel["doubleSided"]

    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    transparent = nodes.new("ShaderNodeBsdfTransparent")
    emission = nodes.new("ShaderNodeEmission")
    mix_shader = nodes.new("ShaderNodeMixShader")
    transparent.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    emission.inputs["Color"].default_value = (*panel["color"], 1.0)
    emission.inputs["Strength"].default_value = panel["emissionStrength"]
    mix_shader.inputs[0].default_value = panel["alpha"]
    links.new(transparent.outputs[0], mix_shader.inputs[1])
    links.new(emission.outputs[0], mix_shader.inputs[2])
    links.new(mix_shader.outputs[0], output.inputs[0])
    return material


def create_face_panel(vertices, faces, style, collection, parent):
    panel = style["facePanel"]
    if not panel["enabled"]:
        raise RuntimeError("The spatial rotation treatment requires face panels.")
    mesh = bpy.data.meshes.new(FACE_PANEL_NAME)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    for polygon in mesh.polygons:
        polygon.use_smooth = False
    obj = bpy.data.objects.new(FACE_PANEL_NAME, mesh)
    obj.parent = parent
    obj.data.materials.append(make_face_panel_material(style))
    obj["face_count"] = len(faces)
    obj["alpha"] = panel["alpha"]
    obj["transparency"] = 1.0 - panel["alpha"]
    obj["render_method"] = panel["renderMethod"]
    obj["double_sided"] = panel["doubleSided"]
    obj["transparency_overlap"] = panel["transparencyOverlap"]
    obj["cast_shadows"] = panel["castShadows"]
    obj["refraction"] = panel["refraction"]
    obj["fresnel"] = panel["fresnel"]
    collection.objects.link(obj)
    return obj


def create_silhouette_mask(vertices, faces, collection, parent):
    mesh = bpy.data.meshes.new(SILHOUETTE_MASK_NAME)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(SILHOUETTE_MASK_NAME, mesh)
    obj.parent = parent
    obj.data.materials.append(
        make_emission_material("opaque-white-silhouette-mask", (1.0, 1.0, 1.0), 1.0)
    )
    obj["silhouette_mask"] = True
    collection.objects.link(obj)
    return obj


def create_poly_curve(name, points, radius, material, collection, parent):
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 1
    curve.bevel_depth = radius
    curve.bevel_resolution = 1
    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for point, coordinates in zip(spline.points, points):
        point.co = (*coordinates, 1.0)
    obj = bpy.data.objects.new(name, curve)
    obj.parent = parent
    obj.data.materials.append(material)
    obj["guide_line"] = True
    obj["opaque"] = True
    obj["breathing"] = False
    obj["directional_weighting"] = False
    obj["depth_independent"] = True
    obj["panel_occlusion"] = False
    collection.objects.link(obj)
    return obj


def create_guide_lines(vertices, edges, style, collection, parent):
    guide = style["guideLine"]
    if not guide["enabled"]:
        raise RuntimeError("The approved treatment requires faint guide lines.")
    material = make_emission_material(
        "opaque-white-depth-independent-guide-mask",
        (1.0, 1.0, 1.0),
        guide["maskEmissionStrength"],
    )
    objects = []
    for index, edge in enumerate(edges):
        a, b = (vertices[vertex_index] for vertex_index in edge)
        objects.append(
            create_poly_curve(
                f"{GUIDE_LINE_PREFIX}-{index + 1:02d}",
                (a, b),
                guide["radius"],
                material,
                collection,
                parent,
            )
        )
    return objects


def create_particle_materials(prefix, palette, strength_min, strength_max):
    materials = []
    denominator = max(1, len(palette) - 1)
    for index, color in enumerate(palette):
        ratio = index / denominator
        strength = strength_min + (strength_max - strength_min) * ratio
        materials.append(
            make_emission_material(f"{prefix}-{index + 1:02d}", tuple(color), strength)
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


def random_barycentric(rng):
    root = math.sqrt(rng.random())
    second = rng.random()
    return (1.0 - root, root * (1.0 - second), root * second)


def point_segment_distance(point, start, end):
    segment = subtract(end, start)
    length_squared = dot(segment, segment)
    if length_squared <= 1e-24:
        return magnitude(subtract(point, start))
    ratio = max(0.0, min(1.0, dot(subtract(point, start), segment) / length_squared))
    closest = tuple(
        start[axis] + segment[axis] * ratio for axis in range(3)
    )
    return magnitude(subtract(point, closest))


def create_face_stardust(vertices, faces, style, collection, parent):
    rng = random.Random(style["seed"])
    materials = create_particle_materials(
        "face-stardust",
        style["faceParticlePalette"],
        style["faceParticleStrengthMin"],
        style["faceParticleStrengthMax"],
    )
    triangles = []
    cumulative_areas = []
    total_area = 0.0
    for face in faces:
        for triangle in ((face[0], face[1], face[2]), (face[0], face[2], face[3])):
            a, b, c = (vertices[index] for index in triangle)
            total_area += triangle_area(a, b, c)
            triangles.append((triangle, face, normalize(face_normal(face, vertices))))
            cumulative_areas.append(total_area)

    centers = []
    while len(centers) < style["faceParticleCount"]:
        selection = rng.random() * total_area
        triangle_index = bisect.bisect_left(cumulative_areas, selection)
        triangle, face, normal = triangles[min(triangle_index, len(triangles) - 1)]
        a, b, c = (vertices[index] for index in triangle)
        weights = random_barycentric(rng)
        surface_point = tuple(
            a[axis] * weights[0]
            + b[axis] * weights[1]
            + c[axis] * weights[2]
            for axis in range(3)
        )
        face_edges = (
            (face[index], face[(index + 1) % len(face)])
            for index in range(len(face))
        )
        boundary_distance = min(
            point_segment_distance(
                surface_point, vertices[start_index], vertices[end_index]
            )
            for start_index, end_index in face_edges
        )
        if (
            boundary_distance < style["faceParticleEdgeTrenchWidth"]
            and rng.random() < style["faceParticleEdgeTrenchDensityReduction"]
        ):
            continue
        jitter = rng.uniform(
            -style["faceParticleJitter"], style["faceParticleJitter"]
        )
        point = tuple(
            surface_point[axis] + normal[axis] * jitter
            for axis in range(3)
        )
        size_ratio = rng.random() ** style["faceParticleSizeExponent"]
        size = style["faceParticleSizeMin"] + (
            style["faceParticleSizeMax"] - style["faceParticleSizeMin"]
        ) * size_ratio
        centers.append((*point, size, rng.randrange(len(materials))))
    return create_particle_mesh(FACE_DUST_NAME, centers, materials, collection, parent)


def create_edge_filaments(vertices, edges, style, collection, parent):
    rng = random.Random(style["seed"] + 404)
    core_material = make_emission_material(
        "broken-cool-lavender-edge-filament",
        style["edgeFilamentColor"],
        style["edgeFilamentStrength"],
    )
    halo_material = make_emission_material(
        "sparse-edge-halo",
        style["edgeHaloColor"],
        style["edgeHaloStrength"],
        style["edgeHaloOpacity"],
    )
    core_centers = []
    total_slots = 0
    for edge in edges:
        a, b = (vertices[vertex_index] for vertex_index in edge)
        outward = normalize(
            tuple((a[axis] + b[axis]) / 2 for axis in range(3))
        )
        slot_count = max(
            2,
            round(
                magnitude(subtract(b, a)) * style["edgeFilamentSlotsPerUnit"]
            ),
        )
        total_slots += slot_count
        for slot_index in range(slot_count):
            if rng.random() > style["edgeFilamentKeepRatio"]:
                continue
            ratio = (
                slot_index
                + 0.5
                + rng.uniform(
                    -style["edgeFilamentSlotJitter"],
                    style["edgeFilamentSlotJitter"],
                )
            ) / slot_count
            point = tuple(
                a[axis]
                + (b[axis] - a[axis]) * ratio
                + outward[axis] * style["edgeFilamentSurfaceOffset"]
                for axis in range(3)
            )
            size = rng.uniform(
                style["edgeFilamentPointSizeMin"],
                style["edgeFilamentPointSizeMax"],
            )
            core_centers.append((*point, size, 0))
    halo_centers = [
        (x, y, z, size * style["edgeHaloSizeMultiplier"], 0)
        for index, (x, y, z, size, _) in enumerate(core_centers)
        if index % style["edgeHaloStride"] == 0
    ]
    core = create_particle_mesh(
        EDGE_FILAMENT_NAME, core_centers, [core_material], collection, parent
    )
    halo = create_particle_mesh(
        EDGE_HALO_NAME, halo_centers, [halo_material], collection, parent
    )
    core["slot_count"] = total_slots
    core["keep_ratio"] = style["edgeFilamentKeepRatio"]
    core["motion"] = "LOCKED"
    halo["source_stride"] = style["edgeHaloStride"]
    halo["motion"] = "LOCKED"
    return core, halo, core_material, halo_material


def point_inside_faces(point, vertices, faces, boundary_padding=0.0):
    for face in faces:
        normal = face_normal(face, vertices)
        origin = vertices[face[0]]
        signed_distance = dot(normal, subtract(point, origin)) / magnitude(normal)
        if signed_distance > -boundary_padding + 1e-12:
            return False
    return True


def create_particle_layer_rig(name, collection, parent):
    rig = bpy.data.objects.new(name, None)
    rig.parent = parent
    collection.objects.link(rig)
    return rig


def create_axial_star_stream(style, collection, parent):
    stream = style["axialStarStream"]
    rng = random.Random(style["seed"] + 9001)
    materials = create_particle_materials(
        "axial-star",
        stream["palette"],
        stream["strengthMin"],
        stream["strengthMax"],
    )
    accent_material = make_emission_material(
        "axial-star-rare-accent",
        (0.82, 0.94, 1.0),
        stream["accentStrength"],
    )
    materials.append(accent_material)
    accent_indices = set(rng.sample(range(stream["count"]), stream["accentCount"]))
    centers = []
    for index in range(stream["count"]):
        # Stratified height placement prevents random knots while retaining gaps.
        ratio = (index + rng.random()) / stream["count"]
        z = -stream["halfHeight"] + ratio * stream["halfHeight"] * 2
        theta = rng.random() * math.tau
        radial = stream["radius"] * math.sqrt(rng.random())
        x = radial * math.cos(theta)
        y = radial * math.sin(theta)
        size_ratio = rng.random() ** 2.4
        size = stream["sizeMin"] + (
            stream["sizeMax"] - stream["sizeMin"]
        ) * size_ratio
        if index in accent_indices:
            size *= 1.12
            material_index = len(materials) - 1
        else:
            material_index = rng.randrange(len(materials) - 1)
        centers.append((x, y, z, size, material_index))
    obj = create_particle_mesh(
        AXIAL_STAR_STREAM_PREFIX,
        centers,
        materials,
        collection,
        parent,
    )
    obj["particle_cloud"] = "axial-star-stream"
    obj["motion"] = "LOCKED"
    return obj


def sample_galaxy_point(rng, galaxy):
    radial_radius = galaxy["radialRadius"]
    vertical_half_height = galaxy["verticalHalfHeight"]
    while True:
        x = rng.gauss(0.0, radial_radius * 0.38)
        y = rng.gauss(0.0, radial_radius * 0.38)
        z = rng.gauss(0.0, vertical_half_height * 0.38)
        normalized = (
            (x / radial_radius) ** 2
            + (y / radial_radius) ** 2
            + (z / vertical_half_height) ** 2
        )
        scaled_distance = math.sqrt(
            x * x
            + y * y
            + (z * radial_radius / vertical_half_height) ** 2
        )
        if normalized <= 1.0 and scaled_distance >= galaxy["coreExclusionRadius"]:
            return x, y, z


def create_galaxy_dust(style, collection, parent):
    galaxy = style["galaxyDust"]
    rng = random.Random(style["seed"] + 12017)
    materials = create_particle_materials(
        "galaxy-dust",
        galaxy["palette"],
        galaxy["strengthMin"],
        galaxy["strengthMax"],
    )
    base_count, remainder = divmod(galaxy["count"], galaxy["layerCount"])
    layer_rigs = []
    for layer_index in range(galaxy["layerCount"]):
        count = base_count + (1 if layer_index < remainder else 0)
        layer_rig = create_particle_layer_rig(
            f"{GALAXY_DUST_PREFIX}-layer-{layer_index + 1:02d}-rig",
            collection,
            parent,
        )
        centers = []
        for _ in range(count):
            x, y, z = sample_galaxy_point(rng, galaxy)
            size_ratio = rng.random() ** 2.7
            size = galaxy["sizeMin"] + (
                galaxy["sizeMax"] - galaxy["sizeMin"]
            ) * size_ratio
            centers.append((x, y, z, size, rng.randrange(len(materials))))
        obj = create_particle_mesh(
            f"{GALAXY_DUST_PREFIX}-layer-{layer_index + 1:02d}",
            centers,
            materials,
            collection,
            layer_rig,
        )
        obj["particle_cloud"] = "central-galaxy-dust"
        layer_rigs.append(layer_rig)
    return layer_rigs


def create_vertex_crystals(vertices, style, collection, parent):
    material = make_emission_material(
        "identical-vertex-crystal",
        style["vertexCrystalColor"],
        style["vertexCrystalStrength"],
    )
    centers = [(*point, style["vertexCrystalSize"], 0) for point in vertices]
    return create_particle_mesh(
        VERTEX_CRYSTALS_NAME, centers, [material], collection, parent
    )


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


def find_layer_collection(layer_collection, collection_name):
    if layer_collection.collection.name == collection_name:
        return layer_collection
    for child in layer_collection.children:
        match = find_layer_collection(child, collection_name)
        if match is not None:
            return match
    return None


def configure_view_layer(scene, name, included_collection_name):
    view_layer = scene.view_layers.get(name)
    if view_layer is None:
        view_layer = scene.view_layers.new(name)
    for collection_name in (
        SURFACE_COLLECTION_NAME,
        EDGE_DETAIL_COLLECTION_NAME,
        GUIDE_COLLECTION_NAME,
        SILHOUETTE_COLLECTION_NAME,
    ):
        layer_collection = find_layer_collection(
            view_layer.layer_collection, collection_name
        )
        if layer_collection is None:
            raise RuntimeError(f"Missing render collection: {collection_name}")
        layer_collection.exclude = collection_name != included_collection_name
    return view_layer


def make_render_layer_node(tree, layer_name, x, y):
    node = tree.nodes.new("CompositorNodeRLayers")
    node.layer = layer_name
    node.location = (x, y)
    return node


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
    scene.render.film_transparent = True
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

    default_view_layer = scene.view_layers[0]
    default_view_layer.name = SURFACE_VIEW_LAYER_NAME
    configure_view_layer(
        scene, SURFACE_VIEW_LAYER_NAME, SURFACE_COLLECTION_NAME
    )
    configure_view_layer(
        scene, EDGE_DETAIL_VIEW_LAYER_NAME, EDGE_DETAIL_COLLECTION_NAME
    )
    configure_view_layer(scene, GUIDE_VIEW_LAYER_NAME, GUIDE_COLLECTION_NAME)
    configure_view_layer(
        scene, SILHOUETTE_VIEW_LAYER_NAME, SILHOUETTE_COLLECTION_NAME
    )

    scene.use_nodes = True
    tree = scene.node_tree
    tree.nodes.clear()
    surface_layers = make_render_layer_node(tree, SURFACE_VIEW_LAYER_NAME, -900, 260)
    edge_layers = make_render_layer_node(
        tree, EDGE_DETAIL_VIEW_LAYER_NAME, -900, 20
    )
    guide_layers = make_render_layer_node(tree, GUIDE_VIEW_LAYER_NAME, -900, -250)
    silhouette_layers = make_render_layer_node(
        tree, SILHOUETTE_VIEW_LAYER_NAME, -900, -520
    )

    surface_glare = tree.nodes.new("CompositorNodeGlare")
    surface_glare.glare_type = "FOG_GLOW"
    surface_glare.quality = "HIGH"
    surface_glare.threshold = style["glowThreshold"]
    surface_glare.size = style["glowSize"]
    surface_glare.location = (-650, 260)
    tree.links.new(surface_layers.outputs["Image"], surface_glare.inputs["Image"])

    edge_glare = tree.nodes.new("CompositorNodeGlare")
    edge_glare.glare_type = "FOG_GLOW"
    edge_glare.quality = "HIGH"
    edge_glare.threshold = style["glowThreshold"]
    edge_glare.size = style["glowSize"]
    edge_glare.location = (-650, 20)
    tree.links.new(edge_layers.outputs["Image"], edge_glare.inputs["Image"])

    add_surface_and_edges = tree.nodes.new("CompositorNodeMixRGB")
    add_surface_and_edges.blend_type = "ADD"
    add_surface_and_edges.inputs[0].default_value = 1.0
    add_surface_and_edges.location = (-390, 150)
    tree.links.new(surface_glare.outputs["Image"], add_surface_and_edges.inputs[1])
    tree.links.new(edge_glare.outputs["Image"], add_surface_and_edges.inputs[2])

    guide_alpha = tree.nodes.new("CompositorNodeMath")
    guide_alpha.operation = "MULTIPLY"
    guide_alpha.use_clamp = True
    guide_alpha.inputs[1].default_value = style["guideLine"]["internalOpacity"]
    guide_alpha.location = (-620, -250)
    tree.links.new(guide_layers.outputs["Alpha"], guide_alpha.inputs[0])

    guide_color = tree.nodes.new("CompositorNodeRGB")
    guide_color.outputs[0].default_value = (*style["guideLine"]["color"], 1.0)
    guide_color.location = (-620, -360)
    guide_overlay = tree.nodes.new("CompositorNodeSetAlpha")
    guide_overlay.location = (-390, -250)
    tree.links.new(guide_color.outputs[0], guide_overlay.inputs["Image"])
    tree.links.new(guide_alpha.outputs[0], guide_overlay.inputs["Alpha"])

    add_guides = tree.nodes.new("CompositorNodeAlphaOver")
    add_guides.inputs[0].default_value = 1.0
    add_guides.location = (-120, 80)
    tree.links.new(add_surface_and_edges.outputs[0], add_guides.inputs[1])
    tree.links.new(guide_overlay.outputs[0], add_guides.inputs[2])

    silhouette_edge = tree.nodes.new("CompositorNodeFilter")
    silhouette_edge.filter_type = "SOBEL"
    silhouette_edge.location = (-620, -520)
    tree.links.new(silhouette_layers.outputs["Alpha"], silhouette_edge.inputs["Image"])

    inner_opacity = style["guideLine"]["internalOpacity"]
    outer_opacity = style["guideLine"]["outerSilhouetteOpacity"]
    outer_boost = (outer_opacity - inner_opacity) / (1.0 - inner_opacity)
    silhouette_alpha = tree.nodes.new("CompositorNodeMath")
    silhouette_alpha.operation = "MULTIPLY"
    silhouette_alpha.use_clamp = True
    silhouette_alpha.inputs[1].default_value = outer_boost
    silhouette_alpha.location = (-390, -520)
    tree.links.new(silhouette_edge.outputs["Image"], silhouette_alpha.inputs[0])

    silhouette_overlay = tree.nodes.new("CompositorNodeSetAlpha")
    silhouette_overlay.location = (-120, -420)
    tree.links.new(guide_color.outputs[0], silhouette_overlay.inputs["Image"])
    tree.links.new(silhouette_alpha.outputs[0], silhouette_overlay.inputs["Alpha"])

    add_silhouette = tree.nodes.new("CompositorNodeAlphaOver")
    add_silhouette.inputs[0].default_value = 1.0
    add_silhouette.location = (130, 40)
    tree.links.new(add_guides.outputs[0], add_silhouette.inputs[1])
    tree.links.new(silhouette_overlay.outputs[0], add_silhouette.inputs[2])

    black = tree.nodes.new("CompositorNodeRGB")
    black.outputs[0].default_value = (*style["backgroundColor"], 1.0)
    black.location = (-120, 280)
    over_black = tree.nodes.new("CompositorNodeAlphaOver")
    over_black.inputs[0].default_value = 1.0
    over_black.location = (370, 40)
    tree.links.new(black.outputs[0], over_black.inputs[1])
    tree.links.new(add_silhouette.outputs[0], over_black.inputs[2])

    composite = tree.nodes.new("CompositorNodeComposite")
    composite.location = (600, 40)
    tree.links.new(over_black.outputs[0], composite.inputs[0])


def set_linear_interpolation(obj):
    if obj.animation_data and obj.animation_data.action:
        for fcurve in obj.animation_data.action.fcurves:
            for keyframe in fcurve.keyframe_points:
                keyframe.interpolation = "LINEAR"


def animate_material_breath(material, profile, base, amount, cycle_seconds):
    emission = next(
        node
        for node in material.node_tree.nodes
        if node.bl_idname == "ShaderNodeEmission"
    )
    strength = emission.inputs["Strength"]
    fps = profile["fps"]
    cycle_count = round(profile["seconds"] / cycle_seconds)
    for cycle in range(cycle_count):
        start = 1 + round(cycle * cycle_seconds * fps)
        quarter = cycle_seconds * fps / 4
        for phase, factor in ((0, 1), (1, 1 + amount), (2, 1), (3, 1 - amount)):
            strength.default_value = base * factor
            strength.keyframe_insert(
                "default_value", frame=start + round(phase * quarter)
            )
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


def animate_rotation(rig, profile, style):
    scene = bpy.context.scene
    frame_count = scene["frame_count"]
    loop_frame = scene["conceptual_loop_frame"]
    turns = profile["seconds"] / style["rotationCycleSeconds"]
    rig.rotation_euler = (0.0, 0.0, 0.0)
    rig.keyframe_insert(data_path="rotation_euler", frame=scene.frame_start)
    final_video_angle = turns * math.tau * (frame_count - 1) / frame_count
    rig.rotation_euler = (0.0, 0.0, final_video_angle)
    rig.keyframe_insert(data_path="rotation_euler", frame=scene.frame_end)
    # The video stops one angular step before closure. The unrendered next frame is
    # normalized to literal zero so equivalent 4*pi floating transforms cannot
    # introduce subpixel raster differences at the loop check.
    rig.rotation_euler = (0.0, 0.0, 0.0)
    rig.keyframe_insert(data_path="rotation_euler", frame=loop_frame)
    rig["frame_count_without_duplicate_tail"] = frame_count
    rig["conceptual_loop_frame"] = loop_frame
    rig["turns"] = turns
    set_linear_interpolation(rig)


def animate_vertical_particle_layers(layer_rigs, profile, style, cloud_key, seed_offset):
    cloud = style[cloud_key]
    scene = bpy.context.scene
    frames_per_cycle = round(profile["fps"] * cloud["periodSeconds"])
    if frames_per_cycle <= 0:
        raise RuntimeError("Particle drift period must contain at least one frame.")
    rng = random.Random(style["seed"] + seed_offset)
    layer_count = len(layer_rigs)
    for layer_index, rig in enumerate(layer_rigs):
        ratio = layer_index / max(1, layer_count - 1)
        amplitude = cloud["verticalAmplitudeMin"] + (
            cloud["verticalAmplitudeMax"] - cloud["verticalAmplitudeMin"]
        ) * ratio
        phase = (
            math.tau * layer_index / layer_count + rng.uniform(-0.12, 0.12)
        )
        signal = (
            f"sin({math.tau:.15f} * ((frame - {scene.frame_start}) % "
            f"{frames_per_cycle}) / {frames_per_cycle} + {phase:.15f})"
        )
        driver = rig.driver_add("location", 2).driver
        driver.expression = f"{amplitude:.15f} * {signal}"
        rig["particle_cloud"] = cloud_key
        rig["motion_axis"] = "Z"
        rig["angular_motion"] = False
        rig["vertical_amplitude"] = amplitude
        rig["period_frames"] = frames_per_cycle
        rig["phase_radians"] = phase


def rotate_reflect_z(point):
    angle = math.pi / 4
    return (
        point[0] * math.cos(angle) - point[1] * math.sin(angle),
        point[0] * math.sin(angle) + point[1] * math.cos(angle),
        -point[2],
    )


def has_matching_vertex(point, vertices, tolerance=1e-9):
    return any(
        max(abs(point[axis] - candidate[axis]) for axis in range(3)) <= tolerance
        for candidate in vertices
    )


def validate_geometry(vertices, faces, edges, belt_edges, belt_half_height, geometry):
    if len(vertices) != 10 or len(edges) != 16 or len(faces) != 8:
        raise RuntimeError("Tetragonal trapezohedron must have V=10, E=16, F=8.")
    if len(vertices) - len(edges) + len(faces) != 2:
        raise RuntimeError("Euler characteristic must equal 2.")
    edge_keys = [canonical_edge(edge) for edge in edges]
    if len(set(edge_keys)) != 16:
        raise RuntimeError("All sixteen structural edges must be unique.")
    incidence = {}
    for face in faces:
        if len(set(face)) != 4 or any(index < 0 or index >= len(vertices) for index in face):
            raise RuntimeError("Every kite must contain four valid unique indices.")
        if face_planarity_error(face, vertices) > 1e-9:
            raise RuntimeError("Every kite face must be coplanar.")
        if quad_area(face, vertices) <= 1e-10:
            raise RuntimeError("Every kite face must have nonzero area.")
        if dot(face_normal(face, vertices), face_centroid(face, vertices)) <= 1e-10:
            raise RuntimeError("Every kite face must wind outward.")
        for index, vertex in enumerate(face):
            key = canonical_edge((vertex, face[(index + 1) % 4]))
            incidence[key] = incidence.get(key, 0) + 1
    if set(incidence) != set(edge_keys) or any(count != 2 for count in incidence.values()):
        raise RuntimeError("Every structural edge must belong to exactly two faces.")
    for a, b in edges:
        same_upper = 2 <= a <= 5 and 2 <= b <= 5
        same_lower = 6 <= a <= 9 and 6 <= b <= 9
        if (same_upper or same_lower) and abs(vertices[a][2] - vertices[b][2]) <= 1e-12:
            raise RuntimeError("Horizontal waist-ring edges are forbidden.")
    if len(belt_edges) != 8:
        raise RuntimeError("The alternating central belt must have eight edges.")
    expected_belt_height = geometry["halfHeight"] * (3 - 2 * math.sqrt(2))
    if abs(belt_half_height - expected_belt_height) > 1e-12:
        raise RuntimeError("Belt half-height must be derived from H.")
    if not all(has_matching_vertex(rotate_reflect_z(vertex), vertices) for vertex in vertices):
        raise RuntimeError("The vertex set must have S8 rotoreflection symmetry.")


def validate_scene_contract(vertices, faces, edges, style, rig):
    face_dust = bpy.data.objects.get(FACE_DUST_NAME)
    face_panel = bpy.data.objects.get(FACE_PANEL_NAME)
    edge_filament = bpy.data.objects.get(EDGE_FILAMENT_NAME)
    edge_halo = bpy.data.objects.get(EDGE_HALO_NAME)
    vertex_crystals = bpy.data.objects.get(VERTEX_CRYSTALS_NAME)
    silhouette_mask = bpy.data.objects.get(SILHOUETTE_MASK_NAME)
    curve_objects = [obj for obj in bpy.data.objects if obj.type == "CURVE"]
    fixed_particle_objects = [face_dust, edge_filament, edge_halo, vertex_crystals]
    axial_objects = [
        obj
        for obj in bpy.data.objects
        if obj.type == "MESH" and obj.name.startswith(AXIAL_STAR_STREAM_PREFIX)
    ]
    galaxy_objects = [
        obj
        for obj in bpy.data.objects
        if obj.type == "MESH" and obj.name.startswith(GALAXY_DUST_PREFIX)
    ]
    galaxy_rigs = [
        obj
        for obj in bpy.data.objects
        if obj.type == "EMPTY"
        and obj.name.startswith(GALAXY_DUST_PREFIX)
        and obj.name.endswith("-rig")
    ]
    dynamic_objects = galaxy_objects
    dynamic_rigs = galaxy_rigs
    panel = style["facePanel"]
    if not style["continuousShell"] or not panel["enabled"]:
        raise RuntimeError("The spatial rotation treatment requires one transparent shell.")
    if not (0.12 <= panel["alpha"] <= 0.24):
        raise RuntimeError("Face-panel alpha must stay within the approved 0.12-0.24 range.")
    if panel["renderMethod"] != "DITHERED" or not panel["transparencyOverlap"]:
        raise RuntimeError("Face panels require depth-aware dithered overlapping transparency.")
    if not panel["doubleSided"] or panel["castShadows"]:
        raise RuntimeError("Face panels must be double-sided and shadowless.")
    if panel["refraction"] or panel["fresnel"]:
        raise RuntimeError("Refraction and Fresnel would lock the perceived rotation direction.")
    if style["directionalLighting"] or len(bpy.data.lights) != 0:
        raise RuntimeError("Directional lighting would reveal a unique depth ordering.")
    if not style["independentParticleMotion"]:
        raise RuntimeError("The approved axial and galaxy particles require vertical drift.")
    if style["particleMotionAxes"] != ["Z"] or style["particleAngularMotion"]:
        raise RuntimeError("Dynamic particles may move only along Z and may never orbit.")
    guide = style["guideLine"]
    if (
        not guide["enabled"]
        or not guide["opaque"]
        or guide["breathing"]
        or guide["directionalWeighting"]
        or not guide["depthIndependent"]
        or guide["panelOcclusion"]
        or not 0 < guide["internalOpacity"] < guide["outerSilhouetteOpacity"] < 1
        or guide["intersectionAccumulation"]
        or guide["compositeMethod"] != "ALPHA_OVER_MAX_MASK"
    ):
        raise RuntimeError(
            "Guide lines must remain static, depth-independent, equal-weight masks."
        )
    if (
        len(curve_objects) != len(edges)
        or any(not obj.name.startswith(GUIDE_LINE_PREFIX) for obj in curve_objects)
        or any(obj.parent != rig or obj.animation_data is not None for obj in curve_objects)
        or any(
            not obj.get("guide_line")
            or not obj.get("opaque")
            or obj.get("breathing")
            or obj.get("directional_weighting")
            or not obj.get("depth_independent")
            or obj.get("panel_occlusion")
            or len(obj.data.materials) != 1
            or abs(obj.data.bevel_depth - guide["radius"]) > 1e-8
            for obj in curve_objects
        )
    ):
        raise RuntimeError("Every structural edge must have one faint ghost guide curve.")
    if (
        silhouette_mask is None
        or silhouette_mask.parent != rig
        or not silhouette_mask.get("silhouette_mask")
        or len(silhouette_mask.data.vertices) != len(vertices)
        or len(silhouette_mask.data.polygons) != len(faces)
    ):
        raise RuntimeError("The opaque silhouette mask must match the full closed shell.")
    expected_view_layers = {
        SURFACE_VIEW_LAYER_NAME,
        EDGE_DETAIL_VIEW_LAYER_NAME,
        GUIDE_VIEW_LAYER_NAME,
        SILHOUETTE_VIEW_LAYER_NAME,
    }
    if {layer.name for layer in bpy.context.scene.view_layers} != expected_view_layers:
        raise RuntimeError("Depth-independent contour compositing requires four view layers.")
    if not bpy.context.scene.render.film_transparent:
        raise RuntimeError("View-layer compositing requires a transparent render film.")
    if any(obj is None for obj in fixed_particle_objects) or face_panel is None:
        raise RuntimeError("Face panels plus face, edge, and vertex particles are required.")
    if (
        face_dust.get("particle_count") != style["faceParticleCount"]
        or vertex_crystals.get("particle_count") != len(vertices)
    ):
        raise RuntimeError("Fixed particle counts do not match the render contract.")
    expected_slots = sum(
        max(
            2,
            round(
                magnitude(subtract(vertices[b], vertices[a]))
                * style["edgeFilamentSlotsPerUnit"]
            ),
        )
        for a, b in edges
    )
    filament_count = edge_filament.get("particle_count", 0)
    if (
        edge_filament.get("slot_count") != expected_slots
        or not 0 < filament_count < expected_slots
        or abs(edge_filament.get("keep_ratio") - style["edgeFilamentKeepRatio"])
        > 1e-12
        or edge_filament.get("motion") != "LOCKED"
        or edge_halo.get("particle_count")
        != math.ceil(filament_count / style["edgeHaloStride"])
        or edge_halo.get("source_stride") != style["edgeHaloStride"]
        or edge_halo.get("motion") != "LOCKED"
    ):
        raise RuntimeError("The broken edge-filament point contract is invalid.")
    if any(obj.parent != rig for obj in fixed_particle_objects):
        raise RuntimeError("Fixed particles must be direct children of the rigid rig.")
    if (
        face_panel.parent != rig
        or face_panel.animation_data is not None
        or len(face_panel.data.vertices) != len(vertices)
        or len(face_panel.data.polygons) != len(faces)
        or len(face_panel.data.materials) != 1
        or face_panel.get("face_count") != len(faces)
        or abs(face_panel.get("alpha") - panel["alpha"]) > 1e-12
        or face_panel.get("render_method") != panel["renderMethod"]
        or not face_panel.get("double_sided")
        or not face_panel.get("transparency_overlap")
        or face_panel.get("cast_shadows")
        or face_panel.get("refraction")
        or face_panel.get("fresnel")
    ):
        raise RuntimeError("The transparent eight-face panel violates its render contract.")
    face_material = face_panel.data.materials[0]
    if (
        face_material.surface_render_method != panel["renderMethod"]
        or not face_material.use_transparency_overlap
    ):
        raise RuntimeError("The face-panel material must preserve overlapping depth attenuation.")
    if (
        len(axial_objects) != 1
        or axial_objects[0].get("particle_count")
        != style["axialStarStream"]["count"]
        or axial_objects[0].parent != rig
        or axial_objects[0].get("motion") != "LOCKED"
    ):
        raise RuntimeError("The axial star stream must be one locked, thin particle mesh.")
    if len(galaxy_objects) != style["galaxyDust"]["layerCount"] or sum(
        obj.get("particle_count", 0) for obj in galaxy_objects
    ) != style["galaxyDust"]["count"]:
        raise RuntimeError("Galaxy-dust layers or particle count are invalid.")
    if len(galaxy_rigs) != style["galaxyDust"]["layerCount"]:
        raise RuntimeError("Every dynamic particle layer must have one drift rig.")
    if any(obj.parent not in dynamic_rigs for obj in dynamic_objects):
        raise RuntimeError("Dynamic particle meshes must be parented to drift rigs.")
    if any(layer_rig.parent != rig for layer_rig in dynamic_rigs):
        raise RuntimeError("Every drift rig must remain inside the rotating rigid body.")
    if any(
        obj.animation_data is not None
        for obj in fixed_particle_objects + axial_objects + dynamic_objects
    ):
        raise RuntimeError("Particle meshes may not carry their own animation data.")
    for layer_rig in dynamic_rigs:
        drivers = (
            list(layer_rig.animation_data.drivers)
            if layer_rig.animation_data is not None
            else []
        )
        if (
            len(drivers) != 1
            or drivers[0].data_path != "location"
            or drivers[0].array_index != 2
            or layer_rig.get("motion_axis") != "Z"
            or layer_rig.get("angular_motion")
        ):
            raise RuntimeError("Each particle layer must have one Z-only drift driver.")
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
        hashes[image_paths[image_index].stem] = hashlib.sha256(
            source_pixels.tobytes()
        ).hexdigest()
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
    if float(phase).is_integer():
        return f"{int(phase):03d}"
    return f"{phase:05.1f}".replace(".", "p")


def render_png(scene, path):
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def write_inspection(
    project_root,
    profile,
    style,
    geometry,
    vertices,
    faces,
    edges,
    belt_edges,
    belt_half_height,
    phase_paths,
    phase_hashes,
    motion_paths,
    motion_hashes,
    loop_hashes,
):
    inspection = {
        "geometry": {
            "vertexCount": len(vertices),
            "edgeCount": len(edges),
            "faceCount": len(faces),
            "eulerCharacteristic": len(vertices) - len(edges) + len(faces),
            "beltEdgeCount": len(belt_edges),
            "waistRadius": geometry["waistRadius"],
            "halfHeight": geometry["halfHeight"],
            "beltHalfHeight": belt_half_height,
            "beltHalfHeightDerived": True,
            "lowerRingTwistDegrees": geometry["lowerRingTwistDegrees"],
            "symmetry": "D4d / S8 rotoreflection",
            "centralInversion": False,
            "centralInversionNote": (
                "A four-point lower ring twisted by 45 degrees cannot also contain -v "
                "for every upper-ring vertex."
            ),
            "maximumFacePlanarityError": max(
                face_planarity_error(face, vertices) for face in faces
            ),
        },
        "renderContract": {
            "continuousShell": style["continuousShell"],
            "facePanel": {
                "enabled": style["facePanel"]["enabled"],
                "faceCount": len(faces),
                "color": style["facePanel"]["color"],
                "alpha": style["facePanel"]["alpha"],
                "transparency": 1.0 - style["facePanel"]["alpha"],
                "emissionStrength": style["facePanel"]["emissionStrength"],
                "renderMethod": style["facePanel"]["renderMethod"],
                "doubleSided": style["facePanel"]["doubleSided"],
                "transparencyOverlap": style["facePanel"]["transparencyOverlap"],
                "castShadows": style["facePanel"]["castShadows"],
                "refraction": style["facePanel"]["refraction"],
                "fresnel": style["facePanel"]["fresnel"],
            },
            "lightCount": len(bpy.data.lights),
            "cameraType": bpy.context.scene.camera.data.type,
            "showBackEdges": style["showBackEdges"],
            "curveObjectCount": len(
                [obj for obj in bpy.data.objects if obj.type == "CURVE"]
            ),
            "continuousEdgeCurves": True,
            "guideLine": {
                "objectCount": len(edges),
                "color": style["guideLine"]["color"],
                "maskEmissionStrength": style["guideLine"][
                    "maskEmissionStrength"
                ],
                "radius": style["guideLine"]["radius"],
                "opaque": style["guideLine"]["opaque"],
                "breathing": style["guideLine"]["breathing"],
                "directionalWeighting": style["guideLine"][
                    "directionalWeighting"
                ],
                "depthIndependent": style["guideLine"]["depthIndependent"],
                "panelOcclusion": style["guideLine"]["panelOcclusion"],
                "internalOpacity": style["guideLine"]["internalOpacity"],
                "outerSilhouetteOpacity": style["guideLine"][
                    "outerSilhouetteOpacity"
                ],
                "intersectionAccumulation": style["guideLine"][
                    "intersectionAccumulation"
                ],
                "compositeMethod": style["guideLine"]["compositeMethod"],
                "viewLayers": [
                    SURFACE_VIEW_LAYER_NAME,
                    EDGE_DETAIL_VIEW_LAYER_NAME,
                    GUIDE_VIEW_LAYER_NAME,
                    SILHOUETTE_VIEW_LAYER_NAME,
                ],
            },
            "faceParticleCount": style["faceParticleCount"],
            "edgeFilamentPointCount": bpy.data.objects[EDGE_FILAMENT_NAME].get(
                "particle_count"
            ),
            "edgeHaloPointCount": bpy.data.objects[EDGE_HALO_NAME].get(
                "particle_count"
            ),
            "edgeFilamentKeepRatio": style["edgeFilamentKeepRatio"],
            "edgeBreathAmount": style["edgeBreathAmount"],
            "axialStarStreamCount": style["axialStarStream"]["count"],
            "axialStarStreamMotion": style["axialStarStream"]["motion"],
            "galaxyDustCount": style["galaxyDust"]["count"],
            "galaxyDustLayers": style["galaxyDust"]["layerCount"],
            "vertexCrystalCount": len(vertices),
            "independentParticleMotion": True,
            "particleMotionAxes": style["particleMotionAxes"],
            "particleAngularMotion": style["particleAngularMotion"],
            "cameraElevationDegrees": style["cameraElevationDegrees"],
            "orthographicScale": style["orthographicScale"],
        },
        "animation": {
            "frameStart": bpy.context.scene.frame_start,
            "frameEnd": bpy.context.scene.frame_end,
            "frameCount": bpy.context.scene["frame_count"],
            "conceptualLoopFrame": bpy.context.scene["conceptual_loop_frame"],
            "rotationCycleSeconds": style["rotationCycleSeconds"],
            "totalTurns": profile["seconds"] / style["rotationCycleSeconds"],
            "interpolation": "LINEAR",
            "videoContainsDuplicateTailFrame": False,
            "firstFramePixelHash": loop_hashes["start"],
            "conceptualLoopFramePixelHash": loop_hashes["next"],
            "firstMatchesConceptualLoopFrame": loop_hashes["start"]
            == loop_hashes["next"],
        },
        "stills": {
            "files": [str(path.relative_to(project_root)) for path in phase_paths],
            "fileHashes": {path.stem: sha256(path) for path in phase_paths},
            "pixelHashes": phase_hashes,
            "zeroMatches360": phase_hashes["phase-000"]
            == phase_hashes["phase-360"],
            "contactSheet": "output/stills/tetragonal-trapezohedron-contact-sheet.png",
        },
        "motionContact": {
            "sampleCount": len(motion_paths),
            "pixelHashes": motion_hashes,
            "contactSheet": (
                "output/stills/tetragonal-trapezohedron-motion-contact-sheet.png"
            ),
        },
    }
    inspection_path = project_root / "output" / "inspection.json"
    inspection_path.write_text(json.dumps(inspection, indent=2), encoding="utf-8")


def render_stills(
    project_root,
    rig,
    profile,
    style,
    geometry,
    vertices,
    faces,
    edges,
    belt_edges,
    belt_half_height,
):
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

    phase_contact_path = still_directory / "tetragonal-trapezohedron-contact-sheet.png"
    phase_hashes = build_contact_sheet(
        phase_paths,
        phase_contact_path,
        len(phase_paths),
        "tetragonal-trapezohedron-phase-contact-sheet",
    )
    if phase_hashes["phase-000"] != phase_hashes["phase-360"]:
        raise RuntimeError("The 0-degree and 360-degree stills must be pixel-identical.")

    motion_paths = []
    frames_per_cycle = round(profile["fps"] * style["rotationCycleSeconds"])
    for index in range(style["motionContactFrameCount"]):
        frame = scene.frame_start + round(
            index * frames_per_cycle / style["motionContactFrameCount"]
        )
        scene.frame_set(frame)
        motion_path = motion_directory / f"motion-{index + 1:03d}-frame-{frame:03d}.png"
        render_png(scene, motion_path)
        motion_paths.append(motion_path)
    motion_contact_path = (
        still_directory / "tetragonal-trapezohedron-motion-contact-sheet.png"
    )
    motion_hashes = build_contact_sheet(
        motion_paths,
        motion_contact_path,
        style["motionContactColumns"],
        "tetragonal-trapezohedron-motion-contact-sheet",
    )

    loop_hashes = {}
    for label, frame in (
        ("start", scene.frame_start),
        ("next", scene["conceptual_loop_frame"]),
    ):
        scene.frame_set(frame)
        endpoint_path = still_directory / f"loop-{label}-frame.png"
        render_png(scene, endpoint_path)
        loop_hashes[label] = pixel_hash(endpoint_path)
    if loop_hashes["start"] != loop_hashes["next"]:
        raise RuntimeError(
            "The conceptual frame after the video must be pixel-identical to frame one."
        )

    write_inspection(
        project_root,
        profile,
        style,
        geometry,
        vertices,
        faces,
        edges,
        belt_edges,
        belt_half_height,
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
    collection = make_collection(ROOT_COLLECTION_NAME)
    surface_collection = make_collection(SURFACE_COLLECTION_NAME, collection)
    edge_detail_collection = make_collection(
        EDGE_DETAIL_COLLECTION_NAME, collection
    )
    guide_collection = make_collection(GUIDE_COLLECTION_NAME, collection)
    silhouette_collection = make_collection(
        SILHOUETTE_COLLECTION_NAME, collection
    )
    rig = bpy.data.objects.new(RIG_NAME, None)
    collection.objects.link(rig)
    vertices, faces, edges, belt_edges, belt_half_height = create_geometry(geometry)
    validate_geometry(
        vertices, faces, edges, belt_edges, belt_half_height, geometry
    )
    create_face_panel(vertices, faces, style, surface_collection, rig)
    create_silhouette_mask(vertices, faces, silhouette_collection, rig)
    create_guide_lines(vertices, edges, style, guide_collection, rig)
    create_face_stardust(vertices, faces, style, surface_collection, rig)
    _, _, edge_material, edge_halo_material = create_edge_filaments(
        vertices, edges, style, edge_detail_collection, rig
    )
    create_axial_star_stream(style, surface_collection, rig)
    galaxy_dust_rigs = create_galaxy_dust(style, surface_collection, rig)
    create_vertex_crystals(vertices, style, edge_detail_collection, rig)
    configure_camera(style)
    configure_render(profile, style, output_path)
    animate_rotation(rig, profile, style)
    animate_material_breath(
        edge_material,
        profile,
        style["edgeFilamentStrength"],
        style["edgeBreathAmount"],
        style["edgeBreathCycleSeconds"],
    )
    animate_material_breath(
        edge_halo_material,
        profile,
        style["edgeHaloStrength"],
        style["edgeBreathAmount"],
        style["edgeBreathCycleSeconds"],
    )
    animate_vertical_particle_layers(
        galaxy_dust_rigs, profile, style, "galaxyDust", 22037
    )
    validate_scene_contract(vertices, faces, edges, style, rig)

    if not args.stills and not args.render:
        bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    elif args.stills:
        render_stills(
            project_root,
            rig,
            profile,
            style,
            geometry,
            vertices,
            faces,
            edges,
            belt_edges,
            belt_half_height,
        )
    else:
        bpy.ops.render.render(animation=True)


if __name__ == "__main__":
    main()
