# Heart Mobius Illusion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `005-heart-blender-illusion` experiment as a procedural glowing Mobius heart ring with orthographic, depth-ambiguous vertical-axis rotation.

**Architecture:** Keep the experiment self-contained in `005-heart-blender-illusion`. TypeScript tests protect the illusion constraints and JSON config shape without requiring Blender; `scripts/run-blender.mjs` owns CLI/profile selection and Blender discovery; `scripts/create_scene.py` owns Blender scene generation from config.

**Tech Stack:** TypeScript, Vitest, Node.js ESM, Blender Python API, JSON config, npm workspace scripts.

---

### Task 1: Lock The Mobius Heart Contract In Tests

**Files:**
- Modify: `005-heart-blender-illusion/tests/heartIllusionPlan.test.ts`
- Modify after test fails: `005-heart-blender-illusion/src/heartIllusionPlan.ts`
- Modify after test fails: `005-heart-blender-illusion/scripts/heart-illusion-config.json`

- [ ] **Step 1: Replace the existing planning-only tests with Mobius contract tests**

Use this content for `005-heart-blender-illusion/tests/heartIllusionPlan.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import {
  canSupportBistableRotation,
  cueLocksDirection,
  hasModelingStarted,
  heartIllusionPlan
} from '../src/heartIllusionPlan';
import config from '../scripts/heart-illusion-config.json';

describe('005 heart Mobius Blender illusion contract', () => {
  it('starts Blender modeling for a Mobius heart ring', () => {
    expect(hasModelingStarted()).toBe(true);
    expect(heartIllusionPlan.implementationStatus).toBe('modeling-started');
    expect(heartIllusionPlan.subject).toBe('mobius-heart-ring');
    expect(heartIllusionPlan.renderer).toBe('blender');
  });

  it('keeps the rotation ambiguous through projection and timing', () => {
    expect(canSupportBistableRotation()).toBe(true);
    expect(heartIllusionPlan.rotationAxis).toBe('vertical');
    expect(heartIllusionPlan.cameraProjection).toBe('orthographic');
    expect(heartIllusionPlan.rotationTiming.easing).toBe('linear');
    expect(heartIllusionPlan.rotationTiming.totalSeconds / heartIllusionPlan.rotationTiming.cycleSeconds).toBe(2);
  });

  it('rejects cues that would lock the perceived direction', () => {
    for (const cue of [
      'perspective camera',
      'cast shadow',
      'asymmetric texture',
      'glass refraction',
      'one-sided highlight'
    ]) {
      expect(cueLocksDirection(cue)).toBe(true);
    }
  });

  it('keeps continuous ribbon cues visible instead of using a silhouette', () => {
    expect(heartIllusionPlan.recommendedGeometry).toContain('continuous Mobius ribbon surface');
    expect(heartIllusionPlan.recommendedGeometry).toContain('emissive rim curves');
    expect(heartIllusionPlan.ambiguityPreservingCues).toContain('matching front and back material');
    expect(heartIllusionPlan.ambiguityPreservingCues).toContain('semi-transparent ribbon surface');
  });

  it('stores render, geometry, material, camera, and motion defaults in config', () => {
    expect(config.status).toBe('modeling-started');
    expect(config.subject).toBe('mobius-heart-ring');
    expect(config.profiles.final.width / config.profiles.final.height).toBe(9 / 16);
    expect(config.motion.totalSeconds / config.motion.rotationCycleSeconds).toBe(2);
    expect(config.motion.easing).toBe('linear');
    expect(config.camera.projection).toBe('orthographic');
    expect(config.geometry.sampleCount).toBeGreaterThanOrEqual(180);
    expect(config.geometry.mobiusTwistDegrees).toBe(180);
    expect(config.geometry.bandWidthRatio).toBeGreaterThanOrEqual(0.1);
    expect(config.geometry.bandWidthRatio).toBeLessThanOrEqual(0.16);
    expect(config.material.surfaceAlpha).toBeGreaterThan(0);
    expect(config.material.surfaceAlpha).toBeLessThan(0.5);
    expect(config.material.edgeEmissionStrength).toBeGreaterThan(config.material.surfaceEmissionStrength);
  });
});
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run:

```powershell
npm run test:005 -- --runInBand
```

Expected: FAIL because `subject` is still `heart`, `status` is still `planning-only`, and the new config fields do not exist.

- [ ] **Step 3: Update the TypeScript plan model**

Use this content for `005-heart-blender-illusion/src/heartIllusionPlan.ts`:

```ts
export type ImplementationStatus = 'planning-only' | 'modeling-started';
export type IllusionSubject = 'heart' | 'mobius-heart-ring';

