# Pink Heart Point Cloud Blender Illusion Design

## Goal

Create the first Blender prototype for a pink heart-shaped point cloud rotation illusion. The prototype should make the heart readable while keeping depth cues weak enough that viewers can repeatedly perceive clockwise or counterclockwise rotation.

## Scope

Add a new independent experiment directory:

```text
005-pink-heart-point-cloud/
```

The experiment will generate a `.blend` scene and optional preview/final renders from script. It will not depend on any previous experiment at runtime.

## Recommended Approach

Use a low-density Blender point cloud made from small pink spheres or emissive dots. Points are sampled inside a mathematical 2D heart silhouette, then given a shallow randomized depth. The whole cloud rotates at a constant speed around the vertical axis.

This is preferred over a solid heart mesh because the point cloud gives the viewer fewer solid surface, lighting, and occlusion cues. It should be easier to see the direction flip during repeated viewing.

## Visual Design

- Subject: one centered pink heart point cloud.
- Density: low to medium, roughly 500-900 points in the first pass.
- Shape: classic heart silhouette with a slight lower taper and rounded lobes.
- Depth: shallow cloud thickness, enough to suggest volume but not enough to create a stable front/back reading.
- Camera: orthographic, front-facing, centered on the heart.
- Materials: soft pink emissive points with minimal or no glossy highlights.
- Background: light neutral or very pale warm background.
- Shadows: disabled by default; an optional extremely faint ground cue may be added only if it does not lock rotation direction.
- Motion: constant-speed vertical-axis rotation with no easing.

## Architecture

Follow the existing Blender experiment pattern used by the `004-*` directories:

```text
005-pink-heart-point-cloud/
├─ README.md
├─ package.json
├─ scripts/
│  ├─ create_scene.py
│  ├─ heart-config.json
│  └─ run-blender.mjs
├─ src/
│  └─ heartPointCloud.ts
├─ tests/
│  └─ heartPointCloud.test.ts
├─ scene/
└─ output/
```

`src/heartPointCloud.ts` will hold deterministic point generation rules that can be tested outside Blender. `scripts/create_scene.py` will recreate the same design parameters in Blender and produce the scene/render. `scripts/run-blender.mjs` will wrap the local Blender executable in the same style as existing Blender experiments.

## Data Flow

1. Read `scripts/heart-config.json`.
2. Generate deterministic heart point positions from seed, density, scale, and depth settings.
3. Build a Blender scene with one parent empty containing all dots.
4. Add constant rotation keyframes to the parent empty.
5. Save the `.blend` scene under `scene/`.
6. When requested, render preview or final output to `output/`.

## Testing

Add focused unit tests for the TypeScript point generator:

- generated points are inside the heart silhouette bounds
- the point count matches the configured density
- generation is deterministic for a fixed seed
- depth stays within the configured shallow range
- the generated bounds remain centered around the rotation axis

Run the experiment test command and the root test/build command if root scripts support the new workspace.

## Commands

The experiment should expose:

```powershell
npm run scene --workspace @illusion-lab/pink-heart-point-cloud
npm run render:preview --workspace @illusion-lab/pink-heart-point-cloud
npm run render:final --workspace @illusion-lab/pink-heart-point-cloud
```

Add root package shortcuts for the new experiment, matching the existing build/test/scene/render shortcuts used for Blender experiments.

## Non-Goals

- No realistic solid heart mesh in the first version.
- No complex UI controls.
- No strong shadows, glossy material, directional arrows, or perspective camera.
- No shared rendering framework across the repository.
- No final tuning for social/video delivery until the first model is visually inspected.

## Acceptance Criteria

- A generated Blender scene shows a clearly recognizable pink heart point cloud.
- The point cloud is low enough density that individual points remain visible.
- Rotation is constant and loopable.
- The camera and material choices keep depth cues weak.
- Unit tests cover the point generation rules.
- Documentation explains local commands and the illusion design intent.
