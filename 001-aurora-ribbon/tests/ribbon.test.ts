import { describe, expect, it } from 'vitest';
import { createRibbonSurface } from '../src/ribbon';

describe('createRibbonSurface', () => {
  it('creates a closed multi-strand surface with stable vertex and index counts', () => {
    const surface = createRibbonSurface({
      radialSegments: 96,
      strands: 4,
      widthSegments: 5,
      radius: 2.1,
      ribbonWidth: 0.42,
      twist: 1.35,
      verticalDrift: 0.58
    });

    expect(surface.positions.length).toBe(96 * 4 * 5 * 3);
    expect(surface.indices.length).toBe(96 * 4 * (5 - 1) * 6);
    expect(surface.strandAnchors).toHaveLength(4);
  });

  it('keeps every vertex inside the orthographic composition bounds', () => {
    const surface = createRibbonSurface({
      radialSegments: 128,
      strands: 5,
      widthSegments: 7,
      radius: 2.0,
      ribbonWidth: 0.5,
      twist: 1.1,
      verticalDrift: 0.65
    });

    const values = Array.from(surface.positions);
    const xs = values.filter((_, index) => index % 3 === 0);
    const ys = values.filter((_, index) => index % 3 === 1);
    const zs = values.filter((_, index) => index % 3 === 2);

    expect(Math.max(...xs.map(Math.abs))).toBeLessThan(3);
    expect(Math.max(...ys.map(Math.abs))).toBeLessThan(1.8);
    expect(Math.max(...zs.map(Math.abs))).toBeLessThan(3);
  });
});
