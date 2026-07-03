import { describe, expect, it } from 'vitest';
import config from '../scripts/hourglass-config.json';
import {
  createHourglassComparison,
  createHourglassGeometry,
  createSynchronizedMotionPlans,
  createSolidHourglassGeometry
} from '../src/hourglassGeometry';

type Vec3 = [number, number, number];

const subtract = (left: Vec3, right: Vec3): Vec3 => [
  left[0] - right[0],
  left[1] - right[1],
  left[2] - right[2]
];

const cross = (left: Vec3, right: Vec3): Vec3 => [
  left[1] * right[2] - left[2] * right[1],
  left[2] * right[0] - left[0] * right[2],
  left[0] * right[1] - left[1] * right[0]
];

const dot = (left: Vec3, right: Vec3): number =>
  left[0] * right[0] + left[1] * right[1] + left[2] * right[2];

const centroid = (points: Vec3[]): Vec3 => [
  points.reduce((sum, point) => sum + point[0], 0) / points.length,
  points.reduce((sum, point) => sum + point[1], 0) / points.length,
  points.reduce((sum, point) => sum + point[2], 0) / points.length
];

const faceNormal = (points: Vec3[]): Vec3 => {
  const [first, second, third] = points;

  return cross(subtract(second, first), subtract(third, first));
};

describe('wireframe hourglass geometry', () => {
  it('uses two square wireframe pyramids with no solid faces', () => {
    const geometry = createHourglassGeometry(config.geometry);

    expect(geometry.vertices).toHaveLength(10);
    expect(geometry.edges).toHaveLength(16);
    expect(geometry.faces).toHaveLength(0);
  });

  it('starts with the two pyramid apexes connected at the center', () => {
    const geometry = createHourglassGeometry(config.geometry);
    const topApex = geometry.vertices[0];
    const bottomApex = geometry.vertices[config.geometry.sides + 1];

    expect(topApex).toEqual([0, 0, 0]);
    expect(bottomApex).toEqual([0, 0, 0]);
  });

  it('keeps the final output vertical, smooth, and two full rotations long', () => {
    const finalProfile = config.profiles.final;

    expect(finalProfile.width / finalProfile.height).toBeCloseTo(9 / 16, 5);
    expect(finalProfile.fps).toBe(30);
    expect(finalProfile.seconds).toBe(22);
    expect(finalProfile.fps * finalProfile.seconds).toBe(660);
    expect(config.style.rotationCycleSeconds).toBe(11);
    expect(finalProfile.seconds / config.style.rotationCycleSeconds).toBe(2);
  });

  it('uses four-arm spiral dust and a dynamic apex bridge for the particle effect', () => {
    expect(config.style.particleCount).toBeGreaterThanOrEqual(280);
    expect(config.style.spiralArmCount).toBe(4);
    expect(config.style.bridgeParticleCount).toBeGreaterThan(60);
    expect(config.style.pulseRingCount).toBe(3);
  });
});