export interface HeartIllusionPlan {
  implementationStatus: ImplementationStatus;
  renderer: 'blender';
  subject: IllusionSubject;
  rotationAxis: 'vertical';
  cameraProjection: 'orthographic';
  rotationTiming: {
    cycleSeconds: number;
    totalSeconds: number;
    easing: 'linear';
  };
  recommendedGeometry: string[];
  directionLockingCues: string[];
  ambiguityPreservingCues: string[];
}

export const heartIllusionPlan: HeartIllusionPlan = {
  implementationStatus: 'modeling-started',
  renderer: 'blender',
  subject: 'mobius-heart-ring',
  rotationAxis: 'vertical',
  cameraProjection: 'orthographic',
  rotationTiming: {
    cycleSeconds: 6,
    totalSeconds: 12,
    easing: 'linear'
  },
  recommendedGeometry: [
    'continuous Mobius ribbon surface',
    'heart-shaped parametric centerline',
    'emissive rim curves',
    'semi-transparent double-sided surface'
  ],
  directionLockingCues: [
    'perspective camera',
    'cast shadow',
    'asymmetric texture',
    'glass refraction',
    'one-sided highlight',
    'different front and back colors'
  ],
  ambiguityPreservingCues: [
    'orthographic projection',
    'constant angular velocity',
    'matching front and back material',
    'semi-transparent ribbon surface',
    'visible continuous ribbon',
    'minimal symmetric lighting'
  ]
};

export const hasModelingStarted = (plan: HeartIllusionPlan = heartIllusionPlan): boolean =>
  plan.implementationStatus === 'modeling-started';

export const canSupportBistableRotation = (plan: HeartIllusionPlan = heartIllusionPlan): boolean =>
  plan.renderer === 'blender'
  && plan.subject === 'mobius-heart-ring'
  && plan.rotationAxis === 'vertical'
  && plan.cameraProjection === 'orthographic'
  && plan.rotationTiming.easing === 'linear'
  && plan.rotationTiming.totalSeconds / plan.rotationTiming.cycleSeconds === 2
  && plan.recommendedGeometry.includes('continuous Mobius ribbon surface')
  && plan.ambiguityPreservingCues.includes('matching front and back material');

export const cueLocksDirection = (cue: string, plan: HeartIllusionPlan = heartIllusionPlan): boolean =>
  plan.directionLockingCues.includes(cue);
