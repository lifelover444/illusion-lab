# Seamless Triangular Bipyramid Depth Rotation Illusion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build experiment 012 as a self-contained, tested Blender point-cloud triangular bipyramid and deliver its scene, nine phase stills, contact sheet, and low-resolution looping preview without rendering the final video.

**Architecture:** TypeScript owns the deterministic geometry, sampling, projection, and loop contracts exercised by Vitest. A self-contained Python generator mirrors the formulas in Blender, combines all 5,700 cold-white point octahedra into one mesh under one rotation rig, renders the requested artifacts, and records inspection metadata. Root npm workspace scripts expose experiment-local commands.

**Tech Stack:** TypeScript 5.4, Vitest 1.6, Node.js workspace scripts, Python in Blender 4.5 LTS, Eevee Next, Blender compositor, ffmpeg-backed H.264 output.

## Global Constraints

- Create only `012-seamless-triangular-bipyramid-depth-rotation-illusion`; do not create an octahedron or comparison variant.
- Use `R = 1.0`, `H = sqrt(2)`, `initialPhase = 30°`, five vertices, and six outward triangular faces.
- Generate one unified six-face point-cloud shell with 5,700 fixed points, one cold-white material, no edge lines, no middle belt, and no internal particles.
- Animate only rigid rotation around world `Z`: 5.4 seconds per turn, 10.8 seconds total, linear interpolation, and `loopFrame = frameEnd + 1`.
- Preview is 360 × 640 at 15 fps; final profile is 720 × 1280 at 30 fps but MUST NOT be rendered in this implementation round.
- Render stills at 0°, 30°, 60°, 90°, 120°, 180°, 240°, 300°, and 360° before rendering the preview.
- Preserve a black background, orthographic stationary camera, uniform depth-neutral emission, and only very light bloom.
- Keep the experiment self-contained and use the root package scripts and numbered-directory conventions from `AGENTS.md`.

---

### Task 1: Geometry and deterministic sampling contract

**Files:**
- Create: `012-seamless-triangular-bipyramid-depth-rotation-illusion/package.json`
- Create: `012-seamless-triangular-bipyramid-depth-rotation-illusion/tsconfig.json`
- Create: `012-seamless-triangular-bipyramid-depth-rotation-illusion/vitest.config.ts`
- Create: `012-seamless-triangular-bipyramid-depth-rotation-illusion/tests/triangularBipyramidGeometry.test.ts`
- Create: `012-seamless-triangular-bipyramid-depth-rotation-illusion/src/triangularBipyramidGeometry.ts`

**Interfaces:**
- Produces: `createTriangularBipyramid(config): TriangularBipyramid`, `triangleArea(a,b,c): number`, `faceNormal(face,vertices): Point3`, `sampleTriangleSurface(...)`, `projectedWidth(...)`, `rotationAtFrame(...)`, and exported point/face/sample types.
- Consumes: no earlier task interfaces.

- [ ] **Step 1: Scaffold only package and compiler/test configuration**

Create a private ESM workspace package named `@illusion-lab/seamless-triangular-bipyramid-depth-rotation-illusion` with `build: tsc` and `test: vitest run`; configure strict TypeScript without emit and Vitest node environment.

- [ ] **Step 2: Write the failing geometry tests**

Write tests that call the wished-for interfaces and assert all twelve required contracts: five unique vertices, six unique faces, symmetric poles, middle plane, 120° spacing, equal face areas, outward normals, samples inside triangles, no dedicated edge collection, loop equality, safe projected widths for all nine phases, and byte-for-byte deterministic seeded samples.

- [ ] **Step 3: Run the focused test and verify RED**

Run:

```powershell
npm run test --workspace @illusion-lab/seamless-triangular-bipyramid-depth-rotation-illusion
```

Expected: FAIL because `src/triangularBipyramidGeometry.ts` does not exist.

- [ ] **Step 4: Implement the minimal geometry module**

Use these public types and defaults:

```ts
export type Point3 = { x: number; y: number; z: number };
export type TriangleFace = readonly [number, number, number];
export type SurfaceSample = Point3 & { size: number; faceIndex: number };
export type TriangularBipyramid = {
  vertices: readonly Point3[];
  faces: readonly TriangleFace[];
  dedicatedEdges: readonly never[];
};
export const DEFAULT_GEOMETRY = {
  radius: 1,
  halfHeight: Math.SQRT2,
  initialPhaseDegrees: 30
} as const;
```

