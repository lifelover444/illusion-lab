import { describe, expect, it } from 'vitest';
import { ANGULAR_SPEED, LOOP_DURATION, createFibonacciSphere } from '../src/sphere';

describe('createFibonacciSphere', () => {
  it('creates exactly 96 deterministic points', () => {
    const first = createFibonacciSphere();
    const second = createFibonacciSphere();

    expect(first).toHaveLength(96);
    expect(second).toEqual(first);
  });

  it('places every point on the unit sphere', () => {
    const points = createFibonacciSphere();

    for (const point of points) {
      const length = Math.hypot(point.x, point.y, point.z);
      expect(length).toBeCloseTo(1, 10);
    }
  });

  it('keeps a stable distribution without random drift', () => {
    const points = createFibonacciSphere();

    expect(points[0]).toEqual({
      x: 0.14396119751130454,
      y: 0.9895833333333334,
      z: 0
    });
    expect(points[47]).toEqual({
      x: 0.9555609097627037,
      y: 0.01041666666666663,
      z: -0.2946096413714757
    });
    expect(points[95]).toEqual({
      x: -0.03296559788430417,
      y: -0.9895833333333333,
      z: 0.140135990184604
    });
  });

  it('covers the vertical extent close to [-1, 1]', () => {
    const yValues = createFibonacciSphere().map((point) => point.y);

    expect(Math.max(...yValues)).toBeGreaterThan(0.98);
    expect(Math.min(...yValues)).toBeLessThan(-0.98);
  });
});

describe('loop constants', () => {
  it('complete one exact rotation over the 16 second loop', () => {
    expect(ANGULAR_SPEED * LOOP_DURATION).toBeCloseTo(Math.PI * 2, 12);
  });

  it('use a steady ambiguous-rotation speed', () => {
    expect(ANGULAR_SPEED).toBeGreaterThanOrEqual(0.3);
    expect(ANGULAR_SPEED).toBeLessThanOrEqual(0.5);
  });
});