```

- [ ] **Step 4: Update the JSON config**

Use this content for `005-heart-blender-illusion/scripts/heart-illusion-config.json`:

```json
{
  "name": "heart-blender-illusion",
  "status": "modeling-started",
  "subject": "mobius-heart-ring",
  "profiles": {
    "preview": {
      "width": 360,
      "height": 640,
      "fps": 15,
      "seconds": 12,
      "output": "output/heart-mobius-illusion-preview.mp4"
    },
    "final": {
      "width": 720,
      "height": 1280,
      "fps": 30,
      "seconds": 12,
      "output": "output/heart-mobius-illusion.mp4"
    }
  },
  "geometry": {
    "sampleCount": 240,
    "heartScale": 0.145,
    "verticalScale": 0.92,
    "bandWidthRatio": 0.13,
    "depthWidthRatio": 0.07,
    "mobiusTwistDegrees": 180,
    "edgeRadius": 0.018
  },
  "material": {
    "surfaceColor": [1.0, 0.18, 0.56],
    "edgeColor": [1.0, 0.72, 0.92],
    "surfaceAlpha": 0.28,
    "surfaceEmissionStrength": 1.4,
    "edgeEmissionStrength": 4.2,
    "backgroundColor": [0.005, 0.004, 0.008],
    "bloomIntensity": 0.08,
    "bloomRadius": 6.5
  },
  "motion": {
    "rotationCycleSeconds": 6,
    "totalSeconds": 12,
    "easing": "linear",
    "axis": "vertical"
  },
  "camera": {
    "projection": "orthographic",
    "orthoScale": 5.8,
    "location": [0, -7.2, 0.18],
    "lookAt": [0, 0, 0.12],
    "avoidPerspectiveDepthCue": true
  },
  "modelingNotes": {
    "preferredFirstPass": "glowing semi-transparent Mobius ribbon following a heart-shaped centerline",
    "avoid": [
      "pure silhouette",
      "solid crystal heart",
      "perspective camera",
      "cast shadow",
      "asymmetric texture",
      "glass refraction",
      "one-sided highlight"
    ]
  }
}
```

- [ ] **Step 5: Run tests and commit**

Run:

```powershell
npm run test:005
```

Expected: PASS.

Commit only these files:

```powershell
git add -- 005-heart-blender-illusion/tests/heartIllusionPlan.test.ts 005-heart-blender-illusion/src/heartIllusionPlan.ts 005-heart-blender-illusion/scripts/heart-illusion-config.json
git commit -m "Model Mobius heart illusion constraints"
```

---

### Task 2: Implement Blender Runner

**Files:**
- Modify: `005-heart-blender-illusion/scripts/run-blender.mjs`
- Test by command: `npm run scene:005`

- [ ] **Step 1: Replace the runner that currently only delegates to the incomplete scene flow**

Use this content for `005-heart-blender-illusion/scripts/run-blender.mjs`:

```js
import { existsSync } from 'node:fs';
import { mkdir } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawn } from 'node:child_process';

const __dirname = dirname(fileURLToPath(import.meta.url));
const projectRoot = resolve(__dirname, '..');
const mode = process.argv[2] ?? 'scene';
const validModes = new Set(['scene', 'preview', 'final']);

if (!validModes.has(mode)) {
  console.error(`Unsupported mode "${mode}". Use one of: ${Array.from(validModes).join(', ')}`);
  process.exit(1);
}

const configPath = resolve(__dirname, 'heart-illusion-config.json');
const scriptPath = resolve(__dirname, 'create_scene.py');
const outputBlend = resolve(projectRoot, 'output', 'heart-mobius-illusion.blend');

const blenderCandidates = [
  process.env.BLENDER_BIN,
  'blender'
].filter(Boolean);

const blenderBin = blenderCandidates[0];

if (!existsSync(scriptPath)) {
  console.error(`Missing Blender scene script: ${scriptPath}`);
  process.exit(1);
}

await mkdir(dirname(outputBlend), { recursive: true });

const args = [
  '--background',
  '--python',
  scriptPath,
  '--',
  '--mode',
  mode,
  '--config',
  configPath,
  '--blend',
  outputBlend
];

const child = spawn(blenderBin, args, {
  cwd: projectRoot,
  stdio: 'inherit',
  shell: process.platform === 'win32'
});

child.on('error', (error) => {
  console.error(`Unable to start Blender with "${blenderBin}". Set BLENDER_BIN to the Blender executable path. ${error.message}`);
  process.exit(1);
});

child.on('exit', (code) => {
  process.exit(code ?? 1);
});
```

- [ ] **Step 2: Run the scene command and verify the runner reaches Blender**

Run:

```powershell
npm run scene:005
```

Expected when Blender is unavailable: FAIL with a clear message mentioning `BLENDER_BIN`. Expected when Blender is available before Task 3: FAIL inside `create_scene.py` because scene generation has not been implemented yet.

- [ ] **Step 3: Commit the runner**

Commit only the runner:

```powershell
git add -- 005-heart-blender-illusion/scripts/run-blender.mjs
git commit -m "Add Blender runner for Mobius heart scene"
```

---

### Task 3: Generate The Mobius Heart Blender Scene

**Files:**
- Modify: `005-heart-blender-illusion/scripts/create_scene.py`
- Test by command: `npm run scene:005`

- [ ] **Step 1: Replace the Blender script that currently exits before scene generation**

Use this content for `005-heart-blender-illusion/scripts/create_scene.py`:

```python
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
    require_positive(config, ["geometry", "sampleCount"])
    require_positive(config, ["geometry", "heartScale"])
    require_positive(config, ["geometry", "bandWidthRatio"])
    require_positive(config, ["geometry", "depthWidthRatio"])
    require_positive(config, ["profiles", "preview", "fps"])
    require_positive(config, ["profiles", "preview", "seconds"])
    require_positive(config, ["profiles", "final", "fps"])
    require_positive(config, ["profiles", "final", "seconds"])


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()


