# Pink Heart Point Cloud Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `005-pink-heart-point-cloud`, a Blender-generated pink low-density heart point cloud that rotates with weak depth cues for bistable direction perception.

**Architecture:** The experiment follows the existing `004-*` Blender layout. TypeScript owns deterministic point generation and tests; Blender Python owns scene creation, animation, material, camera, and render output; Node wraps local Blender execution.

**Tech Stack:** npm workspaces, TypeScript, Vitest, Blender Python (`bpy`), Blender EEVEE Next.

---

## File Structure

- Create `005-pink-heart-point-cloud/package.json`: workspace scripts and metadata.
- Create `005-pink-heart-point-cloud/tsconfig.json`: same strict no-emit TypeScript config used by Blender experiments.
- Create `005-pink-heart-point-cloud/vitest.config.ts`: Node test environment.
- Create `005-pink-heart-point-cloud/src/heartPointCloud.ts`: deterministic point generation, heart equation, seeded RNG, bounds helpers.
- Create `005-pink-heart-point-cloud/tests/heartPointCloud.test.ts`: focused unit tests for the generator and render profile config.
- Create `005-pink-heart-point-cloud/scripts/heart-config.json`: density, color, animation, camera, and output profiles.
- Create `005-pink-heart-point-cloud/scripts/run-blender.mjs`: local Blender wrapper matching `004-wireframe-hourglass-illusion/scripts/run-blender.mjs`.
- Create `005-pink-heart-point-cloud/scripts/create_scene.py`: Blender scene generator.
- Create `005-pink-heart-point-cloud/README.md`: local commands, file structure, and illusion rationale.
- Modify `package.json`: add workspace and root shortcuts for build/test/scene/render commands.
- Modify `package-lock.json`: refresh workspace metadata after adding the new package.

## Task 1: Workspace Scaffold

**Files:**
- Create: `005-pink-heart-point-cloud/package.json`
- Create: `005-pink-heart-point-cloud/tsconfig.json`
- Create: `005-pink-heart-point-cloud/vitest.config.ts`
- Modify: `package.json`
- Modify: `package-lock.json`

- [ ] **Step 1: Create package metadata**

Create `005-pink-heart-point-cloud/package.json`:

```json
{
  "name": "@illusion-lab/pink-heart-point-cloud",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "scene": "node scripts/run-blender.mjs scene",
    "render:preview": "node scripts/run-blender.mjs preview",
    "render:final": "node scripts/run-blender.mjs final",
    "build": "tsc",
    "test": "vitest run"
  },
  "devDependencies": {
    "typescript": "^5.4.5",
    "vitest": "^1.6.0"
  }
}
```

- [ ] **Step 2: Create TypeScript config**

Create `005-pink-heart-point-cloud/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "module": "ESNext",
    "lib": ["ES2020"],
    "allowJs": false,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "forceConsistentCasingInFileNames": true,
    "moduleResolution": "Node",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true
  },
  "include": ["src", "tests"]
}
```

- [ ] **Step 3: Create Vitest config**

Create `005-pink-heart-point-cloud/vitest.config.ts`:

```ts
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'node'
  }
});
```

- [ ] **Step 4: Register the workspace**

Modify root `package.json` by adding `"005-pink-heart-point-cloud"` to `workspaces`, then add these scripts:

```json
{
  "build:005": "npm run build --workspace @illusion-lab/pink-heart-point-cloud",
  "test:005": "npm run test --workspace @illusion-lab/pink-heart-point-cloud",
  "scene:005": "npm run scene --workspace @illusion-lab/pink-heart-point-cloud",
  "render:005:preview": "npm run render:preview --workspace @illusion-lab/pink-heart-point-cloud",
  "render:005:final": "npm run render:final --workspace @illusion-lab/pink-heart-point-cloud"
}
```

- [ ] **Step 5: Refresh npm lockfile**

Run:

```powershell
npm install --package-lock-only --ignore-scripts
```

Expected: `package-lock.json` records the new workspace package without changing installed source files.

