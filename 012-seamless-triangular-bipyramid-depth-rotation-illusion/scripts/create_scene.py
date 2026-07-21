import argparse
from array import array
import hashlib
import json
import math
import shutil
import sys
from pathlib import Path

import bpy
from mathutils import Vector


SCENE_FILENAME = "seamless-triangular-bipyramid-depth-rotation-illusion.blend"
SHELL_NAME = "triangular-bipyramid-glass-shell"
MATERIAL_NAME = "dichroic-smoked-glass"
RIG_NAME = "triangular-bipyramid-rotation-rig"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Create the seamless triangular bipyramid depth rotation illusion."
    )
    parser.add_argument("--profile", choices=("preview", "final"), default="preview")
    parser.add_argument("--project-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--stills", action="store_true")
    script_args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(script_args)


def load_config():
    config_path = Path(__file__).resolve().parent / "triangular-bipyramid-config.json"
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
    radius = geometry["radius"]
    half_height = geometry["halfHeight"]
    phase = math.radians(geometry["initialPhaseDegrees"])
    vertices = [(0.0, 0.0, half_height), (0.0, 0.0, -half_height)]
    for index in range(3):
        angle = phase + index * math.tau / 3
        vertices.append((radius * math.cos(angle), radius * math.sin(angle), 0.0))

    faces = []
    for index in range(3):
        current = 2 + index
        next_index = 2 + (index + 1) % 3
        faces.append(orient_outward((0, current, next_index), vertices))
        faces.append(orient_outward((1, next_index, current), vertices))
    return vertices, faces


def make_dichroic_material(material_config):
    if material_config["colorFieldMode"] != "object-aurora":
        raise RuntimeError("Unsupported dichroic color field mode.")
    material = bpy.data.materials.new(MATERIAL_NAME)
    material.use_nodes = True
    material.diffuse_color = tuple(material_config["facingColors"][-1]["color"])
    material.surface_render_method = material_config["surfaceRenderMethod"]
    material.use_screen_refraction = True
    material.refraction_depth = 0.35

    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    principled = nodes.new("ShaderNodeBsdfPrincipled")
    layer_weight = nodes.new("ShaderNodeLayerWeight")
    texture_coordinate = nodes.new("ShaderNodeTexCoord")
    separate_xyz = nodes.new("ShaderNodeSeparateXYZ")
    x_weight = nodes.new("ShaderNodeMath")
    z_weight = nodes.new("ShaderNodeMath")
    facing_weight = nodes.new("ShaderNodeMath")
    add_position = nodes.new("ShaderNodeMath")
    add_facing = nodes.new("ShaderNodeMath")
    normalize_field = nodes.new("ShaderNodeMath")
    facing_ramp = nodes.new("ShaderNodeValToRGB")
    volume_absorption = nodes.new("ShaderNodeVolumeAbsorption")

    facing_ramp.color_ramp.interpolation = "EASE"
    stops = material_config["facingColors"]
    elements = facing_ramp.color_ramp.elements
    elements[0].position = stops[0]["position"]
    elements[0].color = tuple(stops[0]["color"])
    elements[1].position = stops[-1]["position"]
    elements[1].color = tuple(stops[-1]["color"])
    for stop in stops[1:-1]:
        element = elements.new(stop["position"])
        element.color = tuple(stop["color"])

    x_weight.operation = "MULTIPLY"
    x_weight.inputs[1].default_value = 0.52
    z_weight.operation = "MULTIPLY"
    z_weight.inputs[1].default_value = 0.30
    facing_weight.operation = "MULTIPLY"
    facing_weight.inputs[1].default_value = 0.35
    add_position.operation = "ADD"
    add_facing.operation = "ADD"
    normalize_field.operation = "MULTIPLY"
    normalize_field.inputs[1].default_value = 0.82
    normalize_field.use_clamp = True

    principled.inputs["Metallic"].default_value = material_config["metallic"]
    principled.inputs["Roughness"].default_value = material_config["roughness"]
    principled.inputs["IOR"].default_value = material_config["ior"]
    principled.inputs["Specular IOR Level"].default_value = material_config[
        "specularIorLevel"
    ]
    principled.inputs["Alpha"].default_value = material_config["alpha"]
    principled.inputs["Transmission Weight"].default_value = material_config[
        "transmissionWeight"
    ]
    principled.inputs["Coat Weight"].default_value = material_config["coatWeight"]
    principled.inputs["Coat Roughness"].default_value = material_config[
        "coatRoughness"
    ]
    principled.inputs["Thin Film Thickness"].default_value = material_config[
        "thinFilmThickness"
    ]
    principled.inputs["Thin Film IOR"].default_value = material_config[
        "thinFilmIor"
    ]
    principled.inputs["Emission Strength"].default_value = material_config[
        "emissionStrength"
    ]
    volume_absorption.inputs["Color"].default_value = (
        *material_config["volumeColor"],
        1.0,
    )
    volume_absorption.inputs["Density"].default_value = material_config[
        "volumeDensity"
    ]

    links.new(texture_coordinate.outputs["Generated"], separate_xyz.inputs["Vector"])
    links.new(separate_xyz.outputs["X"], x_weight.inputs[0])
    links.new(separate_xyz.outputs["Z"], z_weight.inputs[0])
    links.new(layer_weight.outputs["Facing"], facing_weight.inputs[0])
    links.new(x_weight.outputs[0], add_position.inputs[0])
    links.new(z_weight.outputs[0], add_position.inputs[1])
    links.new(add_position.outputs[0], add_facing.inputs[0])
    links.new(facing_weight.outputs[0], add_facing.inputs[1])
    links.new(add_facing.outputs[0], normalize_field.inputs[0])
    links.new(normalize_field.outputs[0], facing_ramp.inputs["Fac"])
    links.new(facing_ramp.outputs["Color"], principled.inputs["Base Color"])
    links.new(facing_ramp.outputs["Color"], principled.inputs["Emission Color"])
    links.new(principled.outputs["BSDF"], output.inputs["Surface"])
    links.new(volume_absorption.outputs["Volume"], output.inputs["Volume"])
    return material


