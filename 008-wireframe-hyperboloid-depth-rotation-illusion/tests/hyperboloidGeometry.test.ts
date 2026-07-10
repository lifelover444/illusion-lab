import { describe, expect, it } from 'vitest';
import config from '../scripts/hyperboloid-config.json';
import { createHyperboloidGeometry } from '../src/hyperboloidGeometry';

const radialLength = ([x, y]: [number, number, number]): number => Math.hypot(x, y);

describe('wireframe hyperboloid depth rotation geometry', () => {
  it('creates a single ruled hyperboloid cage with no solid faces', () => {
    const geometry = createHyperboloidGeometry(config.geometry);
    const levelCount = config.geometry.latitudeRingRatios.length + 2;
    const expectedRingEdges = levelCount * config.geometry.ribCount;
    const expectedRibEdges = (levelCount - 1) * config.geometry.ribCount;

    expect(config.geometry.ribCount).toBeGreaterThanOrEqual(12);
    expect(config.geometry.ribCount).toBeLessThanOrEqual(16);
    expect(config.geometry.latitudeRingRatios).toEqual([0.5]);
    expect(geometry.vertices).toHaveLength(levelCount * config.geometry.ribCount);
    expect(geometry.edges).toHaveLength(expectedRingEdges + expectedRibEdges);
    expect(geometry.faces).toHaveLength(0);
  });

  it('keeps top and bottom rings equal while twisting the top ring out of phase', () => {
    const geometry = createHyperboloidGeometry(config.geometry);
    const bottomFirst = geometry.vertices[0];
    const topFirst = geometry.vertices[geometry.vertices.length - config.geometry.ribCount];
    const twistRadians = config.geometry.twistDegrees * Math.PI / 180;

    expect(bottomFirst[0]).toBeCloseTo(config.geometry.ringRadius, 5);
    expect(bottomFirst[1]).toBeCloseTo(0, 5);
    expect(bottomFirst[2]).toBeCloseTo(-config.geometry.height / 2, 5);
    expect(radialLength(bottomFirst)).toBeCloseTo(config.geometry.ringRadius, 5);
    expect(radialLength(topFirst)).toBeCloseTo(config.geometry.ringRadius, 5);
    expect(topFirst[0]).toBeCloseTo(config.geometry.ringRadius * Math.cos(twistRadians), 5);
    expect(topFirst[1]).toBeCloseTo(config.geometry.ringRadius * Math.sin(twistRadians), 5);
    expect(topFirst[2]).toBeCloseTo(config.geometry.height / 2, 5);
  });

  it('narrows at the waist so the silhouette is not a plain cylinder', () => {
    const geometry = createHyperboloidGeometry(config.geometry);
    const waistLevelIndex = geometry.levelRatios.indexOf(0.5);
    const waistFirst = geometry.vertices[waistLevelIndex * config.geometry.ribCount];
    const waistRadius = radialLength(waistFirst);

    expect(waistLevelIndex).toBeGreaterThan(0);
    expect(waistRadius).toBeLessThan(config.geometry.ringRadius * 0.82);
    expect(waistRadius).toBeGreaterThan(config.geometry.ringRadius * 0.45);
  });

  it('keeps the preview vertical, loopable, and two full rotation cycles long', () => {
    const preview = config.profiles.preview;

    expect(preview.width / preview.height).toBeCloseTo(9 / 16, 5);
    expect(preview.fps).toBe(15);
    expect(preview.seconds).toBe(24);
    expect(config.style.rotationCycleSeconds).toBe(12);
    expect(preview.seconds / config.style.rotationCycleSeconds).toBe(2);
  });

  it('uses the saddle-like particle texture without adding depth-order cues', () => {
    expect(config.style.visualMode).toBe('particle-hyperboloid-cage');
    expect(config.style.colorMode).toBe('neutral-noise');
    expect(config.style.cameraProjection).toBe('ORTHO');
    expect(config.style.showBackEdges).toBe(true);
    expect(config.style.particleCount).toBeGreaterThanOrEqual(8000);
    expect(config.style.particleCount).toBeLessThanOrEqual(10000);
    expect(config.style.continuousSideRibs).toBe(false);
    expect(config.style.guideRibFamilies).toEqual(['positive', 'negative']);
    expect(config.style.guideRibCount).toBeLessThanOrEqual(5);
    expect(config.style.ringStyle).toBe('soft-pink-particle-rim');
    expect(config.style.ringCoreRadius).toBeLessThanOrEqual(0.0016);
    expect(config.style.ringParticleCount).toBeGreaterThanOrEqual(240);
    expect(config.style.waistRingVisible).toBe(false);
    expect(config.style.waistRingScale).toBeLessThanOrEqual(0.65);
    expect(config.style.heartPattern).toBe(false);
    expect(config.style.rockDegrees).toBe(0);
    expect(config.style.cameraElevationDegrees).toBeLessThanOrEqual(-5);
  });
});