Build the poles and three middle vertices, orient every face by reversing it when `dot(normal, faceCentroid) <= 0`, use a Mulberry32 seeded generator, use stratified square cells mapped through sqrt barycentric sampling with small clamped jitter, bias sizes toward `pointSizeMin`, rotate around `Z`, project camera-forward onto world `Y`, and normalize loop angles modulo `2π`.

- [ ] **Step 5: Run test and build to verify GREEN**

Run:

```powershell
npm run test --workspace @illusion-lab/seamless-triangular-bipyramid-depth-rotation-illusion
npm run build --workspace @illusion-lab/seamless-triangular-bipyramid-depth-rotation-illusion
```

Expected: all focused tests pass and TypeScript exits 0.

### Task 2: Blender generator and local commands

**Files:**
- Create: `012-seamless-triangular-bipyramid-depth-rotation-illusion/scripts/triangular-bipyramid-config.json`
- Create: `012-seamless-triangular-bipyramid-depth-rotation-illusion/scripts/create_scene.py`
- Create: `012-seamless-triangular-bipyramid-depth-rotation-illusion/scripts/run-blender.mjs`
- Modify: `012-seamless-triangular-bipyramid-depth-rotation-illusion/package.json`

**Interfaces:**
- Consumes: Task 1 geometry constants and contracts, mirrored exactly in JSON/Python.
- Produces: `scene`, `render:stills`, `render:preview`, and `render:final` npm commands; Blender scene generator command modes `scene`, `stills`, `preview`, `final`.

- [ ] **Step 1: Add config values and command wrapper**

Set 950 points per face, seed 12012, point size 0.0045–0.009, color `[0.82,0.91,1.0]`, emission 1.22, rotation cycle 5.4 seconds, 10.8-second preview/final profiles, preview samples 16, final samples 32, phase list `[0,30,60,90,120,180,240,300,360]`, orthographic camera at `(0,-8,0)`, and an initial orthographic scale near 4.35. Default Blender executable is `D:\software\Blender 4.5 LTS\blender.exe`, overridable by `BLENDER_EXE`.

- [ ] **Step 2: Implement the unified scene generator**

In Python, construct all six faces in one list, sample each through the same stratified sqrt-barycentric function, and pass all samples once to `create_point_cloud_mesh`. Create one object named `triangular-bipyramid-point-cloud`, one material named `cold-white-point-emission`, one parent empty named `triangular-bipyramid-rotation-rig`, one orthographic camera, no lights, and a pure-black world. Animate only the rig `rotation_euler.z` from 0 at frame 1 to 720° at `frame_end + 1` with linear interpolation.

- [ ] **Step 3: Implement still and contact-sheet rendering**

For each requested angle, set the rig angle directly and render `phase-000.png` through `phase-360.png` without changing geometry or the camera. Build a single horizontal contact sheet inside Blender/Python by loading the nine PNGs through Pillow if available in the bundled runtime, otherwise use Blender's image API or invoke ffmpeg from the Node wrapper. Save `output/stills/triangular-bipyramid-contact-sheet.png` and write `output/inspection.json` containing object/material/light counts, phase hashes, point count, and render settings.

- [ ] **Step 4: Generate the Blender scene**

Run:

```powershell
npm run scene --workspace @illusion-lab/seamless-triangular-bipyramid-depth-rotation-illusion
```

Expected: Blender exits 0 and writes `scene/seamless-triangular-bipyramid-depth-rotation-illusion.blend`.

### Task 3: Repository integration and documentation

**Files:**
- Create: `012-seamless-triangular-bipyramid-depth-rotation-illusion/README.md`
- Modify: `.gitignore`
- Modify: `package.json`
- Modify: `package-lock.json`
- Modify: `README.md`

**Interfaces:**
- Consumes: experiment-local npm package and commands from Tasks 1–2.
- Produces: root scripts `scene:012`, `render:012:stills`, `render:012:preview`, `render:012:final`, `build:012`, and `test:012`.

- [ ] **Step 1: Document the experiment**