describe('depth comparison layout', () => {
  it('places two colored depth controls around the center wireframe illusion', () => {
    const groups = createHourglassComparison(config);

    expect(groups.map((group) => group.id)).toEqual([
      'left-clockwise-depth-control',
      'center-wireframe-illusion',
      'right-counterclockwise-depth-control'
    ]);
    expect(groups.map((group) => group.xOffset)).toEqual([
      config.layout.leftXOffset,
      config.layout.centerXOffset,
      config.layout.rightXOffset
    ]);
    expect(groups[0].role).toBe('depth-control');
    expect(groups[1].role).toBe('illusion');
    expect(groups[2].role).toBe('depth-control');
  });

  it('keeps the center shape depth-ambiguous while side controls use solid colored faces', () => {
    const groups = createHourglassComparison(config);
    const solidGeometry = createSolidHourglassGeometry(config.geometry);

    expect(groups[1].depthCue).toBe('wireframe-only');
    expect(groups[1].geometry.faces).toHaveLength(0);
    expect(groups[0].depthCue).toBe('solid-color');
    expect(groups[2].depthCue).toBe('solid-color');
    expect(solidGeometry.faces).toHaveLength(config.geometry.sides * 2 + 2);
  });

  it('winds solid control faces outward so lighting reads as convex instead of concave', () => {
    const geometry = createSolidHourglassGeometry(config.geometry);
    const topInterior: Vec3 = [0, 0, config.geometry.pyramidHeight * 0.62];
    const bottomInterior: Vec3 = [0, 0, -config.geometry.pyramidHeight * 0.62];

    for (const face of geometry.faces) {
      const points = face.vertices.map((vertexIndex) => geometry.vertices[vertexIndex]);
      const normal = faceNormal(points);
      const center = centroid(points);
      const interior = face.label.startsWith('top') ? topInterior : bottomInterior;

      expect(dot(normal, subtract(center, interior))).toBeGreaterThan(0);
    }
  });

  it('uses the same projected animation for both controls and only reverses depth interpretation', () => {
    const groups = createHourglassComparison(config);

    expect(groups[0].rotationSign).toBe(groups[1].rotationSign);
    expect(groups[2].rotationSign).toBe(groups[1].rotationSign);
    expect(groups[0].perceivedDirection).toBe('clockwise');
    expect(groups[2].perceivedDirection).toBe('counterclockwise');
    expect(groups[0].depthInterpretationSign).toBe(1);
    expect(groups[2].depthInterpretationSign).toBe(-1);
  });

  it('uses an orthographic camera so depth controls do not rely on perspective', () => {
    expect(config.style.cameraProjection).toBe('orthographic');
  });

  it('uses lit convex depth cues on the side controls instead of wireframe-like glowing faces', () => {
    expect(config.style.controlSurfaceMaterial).toBe('lit-matte');
    expect(config.style.controlAmbientOcclusion).toBe(true);
    expect(config.style.controlDepthShadingStrength).toBeGreaterThanOrEqual(0.35);
    expect(config.style.controlNearEdgeStrength).toBeGreaterThan(config.style.controlFarEdgeStrength);
  });

  it('uses single-hue shaded control faces with bright caps to avoid a concave tunnel cue', () => {
    expect(config.style.controlSolidRead).toBe('convex-teaching-aid');
    expect(config.style.controlPaletteMode).toBe('single-hue-shaded');
    expect(config.style.controlFaceHueVarianceMax).toBeLessThanOrEqual(0.04);
    expect(config.style.controlCapBrightnessFloor).toBeGreaterThanOrEqual(0.66);
    expect(config.style.controlCapBaseGlow).toBeGreaterThan(config.style.controlSurfaceBaseGlow);
  });

  it('makes front depth cues dominate rear cues on the colored controls', () => {
    expect(config.style.controlFrontEdgeStrength).toBeGreaterThan(config.style.controlBackEdgeStrength * 5);
    expect(config.style.controlFrontEdgeRadius).toBeGreaterThan(config.style.controlBackEdgeRadius);
  });

  it('keeps the colored controls as clean pyramids without extra vertex marker dots', () => {
    expect(config.style.controlVertexMarkers).toBe(false);
    expect(config.style.controlThroatMarkers).toBe('none');
  });

  it('keeps both controls frame-synchronized with the center illusion for the full 22 seconds', () => {
    const plans = createSynchronizedMotionPlans(config, 'final');
    const centerPlan = plans.find((plan) => plan.groupId === 'center-wireframe-illusion');

    expect(centerPlan).toBeDefined();
    expect(plans).toHaveLength(3);
    for (const plan of plans) {
      expect(plan.durationSeconds).toBe(22);
      expect(plan.startFrame).toBe(centerPlan?.startFrame);
      expect(plan.midpointFrame).toBe(centerPlan?.midpointFrame);
      expect(plan.endFrame).toBe(centerPlan?.endFrame);
      expect(plan.loopFrame).toBe(centerPlan?.loopFrame);
      expect(plan.gapKeyframes).toEqual(centerPlan?.gapKeyframes);
      expect(plan.rotationDegrees).toBe(centerPlan?.rotationDegrees);
      expect(plan.rotationDegreesPerSecond).toBe(centerPlan?.rotationDegreesPerSecond);
      expect(plan.absoluteRotationDegrees).toBe(centerPlan?.absoluteRotationDegrees);
    }
  });
});
