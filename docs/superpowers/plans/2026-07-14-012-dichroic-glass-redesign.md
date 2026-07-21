# 012 Dichroic Glass Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace 012's white point cloud with one low-saturation smoked dichroic-glass shell while preserving its geometry, orthographic rotation, loop, and preview workflow.

**Architecture:** The JSON configuration becomes the single source of truth for the glass material, restricted cyan-violet-magenta facing palette, paired area lights, background, camera, and render profiles. Blender builds one closed five-vertex/six-face mesh and one node material, records a glass-specific scene contract, then renders the existing phase and preview artifacts. TypeScript retains only geometry, projection, and loop behavior; point-sampling code and tests are removed because no render path consumes them.

**Tech Stack:** TypeScript, Vitest, Blender 4.5 LTS Python API, Eevee Next, Principled BSDF thin-film inputs, Layer Weight/Color Ramp, Node.js, ffprobe.

## Global Constraints

- Keep exactly five source vertices and six outward triangular faces in one closed mesh.
- Use one material for all faces and no point cloud, edge object, middle belt, inner particle, bevel ornament, ground, HDRI, or camera motion.
- Restrict the palette to deep blue-black, cyan-blue, violet, and restrained magenta.
- Keep orthographic framing, 5.4 seconds per turn, 10.8 seconds total, linear interpolation, and the existing nine inspection phases.
- Render only the scene, phase stills, contact sheet, and 360×640 preview; do not render the 720×1280 final MP4.

---

### Task 1: Replace the point profile contract with a glass profile

**Files:**
- Modify: `012-seamless-triangular-bipyramid-depth-rotation-illusion/tests/triangularBipyramidGeometry.test.ts`
- Modify: `012-seamless-triangular-bipyramid-depth-rotation-illusion/src/triangularBipyramidGeometry.ts`
- Modify: `012-seamless-triangular-bipyramid-depth-rotation-illusion/scripts/triangular-bipyramid-config.json`

**Interfaces:**
- Consumes: the existing JSON config path and `createTriangularBipyramid`, `projectedWidth`, and `rotationAtFrame` APIs.
- Produces: `renderMode: "dichroic-glass"`, a glass material block, a three-pair area-light block, and a TypeScript geometry API with no surface-sampling exports.

- [x] **Step 1: Write the failing glass configuration test**

```ts
it('uses the approved dichroic glass render contract', () => {
  expect(renderConfig.renderMode).toBe('dichroic-glass');
  expect(renderConfig).not.toHaveProperty('geometry.pointsPerFace');
  expect(renderConfig.material).toMatchObject({
    ior: 1.47,
    roughness: 0.13,
    transmissionWeight: 0.78,
    thinFilmThickness: 420,
    thinFilmIor: 1.33
  });
  expect(renderConfig.material.facingColors).toHaveLength(4);
  expect(renderConfig.lighting.pairCount).toBe(3);
});
```

- [x] **Step 2: Run the focused test and verify RED**

Run: `npm run test:012 -- --run tests/triangularBipyramidGeometry.test.ts`

Expected: FAIL because the current config has point counts and no `renderMode`, `material`, or `lighting` blocks.

- [x] **Step 3: Write the glass configuration**

Use these exact initial values:

```json
"renderMode": "dichroic-glass",
"material": {
  "ior": 1.47,
  "roughness": 0.13,
  "metallic": 0.04,
  "transmissionWeight": 0.78,
  "coatWeight": 0.24,
  "coatRoughness": 0.08,
  "thinFilmThickness": 420.0,
  "thinFilmIor": 1.33,
  "emissionStrength": 0.035,
  "volumeColor": [0.006, 0.018, 0.065],
  "volumeDensity": 0.42,
  "facingColors": [
    { "position": 0.0, "color": [0.025, 0.24, 0.42, 1.0] },
    { "position": 0.34, "color": [0.09, 0.025, 0.28, 1.0] },
    { "position": 0.64, "color": [0.25, 0.018, 0.16, 1.0] },
    { "position": 1.0, "color": [0.004, 0.014, 0.055, 1.0] }
  ]
},
"lighting": {
  "pairCount": 3,
  "radius": 4.6,
  "height": 2.1,
  "energy": 310.0,
  "size": 3.0,
  "colors": [[0.46, 0.78, 1.0], [0.64, 0.48, 1.0], [1.0, 0.42, 0.68]]
}
```

Set `style.backgroundColor` to `[0.0008, 0.002, 0.009]`, `glowThreshold` to `1.05`, and `glowSize` to `5`. Remove point-count, seed, jitter, and point-size fields.

- [x] **Step 4: Remove obsolete TypeScript point-sampling APIs and tests**

Delete `SurfaceSample`, `SurfaceSampleOptions`, `sampleTriangleSurface`, `mulberry32`, `clampUnit`, and `shuffledIndices` from the source. Delete sampling-inside, reproducibility, height-band, nearest-neighbor-direction, and signed-seed tests. Preserve vertex, face, normal, area, no-dedicated-edge, projection-width, and loop tests.