def heart_point(t, scale, vertical_scale):
    x = 16 * math.sin(t) ** 3
    z = (
        13 * math.cos(t)
        - 5 * math.cos(2 * t)
        - 2 * math.cos(3 * t)
        - math.cos(4 * t)
    )
    return Vector((x * scale, 0, (z * scale * vertical_scale) - 0.18))


def build_mobius_vertices(config):
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
        cross = (plane_normal * math.cos(twist_angle) * band_width) + (depth_axis * math.sin(twist_angle) * depth_width)

        a = center + cross
        b = center - cross
        edge_a.append(a)
        edge_b.append(b)
        vertices.append(tuple(a))
        vertices.append(tuple(b))

    faces = []
    for i in range(sample_count):
        j = (i + 1) % sample_count
        faces.append((i * 2, j * 2, j * 2 + 1, i * 2 + 1))

    return vertices, faces, edge_a, edge_b


def make_surface_material(config):
    material_config = config["material"]
    material = bpy.data.materials.new("Mobius Heart Transparent Emission")
    material.use_nodes = True
    material.blend_method = "BLEND"
    material.use_screen_refraction = False
    material.show_transparent_back = True

    nodes = material.node_tree.nodes
    principled = nodes.get("Principled BSDF")
    color = material_config["surfaceColor"]
    alpha = float(material_config["surfaceAlpha"])
    emission = float(material_config["surfaceEmissionStrength"])

    principled.inputs["Base Color"].default_value = (color[0], color[1], color[2], alpha)
    principled.inputs["Alpha"].default_value = alpha
    principled.inputs["Emission Color"].default_value = (color[0], color[1], color[2], 1)
    principled.inputs["Emission Strength"].default_value = emission
    principled.inputs["Roughness"].default_value = 0.78
    principled.inputs["Metallic"].default_value = 0
    return material