- [ ] **Step 6: Verify scaffold commands fail only because source is missing**

Run:

```powershell
npm run build:005
```

Expected: TypeScript reports no inputs or missing source files because `src/` is not created yet.

- [ ] **Step 7: Commit scaffold**

Run:

```powershell
git add package.json package-lock.json 005-pink-heart-point-cloud/package.json 005-pink-heart-point-cloud/tsconfig.json 005-pink-heart-point-cloud/vitest.config.ts
git commit -m "Add pink heart point cloud workspace"
```

## Task 2: Point Cloud Generator

**Files:**
- Create: `005-pink-heart-point-cloud/src/heartPointCloud.ts`
- Create: `005-pink-heart-point-cloud/tests/heartPointCloud.test.ts`

- [ ] **Step 1: Write failing generator tests**

Create `005-pink-heart-point-cloud/tests/heartPointCloud.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import {
  createHeartPointCloud,
  getPointCloudBounds,
  isInsideHeart,
  type HeartPointCloudConfig
} from '../src/heartPointCloud';

const baseConfig: HeartPointCloudConfig = {
  count: 640,
  seed: 20260705,
  width: 3.0,
  height: 2.72,
  depth: 0.42,
  lobeLift: 0.1,
  pointSizeMin: 0.018,
  pointSizeMax: 0.038
};

describe('heart point cloud generation', () => {
  it('generates the configured number of points inside the heart silhouette', () => {
    const cloud = createHeartPointCloud(baseConfig);

    expect(cloud.points).toHaveLength(baseConfig.count);
    for (const point of cloud.points) {
      expect(isInsideHeart(point.normalizedX, point.normalizedY)).toBe(true);
      expect(point.x).toBeGreaterThanOrEqual(-baseConfig.width / 2);
      expect(point.x).toBeLessThanOrEqual(baseConfig.width / 2);
      expect(point.y).toBeGreaterThanOrEqual(-baseConfig.height / 2 + baseConfig.lobeLift);
      expect(point.y).toBeLessThanOrEqual(baseConfig.height / 2 + baseConfig.lobeLift);
    }
  });

  it('is deterministic for a fixed seed', () => {
    const first = createHeartPointCloud(baseConfig);
    const second = createHeartPointCloud(baseConfig);

    expect(second.points.slice(0, 12)).toEqual(first.points.slice(0, 12));
  });

  it('keeps depth shallow and centered around the rotation axis', () => {
    const cloud = createHeartPointCloud(baseConfig);
    const bounds = getPointCloudBounds(cloud.points);

    expect(bounds.minZ).toBeGreaterThanOrEqual(-baseConfig.depth / 2);
    expect(bounds.maxZ).toBeLessThanOrEqual(baseConfig.depth / 2);
    expect(Math.abs((bounds.minX + bounds.maxX) / 2)).toBeLessThan(0.08);
    expect(Math.abs((bounds.minZ + bounds.maxZ) / 2)).toBeLessThan(0.06);
  });

  it('assigns visible low-density point sizes', () => {
    const cloud = createHeartPointCloud(baseConfig);

    for (const point of cloud.points) {
      expect(point.size).toBeGreaterThanOrEqual(baseConfig.pointSizeMin);
      expect(point.size).toBeLessThanOrEqual(baseConfig.pointSizeMax);
    }
  });

  it('rejects points outside the classic heart equation', () => {
    expect(isInsideHeart(0, 0)).toBe(true);
    expect(isInsideHeart(0, 0.72)).toBe(true);
    expect(isInsideHeart(1.32, 0.9)).toBe(false);
    expect(isInsideHeart(0, -1.18)).toBe(false);
  });
});
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
npm run test:005
```

Expected: FAIL because `../src/heartPointCloud` does not exist.

- [ ] **Step 3: Implement deterministic point generation**

Create `005-pink-heart-point-cloud/src/heartPointCloud.ts`:

```ts
export interface HeartPointCloudConfig {
  count: number;
  seed: number;
  width: number;
  height: number;
  depth: number;
  lobeLift: number;
  pointSizeMin: number;
  pointSizeMax: number;
}

export interface HeartPoint {
  x: number;
  y: number;
  z: number;
  size: number;
  normalizedX: number;
  normalizedY: number;
}

export interface HeartPointCloud {
  points: HeartPoint[];
}

export interface PointCloudBounds {
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
  minZ: number;
  maxZ: number;
}

const HEART_X_LIMIT = 1.35;
const HEART_Y_MIN = -1.15;
const HEART_Y_MAX = 1.25;

const mulberry32 = (seed: number): (() => number) => {
  let state = seed >>> 0;

  return () => {
    state += 0x6D2B79F5;
    let value = state;
    value = Math.imul(value ^ value >>> 15, value | 1);
    value ^= value + Math.imul(value ^ value >>> 7, value | 61);
    return ((value ^ value >>> 14) >>> 0) / 4294967296;
  };
};

const randomBetween = (random: () => number, min: number, max: number): number =>
  min + (max - min) * random();

export const isInsideHeart = (x: number, y: number): boolean => {
  const value = (x * x + y * y - 1) ** 3 - x * x * y ** 3;
  return value <= 0;
};

export const createHeartPointCloud = (config: HeartPointCloudConfig): HeartPointCloud => {
  const random = mulberry32(config.seed);
  const points: HeartPoint[] = [];
  let attempts = 0;
  const maxAttempts = config.count * 180;

  while (points.length < config.count && attempts < maxAttempts) {
    attempts += 1;
    const normalizedX = randomBetween(random, -HEART_X_LIMIT, HEART_X_LIMIT);
    const normalizedY = randomBetween(random, HEART_Y_MIN, HEART_Y_MAX);

    if (!isInsideHeart(normalizedX, normalizedY)) {
      continue;
    }

    const centerBias = 1 - Math.min(1, Math.abs(normalizedX) / HEART_X_LIMIT);
    const depthJitter = randomBetween(random, -0.5, 0.5);
    const normalizedYCenter = (HEART_Y_MIN + HEART_Y_MAX) / 2;
    const y = (normalizedY - normalizedYCenter) / (HEART_Y_MAX - HEART_Y_MIN) * config.height + config.lobeLift;

    points.push({
      x: normalizedX / HEART_X_LIMIT * config.width / 2,
      y,
      z: depthJitter * config.depth * (0.62 + centerBias * 0.38),
      size: randomBetween(random, config.pointSizeMin, config.pointSizeMax),
      normalizedX,
      normalizedY
    });
  }

  if (points.length !== config.count) {
    throw new Error(`Generated ${points.length} heart points after ${attempts} attempts; expected ${config.count}.`);
  }

  return { points };
};

export const getPointCloudBounds = (points: HeartPoint[]): PointCloudBounds => {
  if (points.length === 0) {
    throw new Error('Cannot compute bounds for an empty point cloud.');
  }

  return points.reduce<PointCloudBounds>(
    (bounds, point) => ({
      minX: Math.min(bounds.minX, point.x),
      maxX: Math.max(bounds.maxX, point.x),
      minY: Math.min(bounds.minY, point.y),
      maxY: Math.max(bounds.maxY, point.y),
      minZ: Math.min(bounds.minZ, point.z),
      maxZ: Math.max(bounds.maxZ, point.z)
    }),
    {
      minX: Number.POSITIVE_INFINITY,
      maxX: Number.NEGATIVE_INFINITY,
      minY: Number.POSITIVE_INFINITY,
      maxY: Number.NEGATIVE_INFINITY,
      minZ: Number.POSITIVE_INFINITY,
      maxZ: Number.NEGATIVE_INFINITY
    }
  );
};
```

- [ ] **Step 4: Run tests to verify pass**

Run:

```powershell
npm run test:005
```

Expected: PASS with 5 tests.

- [ ] **Step 5: Run TypeScript build**

Run:

```powershell
npm run build:005
```

Expected: PASS with no TypeScript errors.

- [ ] **Step 6: Commit generator**