- [x] **Step 5: Run GREEN verification**

Run: `npm run test:012 && npm run build:012`

Expected: the remaining geometry tests plus the glass configuration test pass, and TypeScript exits 0.

### Task 2: Build the unified dichroic glass scene

**Files:**
- Modify: `012-seamless-triangular-bipyramid-depth-rotation-illusion/scripts/create_scene.py`

**Interfaces:**
- Consumes: `geometry`, `material`, `lighting`, `style`, and profile blocks from the revised JSON.
- Produces: object `triangular-bipyramid-glass-shell`, material `dichroic-smoked-glass`, six paired `AREA` lights, and the existing rotation rig/camera/animation.

- [x] **Step 1: Replace particle generation with one closed shell mesh**

```python
def create_glass_shell(vertices, faces, material, collection, parent):
    mesh = bpy.data.meshes.new(SHELL_NAME)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(SHELL_NAME, mesh)
    obj.parent = parent
    obj.data.materials.append(material)
    obj["source_vertex_count"] = len(vertices)
    obj["exposed_triangle_count"] = len(faces)
    obj["point_count"] = 0
    collection.objects.link(obj)
    return obj
```

- [x] **Step 2: Create the restricted facing-color glass material**

Create a `ShaderNodeLayerWeight` feeding a four-stop `ShaderNodeValToRGB`. Connect its color to Principled `Base Color` and `Emission Color`; set Principled inputs from the material JSON. Connect `ShaderNodeVolumeAbsorption` to Material Output `Volume`. Set `surface_render_method = "DITHERED"`, `use_screen_refraction = True`, and `refraction_depth = 0.35`.

- [x] **Step 3: Add three opposed area-light pairs**

For pair index `0..2`, use azimuths `0°`, `120°`, and `240°`. Place one light at `(r*cos(a), r*sin(a), +height)` and its mate at the negated XYZ position, give both the corresponding configured color/energy/size, and aim both at the origin. This yields six broad lights with inversion symmetry.

- [x] **Step 4: Enable Eevee transmission and glass render settings**

Set `scene.eevee.use_raytracing = True`, `scene.eevee.ray_tracing_method = "SCREEN"`, preview samples to 32, final samples to 64, and retain the existing compositor Fog Glow using the revised threshold and size.

- [x] **Step 5: Replace point-cloud inspection metadata**

Write `surface.shellObjectCount`, `surface.meshVertexCount`, `surface.meshTriangleCount`, `surface.pointCount`, `surface.materialCount`, `surface.materialName`, plus scene `lightCount`, `lightTypes`, camera, frame range, keyframes, and still hashes. Runtime assertions must require 5 mesh vertices, 6 polygons, 0 points, 1 mesh object, 1 material, and 6 area lights.

- [x] **Step 6: Generate the scene and audit the `.blend` file**

Run: `npm run scene:012`

Open the generated blend in background mode and verify one five-vertex/six-polygon mesh, one material, six `AREA` lights, ORTHO camera, final resolution 720×1280, frames 1–324, loop keyframe 325, and linear interpolation.

### Task 3: Calibrate stills, render preview, and update documentation

**Files:**
- Modify: `012-seamless-triangular-bipyramid-depth-rotation-illusion/README.md`
- Regenerate: `012-seamless-triangular-bipyramid-depth-rotation-illusion/output/stills/*.png`
- Regenerate: `012-seamless-triangular-bipyramid-depth-rotation-illusion/output/inspection.json`
- Regenerate: `012-seamless-triangular-bipyramid-depth-rotation-illusion/output/seamless-triangular-bipyramid-depth-rotation-illusion-preview.mp4`

**Interfaces:**
- Consumes: the glass scene from Task 2.
- Produces: a visually approved phase contact sheet and low-resolution preview, with no final MP4.

- [x] **Step 1: Render nine phase stills**

Run: `npm run render:012:stills`

Expected: nine phase PNGs, pixel-identical 0°/360°, eight distinct non-loop phase hashes, and a horizontal contact sheet.

- [x] **Step 2: Perform the aesthetic gate**

Inspect the contact sheet at original resolution. If the object disappears, increase only paired-light energy or emission strength. If colors become muddy, reduce volume density or transmission overlap. If rainbow saturation dominates, lower facing-ramp RGB values. Do not add outlines, edge objects, a middle belt, or extra geometry. Repeat still rendering after one parameter group change at a time.

- [x] **Step 3: Render and inspect the preview**

Run: `npm run render:012:preview`

Extract five motion phases and check that facet highlights move cleanly, the silhouette stays legible, and no material animation or brightness pulse exists.

- [x] **Step 4: Update README and run final verification**

Describe the unified dichroic glass shell, paired area lights, commands, and output gate. Run `npm test`, `npm run build`, and `git diff --check`. Use `ffprobe` to verify H.264, 360×640, 15 fps, 10.8 seconds, and 162 frames. Confirm the final MP4 is absent.
