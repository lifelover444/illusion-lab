import argparse
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector


def parse_args():
    parser = argparse.ArgumentParser(description="Create the 005 Mobius heart illusion scene.")
    parser.add_argument("--mode", choices=["scene", "preview", "final"], required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--blend", required=True)
    return parser.parse_args()


def require_positive(config, path):
    value = config
    for key in path:
        value = value[key]
    if value <= 0:
        raise ValueError(".".join(path) + " must be positive")
    return value


def validate_config(config):
    if config["status"] != "modeling-started":
        raise ValueError("status must be modeling-started")
    if config["subject"] != "mobius-heart-ring":
        raise ValueError("subject must be mobius-heart-ring")
    if config["camera"]["projection"] != "orthographic":
        raise ValueError("camera.projection must be orthographic")
    if config["motion"]["easing"] != "linear":
        raise ValueError("motion.easing must be linear")
    if config["motion"]["axis"] != "vertical":
        raise ValueError("motion.axis must be vertical")

    sample_count = require_positive(config, ["geometry", "sampleCount"])
    if sample_count < 24:
        raise ValueError("geometry.sampleCount must be at least 24")

    require_positive(config, ["geometry", "heartScale"])
    require_positive(config, ["geometry", "bandWidthRatio"])
    require_positive(config, ["geometry", "depthWidthRatio"])
    require_positive(config, ["geometry", "edgeRadius"])
    require_positive(config, ["profiles", "preview", "fps"])
    require_positive(config, ["profiles", "preview", "seconds"])
    require_positive(config, ["profiles", "final", "fps"])
    require_positive(config, ["profiles", "final", "seconds"])


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()


def set_input(node, names, value):
    for name in names:
        if name in node.inputs:
            node.inputs[name].default_value = value
            return


def heart_point(t, scale, vertical_scale):
    x = 16 * math.sin(t) ** 3
    z = (
        13 * math.cos(t)
        - 5 * math.cos(2 * t)
        - 2 * math.cos(3 * t)
        - math.cos(4 * t)
    )
    return Vector((x * scale, 0, (z * scale * vertical_scale) - 0.18))


def build_mobius_geometry(config):
    geometry = config["geometry"]
    sample_count = int(geometry["sampleCount"])
    scale = float(geometry["heartScale"])
    vertical_scale = float(geometry["verticalScale"])
    band_width = float(geometry["bandWidthRatio"]) * 32 * scale
    depth_width = float(geometry["depthWidthRatio"]) * 32 * scale
    twist = math.radians(float(geometry["mobiusTwistDegrees"]))

    centers = [
        heart_point((i / sample_count) * math.tau, scale, vertical_scale)
        for i in range(sample_count)
    ]

    vertices = []
    edge_a = []
    edge_b = []

    for i, center in enumerate(centers):
        previous_center = centers[(i - 1) % sample_count]
        next_center = centers[(i + 1) % sample_count]
        tangent = (next_center - previous_center).normalized()
        plane_normal = Vector((-tangent.z, 0, tangent.x)).normalized()
        depth_axis = Vector((0, 1, 0))
        twist_angle = (i / sample_count) * twist
        cross = (
            plane_normal * math.cos(twist_angle) * band_width
            + depth_axis * math.sin(twist_angle) * depth_width
        )

        a = center + cross
        b = center - cross
        edge_a.append(a)
        edge_b.append(b)
        vertices.append(tuple(a))
        vertices.append(tuple(b))

    faces = []
    for i in range(sample_count):
        if i == sample_count - 1:
            faces.append((i * 2, 1, 0, i * 2 + 1))
        else:
            j = i + 1
            faces.append((i * 2, j * 2, j * 2 + 1, i * 2 + 1))

    boundary = edge_a + edge_b
    return vertices, faces, boundary


def make_surface_material(config):
    material_config = config["material"]
    material = bpy.data.materials.new("Mobius Heart Transparent Emission")
    material.use_nodes = True
    material.blend_method = "BLEND"
    material.use_screen_refraction = False
    material.show_transparent_back = True

    principled = material.node_tree.nodes.get("Principled BSDF")
    color = material_config["surfaceColor"]
    alpha = float(material_config["surfaceAlpha"])
    emission = float(material_config["surfaceEmissionStrength"])

    set_input(principled, ["Base Color"], (color[0], color[1], color[2], alpha))
    set_input(principled, ["Alpha"], alpha)
    set_input(principled, ["Emission Color", "Emission"], (color[0], color[1], color[2], 1))
    set_input(principled, ["Emission Strength"], emission)
    set_input(principled, ["Roughness"], 0.78)
    set_input(principled, ["Metallic"], 0)
    return material


def make_edge_material(config):
    material_config = config["material"]
    material = bpy.data.materials.new("Mobius Heart Soft Edge Emission")
    material.use_nodes = True

    principled = material.node_tree.nodes.get("Principled BSDF")
    color = material_config["edgeColor"]
    emission = float(material_config["edgeEmissionStrength"])

    set_input(principled, ["Base Color"], (color[0], color[1], color[2], 1))
    set_input(principled, ["Emission Color", "Emission"], (color[0], color[1], color[2], 1))
    set_input(principled, ["Emission Strength"], emission)
    set_input(principled, ["Roughness"], 0.62)
    return material


def add_poly_curve(name, points, radius, material):
    curve = bpy.data.curves.new(name, type="CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 2
    curve.bevel_depth = radius
    curve.bevel_resolution = 4

    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for point, co in zip(spline.points, points):
        point.co = (co.x, co.y, co.z, 1)
    spline.use_cyclic_u = True

    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    return obj


def create_mobius_heart(config):
    root = bpy.data.objects.new("Mobius Heart Rotation Root", None)
    bpy.context.collection.objects.link(root)

    vertices, faces, boundary = build_mobius_geometry(config)
    mesh = bpy.data.meshes.new("Mobius Heart Ribbon Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()

    ribbon = bpy.data.objects.new("Mobius Heart Ribbon", mesh)
    bpy.context.collection.objects.link(ribbon)
    ribbon.data.materials.append(make_surface_material(config))
    ribbon.parent = root

    edge_material = make_edge_material(config)
    edge_radius = float(config["geometry"]["edgeRadius"])
    boundary_curve = add_poly_curve("Mobius Heart Continuous Boundary", boundary, edge_radius, edge_material)
    boundary_curve.parent = root

    return root


def look_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def setup_camera(config):
    camera_data = bpy.data.cameras.new("Orthographic Ambiguity Camera")
    camera = bpy.data.objects.new("Orthographic Ambiguity Camera", camera_data)
    bpy.context.collection.objects.link(camera)
    camera.location = Vector(config["camera"]["location"])
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = float(config["camera"]["orthoScale"])
    look_at(camera, config["camera"]["lookAt"])
    bpy.context.scene.camera = camera


def setup_world(config):
    world = bpy.context.scene.world or bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.color = tuple(config["material"]["backgroundColor"])


def setup_render(config, mode):
    profile_name = "preview" if mode == "scene" else mode
    profile = config["profiles"][profile_name]
    scene = bpy.context.scene

    scene.render.resolution_x = int(profile["width"])
    scene.render.resolution_y = int(profile["height"])
    scene.render.fps = int(profile["fps"])
    scene.frame_start = 1
    scene.frame_end = int(profile["fps"] * profile["seconds"])
    scene.render.film_transparent = False

    engine_items = {item.identifier for item in scene.render.bl_rna.properties["engine"].enum_items}
    scene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in engine_items else "BLENDER_EEVEE"

    if hasattr(scene, "eevee"):
        if hasattr(scene.eevee, "taa_render_samples"):
            scene.eevee.taa_render_samples = 64
        if hasattr(scene.eevee, "use_bloom"):
            scene.eevee.use_bloom = True
        if hasattr(scene.eevee, "bloom_intensity"):
            scene.eevee.bloom_intensity = float(config["material"]["bloomIntensity"])
        if hasattr(scene.eevee, "bloom_radius"):
            scene.eevee.bloom_radius = float(config["material"]["bloomRadius"])

    scene.view_settings.view_transform = "Filmic"
    scene.view_settings.look = "Medium High Contrast"
    scene.view_settings.exposure = 0
    scene.view_settings.gamma = 1

    output_path = Path(profile["output"]).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(output_path)
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"


def animate_rotation(obj, config):
    scene = bpy.context.scene
    total_seconds = float(config["motion"]["totalSeconds"])
    cycle_seconds = float(config["motion"]["rotationCycleSeconds"])
    cycles = total_seconds / cycle_seconds

    scene.frame_set(scene.frame_start)
    obj.rotation_euler = (0, 0, 0)
    obj.keyframe_insert(data_path="rotation_euler", frame=scene.frame_start)

    scene.frame_set(scene.frame_end)
    obj.rotation_euler = (0, 0, math.tau * cycles)
    obj.keyframe_insert(data_path="rotation_euler", frame=scene.frame_end)

    if obj.animation_data and obj.animation_data.action:
        for fcurve in obj.animation_data.action.fcurves:
            for keyframe in fcurve.keyframe_points:
                keyframe.interpolation = "LINEAR"


def main():
    args = parse_args()
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    validate_config(config)

    clear_scene()
    setup_world(config)
    root = create_mobius_heart(config)
    setup_camera(config)
    setup_render(config, args.mode)
    animate_rotation(root, config)

    blend_path = Path(args.blend)
    blend_path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

    if args.mode in {"preview", "final"}:
        bpy.ops.render.render(animation=True)


if __name__ == "__main__":
    main()
