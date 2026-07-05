import { describe, expect, it } from 'vitest';
import config from '../scripts/saddle-config.json';
import { createSaddleGeometry } from '../src/saddleGeometry';

describe('wireframe saddle geometry', () => {
  it('creates an odd square grid of vertices and wire edges with no solid faces', () => {
    const geometry = createSaddleGeometry(config.geometry);
    const count = config.geometry.gridSize;

    expect(count % 2).toBe(1);
    expect(geometry.vertices).toHaveLength(count * count);
    expect(geometry.edges).toHaveLength(count * (count - 1) * 2);
    expect(geometry.faces).toHaveLength(0);
  });

  it('uses a hyperbolic paraboloid saddle with opposite corners sharing height signs', () => {
    const geometry = createSaddleGeometry(config.geometry);
    const count = config.geometry.gridSize;
    const topLeft = geometry.vertices[0];
    const topRight = geometry.vertices[count - 1];
    const bottomLeft = geometry.vertices[count * (count - 1)];
    const bottomRight = geometry.vertices[count * count - 1];
    const center = geometry.vertices[Math.floor(count * count / 2)];

    expect(topLeft[2]).toBeCloseTo(config.geometry.saddleHeight, 5);
    expect(bottomRight[2]).toBeCloseTo(config.geometry.saddleHeight, 5);
    expect(topRight[2]).toBeCloseTo(-config.geometry.saddleHeight, 5);
    expect(bottomLeft[2]).toBeCloseTo(-config.geometry.saddleHeight, 5);
    expect(center).toEqual([0, 0, 0]);
  });

  it('keeps the preview vertical, short, and loopable for low-resolution review', () => {
    const preview = config.profiles.preview;

    expect(preview.width / preview.height).toBeCloseTo(9 / 16, 5);
    expect(preview.fps).toBe(15);
    expect(preview.seconds).toBe(24);
    expect(preview.fps * preview.seconds).toBe(360);
    expect(config.style.rotationCycleSeconds).toBe(12);
    expect(preview.seconds / config.style.rotationCycleSeconds).toBe(2);
  });

  it('uses a particle surface with outline-only structure cues for visual detail', () => {
    expect(config.geometry.gridSize).toBeGreaterThanOrEqual(7);
    expect(config.geometry.gridSize).toBeLessThanOrEqual(11);
    expect(config.style.cameraProjection).toBe('ORTHO');
    expect(config.style.showBackEdges).toBe(true);
    expect(config.style.visualMode).toBe('particle-surface');
    expect(config.style.particleCount).toBeGreaterThanOrEqual(6000);
    expect(config.style.particleLayerCount).toBeGreaterThanOrEqual(5);
    expect(config.style.outlineSampleCount).toBeGreaterThanOrEqual(160);
    expect(config.style.ridgeCurveCount).toBe(0);
    expect(config.style.centerPulseAlpha).toBe(0);
    expect(config.style.colorMode).toBe('neutral-noise');
    expect(config.style.cameraElevationDegrees).toBeLessThanOrEqual(-6);
    expect(config.style.rockDegrees).toBe(0);
    expect(config.style.gridGuideAlpha).toBeLessThanOrEqual(0.25);
  });
});
