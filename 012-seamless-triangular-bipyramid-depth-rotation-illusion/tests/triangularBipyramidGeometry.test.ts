import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';

import {
  DEFAULT_GEOMETRY,
  createTriangularBipyramid,
  faceNormal,
  projectedWidth,
  rotationAtFrame,
  triangleArea,
  type Point3
} from '../src/triangularBipyramidGeometry';

const geometry = createTriangularBipyramid(DEFAULT_GEOMETRY);
const EPSILON = 1e-10;
const renderConfig = JSON.parse(
  readFileSync(
    new URL('../scripts/triangular-bipyramid-config.json', import.meta.url),
    'utf8'
  )
);

function pointKey(point: Point3): string {
  return [point.x, point.y, point.z]
    .map((value) => value.toFixed(12))
    .join(',');
}

function dot(a: Point3, b: Point3): number {
  return a.x * b.x + a.y * b.y + a.z * b.z;
}

describe('triangular bipyramid geometry', () => {
  it('uses the approved dichroic glass render contract', () => {
    expect(renderConfig.renderMode).toBe('dichroic-glass');
    expect(renderConfig.geometry).not.toHaveProperty('pointsPerFace');
    expect(renderConfig.material).toMatchObject({
      ior: 1.47,
      roughness: 0.28,
      transmissionWeight: 0.62,
      alpha: 0.78,
      volumeDensity: 0.025,
      surfaceRenderMethod: 'BLENDED',
      colorFieldMode: 'object-aurora',
      thinFilmThickness: 320,
      thinFilmIor: 1.33
    });
    expect(renderConfig.material.facingColors).toHaveLength(4);
    expect(renderConfig.lighting.pairCount).toBe(3);
    expect(renderConfig.lighting.shape).toBe('RECTANGLE');
    expect(renderConfig.lighting.sizeY).toBe(0.5);
  });

  it('creates exactly five unique vertices', () => {
    expect(geometry.vertices).toHaveLength(5);
    expect(new Set(geometry.vertices.map(pointKey)).size).toBe(5);
  });

  it('creates exactly six unique triangular faces', () => {
    const canonicalFaces = geometry.faces.map((face) =>
      [...face].sort((a, b) => a - b).join(',')
    );
    expect(geometry.faces).toHaveLength(6);
    expect(new Set(canonicalFaces).size).toBe(6);
  });

  it('places the poles symmetrically around z = 0', () => {
    const [top, bottom] = geometry.vertices;
    expect(top).toEqual({ x: 0, y: 0, z: Math.SQRT2 });
    expect(bottom).toEqual({ x: 0, y: 0, z: -Math.SQRT2 });
  });

  it('places all three middle vertices on z = 0', () => {
    expect(geometry.vertices.slice(2).every((point) => point.z === 0)).toBe(true);
  });

  it('spaces the middle vertices by 120 degrees', () => {
    const angles = geometry.vertices
      .slice(2)
      .map((point) => Math.atan2(point.y, point.x))
      .map((angle) => (angle + Math.PI * 2) % (Math.PI * 2))
      .sort((a, b) => a - b);
    const gaps = [
      angles[1] - angles[0],
      angles[2] - angles[1],
      angles[0] + Math.PI * 2 - angles[2]
    ];
    for (const gap of gaps) expect(gap).toBeCloseTo((2 * Math.PI) / 3, 12);
  });

  it('gives all six exposed triangles equal area', () => {
    const areas = geometry.faces.map(([a, b, c]) =>
      triangleArea(geometry.vertices[a], geometry.vertices[b], geometry.vertices[c])
    );
    for (const area of areas.slice(1)) expect(area).toBeCloseTo(areas[0], 12);
  });

  it('orients every triangle normal away from the origin', () => {
    for (const face of geometry.faces) {
      const normal = faceNormal(face, geometry.vertices);
      const centroid = face.reduce(
        (sum, index) => ({
          x: sum.x + geometry.vertices[index].x / 3,
          y: sum.y + geometry.vertices[index].y / 3,
          z: sum.z + geometry.vertices[index].z / 3
        }),
        { x: 0, y: 0, z: 0 }
      );
      expect(dot(normal, centroid)).toBeGreaterThan(EPSILON);
    }
  });

  it('defines no dedicated common-edge or middle-belt geometry', () => {
    expect(geometry.dedicatedEdges).toEqual([]);
  });

  it('matches the start angle at the frame after the rendered loop', () => {
    const animation = { frameStart: 1, frameEnd: 162, turns: 2 } as const;
    expect(rotationAtFrame(animation.frameStart, animation)).toBeCloseTo(0, 12);
    expect(rotationAtFrame(animation.frameEnd + 1, animation)).toBeCloseTo(0, 12);
  });

  it('preserves a safe projected width at all nine inspection phases', () => {
    const phases = [0, 30, 60, 90, 120, 180, 240, 300, 360];
    for (const phase of phases) {
      expect(projectedWidth(geometry.vertices, phase)).toBeGreaterThan(1.45);
    }
  });

});