def create_glass_shell(vertices, faces, material, collection, parent):
    mesh = bpy.data.meshes.new(SHELL_NAME)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    for polygon in mesh.polygons:
        polygon.use_smooth = False

    obj = bpy.data.objects.new(SHELL_NAME, mesh)
    obj.parent = parent
    obj.data.materials.append(material)
    obj["point_count"] = 0
    obj["source_vertex_count"] = len(vertices)
    obj["exposed_triangle_count"] = len(faces)
    obj["dedicated_edge_count"] = 0
    collection.objects.link(obj)
    return obj


def create_area_lights(lighting, collection):
    lights = []
    pair_count = lighting["pairCount"]
    radius = lighting["radius"]
    height = lighting["height"]

    for pair_index in range(pair_count):
        angle = pair_index * math.tau / pair_count
        color = tuple(lighting["colors"][pair_index])
        for mate_index, sign in enumerate((1, -1)):
            name = f"dichroic-area-{pair_index + 1:02d}-{mate_index + 1:02d}"
            light_data = bpy.data.lights.new(name, "AREA")
            light_data.energy = lighting["energy"]
            light_data.shape = lighting["shape"]
            light_data.size = lighting["size"]
            light_data.size_y = lighting["sizeY"]
            light_data.color = color
            light = bpy.data.objects.new(name, light_data)
            light.location = (
                sign * radius * math.cos(angle),
                sign * radius * math.sin(angle),
                sign * height,
            )
            look_at(light, (0.0, 0.0, 0.0))
            collection.objects.link(light)
            lights.append(light)
    return lights


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
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = style["orthographicScale"]
    bpy.context.scene.collection.objects.link(camera)
    bpy.context.scene.camera = camera
    return camera


def configure_render(profile, style, output_path):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.eevee.use_raytracing = True
    scene.eevee.ray_tracing_method = "SCREEN"
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

    world = bpy.data.worlds.new("deep-blue-black-world")
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (*style["backgroundColor"], 1.0)
    background.inputs["Strength"].default_value = 1.0
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
    loop_frame = scene.frame_end + 1
    turns = profile["seconds"] / style["rotationCycleSeconds"]
    rig.rotation_euler = (0.0, 0.0, 0.0)
    rig.keyframe_insert(data_path="rotation_euler", frame=scene.frame_start)
    rig.rotation_euler = (0.0, 0.0, turns * math.tau)
    rig.keyframe_insert(data_path="rotation_euler", frame=loop_frame)
    set_linear_interpolation(rig)


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
        if tuple(image.size) != (width, height):
            raise RuntimeError("All phase stills must have identical dimensions.")
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
        "triangular-bipyramid-contact-sheet",
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


def triangle_area(a, b, c):
    normal = cross(subtract(b, a), subtract(c, a))
    return math.sqrt(dot(normal, normal)) / 2


def validate_scene_contract(vertices, faces):
    shell = bpy.data.objects.get(SHELL_NAME)
    mesh_objects = [obj for obj in bpy.data.objects if obj.type == "MESH"]
    area_lights = [light for light in bpy.data.lights if light.type == "AREA"]
    if len(vertices) != 5 or len(faces) != 6:
        raise RuntimeError("The source geometry must contain five vertices and six faces.")
    if shell is None or len(mesh_objects) != 1:
        raise RuntimeError("The render scene must contain one glass shell mesh.")
    if len(shell.data.vertices) != 5 or len(shell.data.polygons) != 6:
        raise RuntimeError("The glass shell mesh must contain five vertices and six faces.")
    if shell.get("point_count") != 0:
        raise RuntimeError("The dichroic glass scene must contain zero point-cloud points.")
    if len(bpy.data.materials) != 1 or shell.data.materials[0].name != MATERIAL_NAME:
        raise RuntimeError("All six faces must share the one dichroic glass material.")
    if len(bpy.data.lights) != 6 or len(area_lights) != 6:
        raise RuntimeError("The scene must contain exactly six paired area lights.")