Run:

```powershell
git add 005-pink-heart-point-cloud/src/heartPointCloud.ts 005-pink-heart-point-cloud/tests/heartPointCloud.test.ts
git commit -m "Add heart point cloud generator"
```

## Task 3: Blender Scene Generation

**Files:**
- Create: `005-pink-heart-point-cloud/scripts/heart-config.json`
- Create: `005-pink-heart-point-cloud/scripts/run-blender.mjs`
- Create: `005-pink-heart-point-cloud/scripts/create_scene.py`
- Modify: `005-pink-heart-point-cloud/tests/heartPointCloud.test.ts`

- [ ] **Step 1: Add config tests**

Extend `005-pink-heart-point-cloud/tests/heartPointCloud.test.ts` with:

```ts
import config from '../scripts/heart-config.json';

describe('heart point cloud render config', () => {
  it('uses a vertical loopable render profile with a weak-depth rotation cycle', () => {
    expect(config.profiles.final.width / config.profiles.final.height).toBeCloseTo(9 / 16, 5);
    expect(config.profiles.final.fps).toBe(30);
    expect(config.profiles.final.seconds).toBe(12);
    expect(config.style.rotationCycleSeconds).toBe(6);
    expect(config.profiles.final.seconds / config.style.rotationCycleSeconds).toBe(2);
  });

  it('keeps the first pass low density and shallow', () => {
    expect(config.geometry.count).toBeGreaterThanOrEqual(500);
    expect(config.geometry.count).toBeLessThanOrEqual(900);
    expect(config.geometry.depth).toBeLessThanOrEqual(0.5);
    expect(config.style.shadowOpacity).toBe(0);
  });
});
```

- [ ] **Step 2: Run tests to verify config failure**

Run:

```powershell
npm run test:005
```

Expected: FAIL because `scripts/heart-config.json` does not exist.

- [ ] **Step 3: Create scene config**

Create `005-pink-heart-point-cloud/scripts/heart-config.json`:

```json
{
  "name": "pink-heart-point-cloud",
  "profiles": {
    "preview": {
      "width": 360,
      "height": 640,
      "fps": 15,
      "seconds": 12,
      "samples": 8,
      "output": "output/pink-heart-point-cloud-preview.mp4"
    },
    "final": {
      "width": 720,
      "height": 1280,
      "fps": 30,
      "seconds": 12,
      "samples": 16,
      "output": "output/pink-heart-point-cloud.mp4"
    }
  },
  "geometry": {
    "count": 640,
    "seed": 20260705,
    "width": 3.0,
    "height": 2.72,
    "depth": 0.42,
    "lobeLift": 0.1,
    "pointSizeMin": 0.018,
    "pointSizeMax": 0.038
  },
  "style": {
    "rotationCycleSeconds": 6,
    "orthographicScale": 4.5,
    "cameraDistance": 8.0,
    "cameraTargetZ": 0,
    "backgroundColor": [1.0, 0.955, 0.975],
    "heartColor": [1.0, 0.25, 0.58],
    "heartCoreColor": [1.0, 0.62, 0.78],
    "emissionStrength": 1.2,
    "shadowOpacity": 0,
    "worldStrength": 0.78
  }
}
```

- [ ] **Step 4: Create Blender runner**

Create `005-pink-heart-point-cloud/scripts/run-blender.mjs`:

