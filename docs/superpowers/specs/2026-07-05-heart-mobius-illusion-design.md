# Heart Mobius Illusion Design

Date: 2026-07-05
Project: `005-heart-blender-illusion`
Status: Approved design, not yet implemented

## Summary

The experiment will build a glowing Mobius heart ring in Blender. The subject is not a silhouette and not a solid crystal heart. It is a continuous semi-transparent ribbon following a heart-shaped path, with a 180 degree Mobius twist along the closed loop.

The goal is a vertical-axis rotation that keeps continuous spatial motion while preserving depth ambiguity. Viewers should be able to perceive the same linear rotation as clockwise or counterclockwise because the ribbon has no strong front/back marker, uses orthographic projection, and avoids one-sided lighting cues.

## Goals

- Generate the model procedurally from code inside `005-heart-blender-illusion`.
- Keep the first implemented model recognizably heart-shaped from the front.
- Use a continuous ribbon surface so the motion feels like rotation, not frame morphing.
- Preserve bistable direction perception by weakening front/back, near/far, and surface-side cues.
- Render preview and final vertical videos through the existing workspace commands.

## Non-Goals

- Do not make a pure black silhouette.
- Do not make a physically realistic glass or crystal heart in the first pass.
- Do not use a normal cube, solid block, or conventional opaque polyhedron as the subject.
- Do not add strong cast shadows, perspective depth, asymmetric texture, or one-sided highlights.
- Do not hand-keyframe shape morphs to fake the rotation.

## User-Facing Behavior

The final render should show a pink or magenta glowing heart-shaped ribbon floating against a dark background. Over a 12 second clip, the ring rotates twice around a vertical axis at constant speed.

At the front phase, the heart shape should read clearly. At the side phase, the form should compress but still reveal a continuous twisted band instead of collapsing into a flat line. At the rear phase, the heart shape should return with similar visual strength. The illusion succeeds when the viewer can lose certainty about whether the ring is turning clockwise or counterclockwise.

## Geometry

The model is generated from a parametric heart centerline sampled at a fixed count, initially around 240 points. The 2D heart curve is placed in the `X/Z` plane with `Z` as vertical height. The ribbon's depth coordinate uses `Y`.

For each centerline sample:

- Compute a tangent from neighboring curve points.
- Compute a local normal in the heart plane.
- Build a ribbon cross direction from the local normal plus a Mobius twist angle.
- Advance the twist by 180 degrees over one complete loop.
- Emit two ribbon edge vertices per sample.
- Connect adjacent samples with quad faces.
- Close the final sample back to the first sample.

The first pass should use one 180 degree twist. The design may expose `mobiusTwistAmount` for tuning in the range of roughly 150 to 210 degrees, but 180 degrees remains the default.

The ribbon should be thin enough to stay delicate and ambiguous, but wide enough to read as a surface. The initial band width target is roughly 10 to 16 percent of the heart height.

## Materials

The material should use emission and transparency rather than realistic directional lighting.

Default look:

- Semi-transparent pink ribbon surface.
- Brighter magenta or soft white edge lines.
- Double-sided visual treatment.
- Very weak bloom or glow.
- Dark background.

Direction-locking material choices are intentionally excluded from the first pass:

- No glass refraction.
- No metallic specular highlight.
- No single bright highlight fixed to one side.
- No different front and back colors.
- No texture pattern that marks travel direction around the ring.

## Camera And Motion

The camera uses orthographic projection and faces the object from the negative `Y` direction. The model rotates around the vertical `Z` axis.

Motion defaults:

- `rotationCycleSeconds`: 6
- `totalSeconds`: 12
- `easing`: linear
- `rotationAxis`: vertical `Z`
- `cycles`: 2

The orthographic scale should frame the heart with comfortable margins for a vertical 9:16 render. The camera should not use perspective projection because near/far size changes would expose depth order.

## Scene

The scene should avoid a physical floor in the first pass. If a spatial cue is needed later, use only a very faint phase-linked glow or haze behind the object, not a fixed cast shadow.

Lighting should be minimal because the object is primarily emissive. Any ambient light should be symmetrical and soft.

## Components

The implementation should keep the experiment self-contained:

- `scripts/heart-illusion-config.json` stores tunable render, model, material, camera, and motion values.
- `scripts/create_scene.py` builds the Blender scene from the config.
- `scripts/run-blender.mjs` invokes Blender for scene generation and rendering profiles.
- `src/heartIllusionPlan.ts` exposes testable planning and configuration expectations.
- `tests/heartIllusionPlan.test.ts` validates the constraints that protect the illusion.

## Data Flow

1. The Node runner receives `scene`, `preview`, or `final`.
2. It loads the JSON config and selects the matching render profile.
3. It launches Blender with `create_scene.py`, the mode, and the config path.
4. The Blender script creates the Mobius heart mesh, materials, camera, animation, and render settings.
5. Preview and final modes render to the configured output path.

## Error Handling

The runner should fail with a clear message if Blender cannot be found. The Blender script should validate required config fields before generating the scene. Invalid values, such as non-positive sample counts, non-positive band width, unsupported camera projection, or non-linear easing, should fail early.

Output directories should be created when needed. Existing render outputs may be overwritten by explicit render commands.

## Testing

Unit tests should cover the design constraints without requiring Blender:

- The project has moved from planning-only to modeling-started when implementation begins.
- The selected subject is a Mobius heart ring, not a silhouette or solid crystal heart.
- The camera remains orthographic.
- Motion remains linear around the vertical axis.
- The default render duration contains exactly two complete cycles.
- Direction-locking cues such as perspective camera, cast shadow, asymmetric texture, glass refraction, and one-sided highlight are rejected.
- Ambiguity-preserving cues such as emission material, transparent surface, matching front/back treatment, and visible continuous ribbon are present.
- Config values keep the ribbon surface readable at side phases.

Visual verification should inspect frames around 0, 90, 180, and 270 degrees:

- 0 degrees: clear front-facing heart.
- 90 degrees: compressed but continuous twisted ribbon.
- 180 degrees: heart shape returns with similar strength.
- 270 degrees: second compressed side phase, still ambiguous.

## Acceptance Criteria

- `npm run test:005` passes.
- `npm run build:005` passes.
- `npm run scene:005` creates a Blender scene once implementation starts.
- `npm run render:005:preview` creates a short preview video.
- The rendered subject is a glowing Mobius heart ring, not a silhouette, cube, or solid crystal heart.
- The render avoids strong perspective, shadows, directional highlights, and asymmetric markings.
- The rotation feels continuous and can plausibly be interpreted in either direction.