def write_inspection(
    project_root,
    profile,
    style,
    geometry,
    vertices,
    faces,
    render_mode,
    still_paths,
    pixel_hashes,
):
    file_hashes = {path.stem: sha256(path) for path in still_paths}
    inspection = {
        "geometry": {
            "uniqueVertexCount": len(vertices),
            "uniqueTriangleCount": len(faces),
            "faceAreas": [
                triangle_area(*(vertices[index] for index in face)) for face in faces
            ],
            "dedicatedEdgeCount": 0,
            "radius": geometry["radius"],
            "halfHeight": geometry["halfHeight"],
            "initialPhaseDegrees": geometry["initialPhaseDegrees"],
        },
        "surface": {
            "renderMode": render_mode,
            "pointCount": 0,
            "shellObjectCount": len(
                [obj for obj in bpy.data.objects if obj.type == "MESH"]
            ),
            "meshObjectCount": len([obj for obj in bpy.data.objects if obj.type == "MESH"]),
            "meshVertexCount": len(bpy.data.objects[SHELL_NAME].data.vertices),
            "meshTriangleCount": len(bpy.data.objects[SHELL_NAME].data.polygons),
            "materialCount": len(bpy.data.materials),
            "materialName": MATERIAL_NAME,
        },
        "scene": {
            "lightCount": len(bpy.data.lights),
            "lightTypes": [light.type for light in bpy.data.lights],
            "cameraType": bpy.context.scene.camera.data.type,
            "orthographicScale": bpy.context.scene.camera.data.ortho_scale,
            "worldBackground": style["backgroundColor"],
        },
        "animation": {
            "frameStart": bpy.context.scene.frame_start,
            "frameEnd": bpy.context.scene.frame_end,
            "loopFrame": bpy.context.scene.frame_end + 1,
            "rotationCycleSeconds": style["rotationCycleSeconds"],
            "totalTurns": profile["seconds"] / style["rotationCycleSeconds"],
            "interpolation": "LINEAR",
        },
        "render": {
            "width": profile["width"],
            "height": profile["height"],
            "fps": profile["fps"],
            "seconds": profile["seconds"],
            "samples": profile["samples"],
            "phaseDegrees": style["phaseDegrees"],
        },
        "stills": {
            "fileHashes": file_hashes,
            "pixelHashes": pixel_hashes,
            "zeroMatches360": pixel_hashes["phase-000"]
            == pixel_hashes["phase-360"],
            "contactSheet": "output/stills/triangular-bipyramid-contact-sheet.png",
        },
    }
    inspection_path = project_root / "output" / "inspection.json"
    inspection_path.write_text(json.dumps(inspection, indent=2), encoding="utf-8")


def render_stills(
    project_root, rig, profile, style, geometry, vertices, faces, render_mode
):
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
                    raise RuntimeError("The 0-degree phase must precede the loop phase.")
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

    contact_sheet_path = still_directory / "triangular-bipyramid-contact-sheet.png"
    pixel_hashes = build_contact_sheet(still_paths, contact_sheet_path)
    phase_names = [f"phase-{phase:03d}" for phase in style["phaseDegrees"]]
    if pixel_hashes["phase-000"] != pixel_hashes["phase-360"]:
        raise RuntimeError("The 0-degree and 360-degree stills must be pixel-identical.")
    if len({pixel_hashes[name] for name in phase_names[:-1]}) != len(phase_names) - 1:
        raise RuntimeError("Every non-loop phase still must have distinct decoded pixels.")
    write_inspection(
        project_root,
        profile,
        style,
        geometry,
        vertices,
        faces,
        render_mode,
        still_paths,
        pixel_hashes,
    )


def main():
    args = parse_args()
    config = load_config()
    profile = config["profiles"][args.profile]
    geometry = config["geometry"]
    material_config = config["material"]
    lighting = config["lighting"]
    style = config["style"]
    project_root = Path(args.project_root)
    output_path = project_root / profile["output"]
    blend_path = project_root / "scene" / SCENE_FILENAME
    output_path.parent.mkdir(parents=True, exist_ok=True)
    blend_path.parent.mkdir(parents=True, exist_ok=True)

    clear_scene()
    collection = make_collection("seamless-triangular-bipyramid-depth-rotation-illusion")
    rig = bpy.data.objects.new(RIG_NAME, None)
    collection.objects.link(rig)
    vertices, faces = create_geometry(geometry)
    material = make_dichroic_material(material_config)
    create_glass_shell(vertices, faces, material, collection, rig)
    create_area_lights(lighting, collection)
    configure_camera(style)
    configure_render(profile, style, output_path)
    animate_rotation(rig, profile, style)
    validate_scene_contract(vertices, faces)
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

    if args.stills:
        render_stills(
            project_root,
            rig,
            profile,
            style,
            geometry,
            vertices,
            faces,
            config["renderMode"],
        )
    elif args.render:
        bpy.ops.render.render(animation=True)


if __name__ == "__main__":
    main()
