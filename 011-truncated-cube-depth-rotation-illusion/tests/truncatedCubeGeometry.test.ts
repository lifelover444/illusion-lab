import { describe, expect, it } from 'vitest';

import {
  cornerTriangleVertices,
  cutPlaneValue,
  isOnLargeFace,
  largeFacePoint,
  pointOnTriangle,
  type Sign,
  type TruncatedCubeGeometry
} from '../src/truncatedCubeGeometry';

const geometry: TruncatedCubeGeometry = {
  edgeLength: 2,
  cutDepth: 0.28
};

describe('truncated cube geometry', () => {
  it('uses the intended fourteen-percent vertex cut', () => {
    expect(geometry.cutDepth / geometry.edgeLength).toBeCloseTo(0.14);
  });

  it('creates eight equal triangular cut faces on one cut plane each', () => {
    const signs: Sign[] = [-1, 1];
    let faceCount = 0;
    for (const sx of signs) {
      for (const sy of signs) {
        for (const sz of signs) {
          const vertices = cornerTriangleVertices(sx, sy, sz, geometry);
          const values = vertices.map((point) => cutPlaneValue(point, sx, sy, sz));
          expect(values[1]).toBeCloseTo(values[0]);
          expect(values[2]).toBeCloseTo(values[0]);
          faceCount += 1;
        }
      }
    }
    expect(faceCount).toBe(8);
  });

  it('clips all four corners from every large square face', () => {
    const half = geometry.edgeLength / 2;
    expect(isOnLargeFace(0, 0, geometry)).toBe(true);
    expect(isOnLargeFace(half, half, geometry)).toBe(false);
    expect(isOnLargeFace(half - geometry.cutDepth, half, geometry)).toBe(true);
  });

  it('maps each large face to the selected cube plane', () => {
    expect(largeFacePoint('x', 1, 0.2, -0.3, geometry).x).toBeCloseTo(1);
    expect(largeFacePoint('y', -1, 0.2, -0.3, geometry).y).toBeCloseTo(-1);
    expect(largeFacePoint('z', 1, 0.2, -0.3, geometry).z).toBeCloseTo(1);
  });

  it('samples points inside a corner triangle', () => {
    const vertices = cornerTriangleVertices(1, 1, 1, geometry);
    const point = pointOnTriangle(vertices, 0.25, 0.5);
    expect(cutPlaneValue(point, 1, 1, 1)).toBeCloseTo(3 - geometry.cutDepth);
  });
});
