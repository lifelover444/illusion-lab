import { describe, expect, it } from 'vitest';
import config from '../scripts/hourglass-config.json';
import { createHourglassGeometry } from '../src/hourglassGeometry';

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
