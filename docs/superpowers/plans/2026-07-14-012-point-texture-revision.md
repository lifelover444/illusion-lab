# 012 Point Texture Revision Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Match 012's point scale and visual spacing to experiment 008 while preserving the approved geometry, camera, material, and animation.

**Architecture:** Keep the existing unified six-face sampler and Blender scene generator unchanged. Treat the experiment JSON as the single render source of truth, add a regression test that reads it directly, then regenerate and visually audit the ignored Blender artifacts.

**Tech Stack:** TypeScript, Vitest, Blender 4.5 LTS Python API, Node.js render wrapper, ffprobe, Pillow.

## Global Constraints

- Use `600` points per face and `3,600` points total.
- Use point radii `0.0014–0.0045`, matching 008's main particles.
- Keep seed, sampling algorithm, cold-white material, emission, Bloom, orthographic camera, geometry, composition, speed, and duration unchanged.
- Render the scene, nine phase stills, contact sheet, and preview only; do not render the final MP4.

---

### Task 1: Lock and apply the revised point profile

**Files:**
- Modify: `012-seamless-triangular-bipyramid-depth-rotation-illusion/tests/triangularBipyramidGeometry.test.ts`
- Modify: `012-seamless-triangular-bipyramid-depth-rotation-illusion/scripts/triangular-bipyramid-config.json`
- Modify: `012-seamless-triangular-bipyramid-depth-rotation-illusion/README.md`

**Interfaces:**
- Consumes: `geometry.pointsPerFace`, `geometry.pointSizeMin`, and `geometry.pointSizeMax` from the JSON render configuration.
- Produces: A render configuration fixed at 600 points per face and point radii 0.0014–0.0045.

- [x] **Step 1: Add the failing configuration regression test**

```ts
import { readFileSync } from 'node:fs';

const renderConfig = JSON.parse(
  readFileSync(
    new URL('../scripts/triangular-bipyramid-config.json', import.meta.url),
    'utf8'
  )
);

it('uses the approved 008-scale sparse point profile', () => {
  expect(renderConfig.geometry.pointsPerFace).toBe(600);
  expect(renderConfig.geometry.pointSizeMin).toBe(0.0014);
  expect(renderConfig.geometry.pointSizeMax).toBe(0.0045);
  expect(renderConfig.geometry.pointsPerFace * geometry.faces.length).toBe(3600);
});
```

- [x] **Step 2: Run the focused test and verify RED**

Run: `npm run test:012 -- --run tests/triangularBipyramidGeometry.test.ts`

Expected: FAIL because the current configuration is 950 points per face with radii 0.0045–0.009.

- [x] **Step 3: Apply the minimal configuration change**

```json
"pointsPerFace": 600,
"pointSizeMin": 0.0014,
"pointSizeMax": 0.0045
```

Update existing sampling tests and README numbers to the same values; do not alter the sampler implementation.

- [x] **Step 4: Run focused tests and build, verifying GREEN**

Run: `npm run test:012 && npm run build:012`

Expected: all 012 tests pass and TypeScript exits 0.

### Task 2: Regenerate and audit preview artifacts

**Files:**
- Regenerate: `012-seamless-triangular-bipyramid-depth-rotation-illusion/scene/seamless-triangular-bipyramid-depth-rotation-illusion.blend`
- Regenerate: `012-seamless-triangular-bipyramid-depth-rotation-illusion/output/stills/*.png`
- Regenerate: `012-seamless-triangular-bipyramid-depth-rotation-illusion/output/seamless-triangular-bipyramid-depth-rotation-illusion-preview.mp4`
- Regenerate: `012-seamless-triangular-bipyramid-depth-rotation-illusion/output/inspection.json`

**Interfaces:**
- Consumes: The revised JSON configuration from Task 1.
- Produces: A 3,600-point Blender scene, nine phase stills, contact sheet, and 360×640 preview.

- [x] **Step 1: Generate scene and nine phase stills**

Run: `npm run scene:012 && npm run render:012:stills`

Expected: Blender exits 0, inspection reports 3,600 points, and the contact sheet contains nine images.

- [x] **Step 2: Compare point coverage against 008**

Use Pillow to measure bright-pixel occupancy inside each subject bounding box and inspect the contact sheet at original resolution. The revised 012 must have visibly separated points and substantially lower high-brightness occupancy than the first 012 render, without losing the double-pointed silhouette.

- [x] **Step 3: Render the low-resolution preview**

Run: `npm run render:012:preview`

Expected: Blender exits 0 and writes the preview MP4; no final MP4 is created.

- [x] **Step 4: Run final verification**

Run: `npm test && npm run build && git diff --check`

Use `ffprobe` to verify H.264, 360×640, 15 fps, 10.8 seconds, and 162 frames. Verify inspection reports one mesh, one material, zero lights, 3,600 points, distinct non-loop phases, and pixel-identical 0°/360° stills.