```js
import { existsSync } from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const experimentRoot = path.resolve(__dirname, '..');
const command = process.argv.length > 2 ? process.argv[2] : 'scene';
const blenderExe = process.env.BLENDER_EXE || 'D:\\software\\Blender 4.5 LTS\\blender.exe';

const commandMap = {
  scene: { profile: 'final', render: false },
  preview: { profile: 'preview', render: true },
  final: { profile: 'final', render: true }
};

if (!Object.hasOwn(commandMap, command)) {
  console.error(`Unknown command "${command}". Use one of: scene, preview, final.`);
  process.exit(1);
}

if (!existsSync(blenderExe)) {
  console.error(`Blender executable not found: ${blenderExe}`);
  console.error('Set BLENDER_EXE to the full path of blender.exe if it is installed elsewhere.');
  process.exit(1);
}

const sceneScript = path.join(__dirname, 'create_scene.py');
const selected = commandMap[command];
const blenderArgs = [
  '--background',
  '--factory-startup',
  '--python',
  sceneScript,
  '--',
  '--profile',
  selected.profile,
  '--project-root',
  experimentRoot
];

if (selected.render) {
  blenderArgs.push('--render');
}

const result = spawnSync(blenderExe, blenderArgs, {
  stdio: 'inherit',
  windowsHide: false
});

if (result.error) {
  console.error(result.error.message);
  process.exit(1);
}

process.exit(result.status === null ? 1 : result.status);
```

- [ ] **Step 5: Create Blender scene script**

Create `005-pink-heart-point-cloud/scripts/create_scene.py` with these functions:

```python
import argparse
import json
import math
import random
import sys
from pathlib import Path

import bpy
from mathutils import Vector

HEART_X_LIMIT = 1.35
HEART_Y_MIN = -1.15
HEART_Y_MAX = 1.25


def parse_args():
    parser = argparse.ArgumentParser(description="Create and optionally render the pink heart point cloud illusion.")
    parser.add_argument("--profile", choices=("preview", "final"), default="preview")
    parser.add_argument("--project-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--render", action="store_true")
    script_args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return parser.parse_args(script_args)


def load_config():
    config_path = Path(__file__).resolve().parent / "heart-config.json"
    return json.loads(config_path.read_text(encoding="utf-8"))


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for data_block in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras, bpy.data.lights, bpy.data.collections):
        for item in list(data_block):
            if item.users == 0:
                data_block.remove(item)


def make_collection(name):
    collection = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(collection)
    return collection


def make_emission_material(name, color, strength):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    material.diffuse_color = (color[0], color[1], color[2], 1.0)
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    emission = nodes.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value = (color[0], color[1], color[2], 1.0)
    emission.inputs["Strength"].default_value = strength
    links.new(emission.outputs[0], output.inputs[0])
    return material


def is_inside_heart(x, y):
    return (x * x + y * y - 1) ** 3 - x * x * y ** 3 <= 0


def random_between(rng, minimum, maximum):
    return minimum + (maximum - minimum) * rng.random()


def create_heart_points(geometry):
    rng = random.Random(geometry["seed"])
    points = []
    attempts = 0
    max_attempts = geometry["count"] * 180
    while len(points) < geometry["count"] and attempts < max_attempts:
        attempts += 1
        normalized_x = random_between(rng, -HEART_X_LIMIT, HEART_X_LIMIT)
        normalized_y = random_between(rng, HEART_Y_MIN, HEART_Y_MAX)
        if not is_inside_heart(normalized_x, normalized_y):
            continue
        center_bias = 1 - min(1, abs(normalized_x) / HEART_X_LIMIT)
        normalized_y_center = (HEART_Y_MIN + HEART_Y_MAX) / 2
        y = (
            (normalized_y - normalized_y_center)
            / (HEART_Y_MAX - HEART_Y_MIN)
            * geometry["height"]
            + geometry["lobeLift"]
        )
        points.append({
            "x": normalized_x / HEART_X_LIMIT * geometry["width"] / 2,
            "y": y,
            "z": random_between(rng, -0.5, 0.5) * geometry["depth"] * (0.62 + center_bias * 0.38),
            "size": random_between(rng, geometry["pointSizeMin"], geometry["pointSizeMax"]),
        })
    if len(points) != geometry["count"]:
        raise RuntimeError(f"Generated {len(points)} heart points; expected {geometry['count']}.")
    return points


def create_point_mesh(name, points, material, collection, parent):
    vertices = []
    faces = []
    for point in points:
        x, y, z, size = point["x"], point["y"], point["z"], point["size"]
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


def look_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def configure_camera(style):
    camera_data = bpy.data.cameras.new("orthographic-camera")
    camera = bpy.data.objects.new("orthographic-camera", camera_data)
    camera.location = (0, -style["cameraDistance"], 0.12)
    look_at(camera, (0, 0, style["cameraTargetZ"]))
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = style["orthographicScale"]
    bpy.context.scene.collection.objects.link(camera)
    bpy.context.scene.camera = camera


def configure_render(profile, style, output_path):
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
    scene.world = bpy.data.worlds.new("soft-pink-world")
    scene.world.color = tuple(style["backgroundColor"])
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "MEDIUM"
    scene.render.ffmpeg.ffmpeg_preset = "GOOD"
    scene.render.ffmpeg.gopsize = profile["fps"]
    scene.render.filepath = str(output_path)
    try:
        scene.view_settings.view_transform = "Standard"
        scene.view_settings.look = "Medium High Contrast"
        scene.view_settings.exposure = 0
        scene.view_settings.gamma = 1
    except TypeError:
        pass


def set_fcurve_interpolation(obj, interpolation):
    if obj.animation_data and obj.animation_data.action:
        for fcurve in obj.animation_data.action.fcurves:
            for keyframe in fcurve.keyframe_points:
                keyframe.interpolation = interpolation


def animate_rotation(rig, profile, style):
    start_frame = bpy.context.scene.frame_start
    loop_frame = bpy.context.scene.frame_end + 1
    turns = profile["seconds"] / style["rotationCycleSeconds"]
    rig.rotation_euler = (0, 0, 0)
    rig.keyframe_insert(data_path="rotation_euler", frame=start_frame)
    rig.rotation_euler = (0, 0, math.radians(360 * turns))
    rig.keyframe_insert(data_path="rotation_euler", frame=loop_frame)
    set_fcurve_interpolation(rig, "LINEAR")


def main():
    args = parse_args()
    config = load_config()
    profile = config["profiles"][args.profile]
    project_root = Path(args.project_root)
    output_path = project_root / profile["output"]
    blend_path = project_root / "scene" / "pink-heart-point-cloud.blend"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    blend_path.parent.mkdir(parents=True, exist_ok=True)

    clear_scene()
    collection = make_collection("pink-heart-point-cloud")
    rotation_rig = bpy.data.objects.new("heart-rotation-rig", None)
    bpy.context.scene.collection.objects.link(rotation_rig)

    material = make_emission_material(
        "soft-pink-heart-points",
        config["style"]["heartColor"],
        config["style"]["emissionStrength"],
    )
    points = create_heart_points(config["geometry"])
    create_point_mesh("heart-point-cloud", points, material, collection, rotation_rig)
    configure_camera(config["style"])
    configure_render(profile, config["style"], output_path)
    animate_rotation(rotation_rig, profile, config["style"])

    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    if args.render:
        bpy.ops.render.render(animation=True)


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Run tests and build**

Run:

```powershell
npm run test:005
npm run build:005
```

Expected: both commands pass.

- [ ] **Step 7: Generate the Blender scene**

Run:

```powershell
npm run scene:005
```

Expected: Blender exits with code 0 and writes `005-pink-heart-point-cloud/scene/pink-heart-point-cloud.blend`.

- [ ] **Step 8: Commit Blender scene tooling**

Run:

```powershell
git add 005-pink-heart-point-cloud/scripts 005-pink-heart-point-cloud/tests/heartPointCloud.test.ts 005-pink-heart-point-cloud/scene/pink-heart-point-cloud.blend
git commit -m "Add Blender heart point cloud scene"
```

## Task 4: Documentation

**Files:**
- Create: `005-pink-heart-point-cloud/README.md`

- [ ] **Step 1: Write experiment README**

Create `005-pink-heart-point-cloud/README.md`:

````md
# Pink Heart Point Cloud

一个用 Blender 生成的粉色低密度心形点阵云旋转错觉实验。目标是让心形保持清晰，同时减少实体表面、强光照、透视和阴影带来的前后方向线索，让观众有机会反复感知顺时针或逆时针旋转。

## 文件结构

```text
005-pink-heart-point-cloud/
├─ scripts/
│  ├─ create_scene.py       # Blender 场景生成与渲染脚本
│  ├─ heart-config.json     # 点云、运动、相机、输出规格
│  └─ run-blender.mjs       # Node 包装脚本
├─ src/
│  └─ heartPointCloud.ts    # 可测试的心形点云生成逻辑
├─ tests/
│  └─ heartPointCloud.test.ts
├─ scene/                   # 生成的 .blend 文件
└─ output/                  # 生成的 MP4 文件
```

## 命令

默认使用：

```powershell
D:\software\Blender 4.5 LTS\blender.exe
```

如果 Blender 在别的位置，先设置：

```powershell
$env:BLENDER_EXE = "D:\path\to\blender.exe"
```

生成 `.blend` 场景文件：

```powershell
npm run scene --workspace @illusion-lab/pink-heart-point-cloud
```

渲染低清预览：

```powershell
npm run render:preview --workspace @illusion-lab/pink-heart-point-cloud
```

渲染竖屏最终版：

```powershell
npm run render:final --workspace @illusion-lab/pink-heart-point-cloud
```

根目录快捷命令：

```powershell
npm run scene:005
npm run render:005:preview
npm run render:005:final
```

## 错觉设计

- 使用 640 个左右的粉色发光点，而不是实体心形表面。
- 点云深度较浅，避免稳定的前后遮挡判断。
- 使用正交相机和恒速旋转，不使用透视镜头。
- 默认不添加阴影；如果后续需要空间参照，只能加入极淡且相位联动的地面线索。
- 12 秒总时长，6 秒一圈，预览时能看到两次完整旋转。
````

- [ ] **Step 2: Commit documentation**

Run:

```powershell
git add 005-pink-heart-point-cloud/README.md
git commit -m "Document pink heart point cloud experiment"
```

## Task 5: Full Verification

**Files:**
- Verify generated: `005-pink-heart-point-cloud/scene/pink-heart-point-cloud.blend`
- Verify optional generated: `005-pink-heart-point-cloud/output/pink-heart-point-cloud-preview.mp4`

- [ ] **Step 1: Run focused verification**

Run:

```powershell
npm run test:005
npm run build:005
npm run scene:005
```

Expected: all commands pass and the `.blend` file is regenerated.

- [ ] **Step 2: Run root verification**

Run:

```powershell
npm run build
npm run test
```

Expected: all workspace builds and tests pass.

- [ ] **Step 3: Render preview if Blender scene generation is successful**

Run:

```powershell
npm run render:005:preview
```

Expected: Blender exits with code 0 and writes `005-pink-heart-point-cloud/output/pink-heart-point-cloud-preview.mp4`.

- [ ] **Step 4: Inspect generated artifact paths**

Run:

```powershell
Get-ChildItem 005-pink-heart-point-cloud/scene,005-pink-heart-point-cloud/output -Force
```

Expected: `pink-heart-point-cloud.blend` exists, and preview MP4 exists if Step 3 was run.

- [ ] **Step 5: Report final status**

Summarize:

```text
Implemented 005-pink-heart-point-cloud.
Verified: npm run test:005, npm run build:005, npm run scene:005, npm run build, npm run test.
Generated: 005-pink-heart-point-cloud/scene/pink-heart-point-cloud.blend.
Preview render: report whether 005-pink-heart-point-cloud/output/pink-heart-point-cloud-preview.mp4 exists.
```

## Self-Review

- Spec coverage: the tasks create the independent `005-pink-heart-point-cloud/` experiment, low-density pink point cloud, shallow depth, orthographic Blender scene, constant loopable rotation, tests, commands, and documentation.
- Unresolved-marker scan: no task contains deferred work markers or undefined later-only names.
- Type consistency: `HeartPointCloudConfig`, `createHeartPointCloud`, `isInsideHeart`, and `getPointCloudBounds` are defined before tests rely on them. Config keys match both TypeScript tests and Blender Python code.