Describe the complete triangular bipyramid, unified point shell, depth-neutral rendering, exact animation/output behavior, artifact paths, commands, default Blender path, and prohibition on final rendering before user approval.

- [ ] **Step 2: Integrate the workspace**

Add the 012 directory to root `workspaces`; add the six root scripts; add the experiment to the README project table and common commands; ignore its `scene/` and `output/` directories.

- [ ] **Step 3: Refresh workspace metadata**

Run:

```powershell
npm install
```

Expected: npm exits 0 and `package-lock.json` contains the 012 workspace package.

- [ ] **Step 4: Verify root entry points**

Run:

```powershell
npm run test:012
npm run build:012
```

Expected: focused tests and build pass from the root.

### Task 4: Still rendering and visual inspection

**Files:**
- Generated: `012-seamless-triangular-bipyramid-depth-rotation-illusion/output/stills/*.png`
- Generated: `012-seamless-triangular-bipyramid-depth-rotation-illusion/output/stills/triangular-bipyramid-contact-sheet.png`
- Generated: `012-seamless-triangular-bipyramid-depth-rotation-illusion/output/inspection.json`
- Modify if required by inspection: `012-seamless-triangular-bipyramid-depth-rotation-illusion/scripts/triangular-bipyramid-config.json`

**Interfaces:**
- Consumes: `render:012:stills` root script and generated `.blend` scene.
- Produces: approved static render settings for preview.

- [ ] **Step 1: Render nine phase stills**

Run:

```powershell
npm run render:012:stills
```

Expected: nine phase PNGs, one horizontal contact sheet, and inspection JSON exist.

- [ ] **Step 2: Verify artifact identities and dimensions**

Use file hashing and image metadata to assert phase 0° and 360° are pixel-identical, every phase is 360 × 640, the contact sheet contains all nine phases in order, and no phase is blank.

- [ ] **Step 3: Inspect the contact sheet visually**

Check that the object reads as a complete double-pointed crystal in every phase, remains non-degenerate, preserves both tips, has black gaps between points, shows no bright middle belt or solid white face, and uses no face-dependent color/brightness cue. If the first pass violates a criterion, modify only height within 1.25–1.35, point size/density, orthographic scale, or bloom, regenerate the scene, and repeat still verification.

### Task 5: Low-resolution preview

**Files:**
- Generated: `012-seamless-triangular-bipyramid-depth-rotation-illusion/output/seamless-triangular-bipyramid-depth-rotation-illusion-preview.mp4`

**Interfaces:**
- Consumes: approved still configuration from Task 4.
- Produces: 360 × 640, 15 fps, 10.8-second H.264 preview.

- [ ] **Step 1: Render preview only after still approval**

Run:

```powershell
npm run render:012:preview
```

Expected: Blender exits 0 and writes the preview MP4; do not run `render:012:final`.

- [ ] **Step 2: Inspect media metadata and loop samples**

Use `ffprobe` to assert width 360, height 640, frame rate 15, duration approximately 10.8 seconds, H.264 codec, and 162 frames. Extract the first frame and the conceptual loop frame from the scene logic; verify the normalized rotations match and inspect early/late decoded frames for no animation other than rigid rotation.

### Task 6: Complete verification and handoff

**Files:**
- Review all tracked files and generated artifacts from Tasks 1–5.

**Interfaces:**
- Consumes: all previous deliverables.
- Produces: evidence-backed user handoff without a final-resolution render.

- [ ] **Step 1: Run complete test and build verification**

Run:

```powershell
npm run test:012
npm run build:012
npm test
npm run build
git diff --check
```

Expected: every command exits 0, no tests fail, and no whitespace errors are reported.

- [ ] **Step 2: Audit requirements and scene metadata**

Confirm the tracked implementation and `inspection.json` demonstrate five vertices, six faces, 5,700 points, one point-cloud mesh, one emission material, zero lights, one rigid rotation rig, the requested camera/render settings, all nine phases, matching 0°/360°, and no final MP4.

- [ ] **Step 3: Report artifacts for user confirmation**

Provide clickable paths to the Blender scene, contact sheet, nine-phase directory, preview MP4, source, tests, and README. Explicitly state that the final render was not run and wait for user approval before executing it.