def make_edge_material(config):
    material_config = config["material"]
    material = bpy.data.materials.new("Mobius Heart Soft Edge Emission")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    principled = nodes.get("Principled BSDF")
    color = material_config["edgeColor"]
    emission = float(material_config["edgeEmissionStrength"])
    principled.inputs["Base Color"].default_value = (color[0], color[1], color[2], 1)
    principled.inputs["Emission Color"].default_value = (color[0], color[1], color[2], 1)
    principled.inputs["Emission Strength"].default_value = emission
    principled.inputs["Roughness"].default_value = 0.62
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
    vertices, faces, edge_a, edge_b = build_mobius_vertices(config)
    mesh = bpy.data.meshes.new("Mobius Heart Ribbon Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()

    obj = bpy.data.objects.new("Mobius Heart Ribbon", mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(make_surface_material(config))

    edge_material = make_edge_material(config)
    edge_radius = float(config["geometry"]["edgeRadius"])
    add_poly_curve("Mobius Heart Edge A", edge_a, edge_radius, edge_material)
    add_poly_curve("Mobius Heart Edge B", edge_b, edge_radius, edge_material)
    return obj


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
    scene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in {item.identifier for item in scene.render.bl_rna.properties["engine"].enum_items} else "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 64
    scene.render.film_transparent = False
    scene.render.filepath = str(Path(profile["output"]).resolve())
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
    ribbon = create_mobius_heart(config)
    setup_camera(config)
    setup_render(config, args.mode)
    animate_rotation(ribbon, config)

    blend_path = Path(args.blend)
    blend_path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

    if args.mode in {"preview", "final"}:
      bpy.ops.render.render(animation=True)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run scene generation**

Run:

```powershell
npm run scene:005
```

Expected when Blender is available: PASS and create `005-heart-blender-illusion/output/heart-mobius-illusion.blend`. Expected when Blender is unavailable: FAIL with a clear `BLENDER_BIN` message from the runner.

- [ ] **Step 3: Commit the Blender scene script**

Commit only the script:

```powershell
git add -- 005-heart-blender-illusion/scripts/create_scene.py
git commit -m "Generate Mobius heart Blender scene"
```

---

### Task 4: Document The Implemented Experiment

**Files:**
- Modify: `005-heart-blender-illusion/README.md`

- [ ] **Step 1: Replace planning-only README language**

Use this content for `005-heart-blender-illusion/README.md`:

```md
# Heart Blender Illusion

005 is a Blender-based depth-ambiguous rotation experiment. It renders a glowing Mobius heart ring: a semi-transparent ribbon following a heart-shaped centerline with a 180 degree Mobius twist.

The experiment avoids a silhouette and avoids a solid crystal heart. The intended illusion comes from continuous ribbon motion, orthographic projection, matching front/back material, and weak depth cues. The same linear vertical-axis rotation should be plausibly perceived as clockwise or counterclockwise.

## Commands

```powershell
npm run build:005
npm run test:005
npm run scene:005
npm run render:005:preview
npm run render:005:final
```

Set `BLENDER_BIN` if Blender is not available as `blender` on `PATH`:

```powershell
$env:BLENDER_BIN = "C:\Program Files\Blender Foundation\Blender 4.3\blender.exe"
```

## File Structure

```text
005-heart-blender-illusion/
├─ scripts/
│  ├─ create_scene.py              # Procedural Blender scene generator
│  ├─ heart-illusion-config.json   # Render, geometry, material, camera, and motion config
│  └─ run-blender.mjs              # Node runner for scene and render commands
├─ src/
│  └─ heartIllusionPlan.ts         # Testable illusion constraints
├─ tests/
│  └─ heartIllusionPlan.test.ts
├─ package.json
├─ tsconfig.json
└─ vitest.config.ts
```

## Visual Design

- Pink/magenta semi-transparent Mobius ribbon surface.
- Brighter emissive edge curves on both ribbon boundaries.
- Orthographic camera facing the object from negative `Y`.
- Linear rotation around the vertical `Z` axis.
- Dark background with no floor and no cast shadow.
- No perspective camera, asymmetric texture, glass refraction, or one-sided highlight.

## Verification Frames

Inspect frames near these phases:

- `0°`: clear front-facing heart.
- `90°`: compressed but continuous twisted ribbon.
- `180°`: heart shape returns with similar strength.
- `270°`: second compressed side phase that still avoids a fixed direction cue.
```

- [ ] **Step 2: Commit README update**

Run:

```powershell
git add -- 005-heart-blender-illusion/README.md
git commit -m "Document Mobius heart Blender experiment"
```

---

### Task 5: Final Verification

**Files:**
- No source edits expected.

- [ ] **Step 1: Run TypeScript build**

Run:

```powershell
npm run build:005
```

Expected: PASS with no TypeScript errors.

- [ ] **Step 2: Run unit tests**

Run:

```powershell
npm run test:005
```

Expected: PASS.

- [ ] **Step 3: Run Blender scene command**

Run:

```powershell
npm run scene:005
```

Expected if Blender is installed or `BLENDER_BIN` is set: PASS and create `005-heart-blender-illusion/output/heart-mobius-illusion.blend`.

If Blender is unavailable, record the exact error. The acceptable unavailable-Blender failure is a clear message telling the user to set `BLENDER_BIN`.

- [ ] **Step 4: Run preview render when Blender is available**

Run:

```powershell
npm run render:005:preview
```

Expected if Blender is installed or `BLENDER_BIN` is set: PASS and create `005-heart-blender-illusion/output/heart-mobius-illusion-preview.mp4`.

If Blender is unavailable, record the exact error and do not claim render verification passed.

- [ ] **Step 5: Report final status**

Summarize:

- files changed,
- tests run,
- Blender command outcome,
- render artifact path if created,
- any residual risk around perceptual ambiguity that requires visual tuning.
