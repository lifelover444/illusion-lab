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
