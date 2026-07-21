import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';

import {
  DEFAULT_GEOMETRY,
  createSquareBipyramid,
  dustDriftAtFrame,
  faceNormal,
  isInsideSquareBipyramid,
  projectOrthographic,
  rotationAtFrame,
  triangleArea,
  type Point3
} from '../src/squareBipyramidGeometry';

const EPSILON = 1e-10;
const geometry = createSquareBipyramid(DEFAULT_GEOMETRY);
const renderConfig = JSON.parse(
  readFileSync(
    new URL('../scripts/square-bipyramid-config.json', import.meta.url),
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

describe('square bipyramid geometry', () => {
  it('uses the approved ambiguous crystal-and-stardust render contract', () => {
    expect(renderConfig.renderMode).toBe('ambiguous-crystal-stardust');
    expect(renderConfig.geometry).toMatchObject(DEFAULT_GEOMETRY);
    expect(renderConfig.style).toMatchObject({
      cameraProjection: 'ORTHO',
      showBackEdges: true,
      faceAlpha: 0.12,
      particleCount: 3200,
      rotationCycleSeconds: 12,
      edgeCoreStrength: 3.9,
      edgeGlowStrength: 0.5,
      edgeGlowRadius: 0.0068
    });
    expect(renderConfig.style.interiorDust).toMatchObject({
      count: 1500,
      boundaryPadding: 0.08,
      layers: [
        { name: 'ambient', count: 1050 },
        { name: 'chromatic', count: 375 },
        { name: 'glints', count: 75 }
      ]
    });
    expect(
      renderConfig.style.interiorDust.layers.reduce(
        (sum: number, layer: { count: number }) => sum + layer.count,
        0
      )
    ).toBe(renderConfig.style.interiorDust.count);
    expect(renderConfig.style.edgePalette).toHaveLength(5);
    expect(renderConfig.style.particlePalette).toHaveLength(6);
    expect(renderConfig.profiles.preview).toMatchObject({
      width: 360,
      height: 640,
      fps: 15,
      seconds: 24
    });
    expect(renderConfig.profiles.final).toMatchObject({
      width: 720,
      height: 1280,
      fps: 30,
      seconds: 24
    });
  });

  it('creates six unique vertices and eight unique triangular faces', () => {
    expect(geometry.vertices).toHaveLength(6);
    expect(new Set(geometry.vertices.map(pointKey)).size).toBe(6);

    const canonicalFaces = geometry.faces.map((face) =>
      [...face].sort((a, b) => a - b).join(',')
    );
    expect(geometry.faces).toHaveLength(8);
    expect(new Set(canonicalFaces).size).toBe(8);
  });

  it('places symmetric poles on the vertical axis', () => {
    const [top, bottom] = geometry.vertices;
    expect(top).toEqual({ x: 0, y: 0, z: DEFAULT_GEOMETRY.halfHeight });
    expect(bottom).toEqual({ x: 0, y: 0, z: -DEFAULT_GEOMETRY.halfHeight });
  });

  it('places four waist vertices on z = 0 as a square', () => {
    const waist = geometry.vertices.slice(2);
    expect(waist.every((point) => point.z === 0)).toBe(true);
    for (const point of waist) {
      expect(Math.hypot(point.x, point.y)).toBeCloseTo(DEFAULT_GEOMETRY.waistRadius, 12);
    }
    for (let index = 0; index < waist.length; index += 1) {
      const current = waist[index];
      const next = waist[(index + 1) % waist.length];
      const side = Math.hypot(next.x - current.x, next.y - current.y);
      expect(side).toBeCloseTo(DEFAULT_GEOMETRY.waistRadius * Math.SQRT2, 12);
    }
  });

  it('gives all eight exposed triangles equal area and outward normals', () => {
    const areas = geometry.faces.map(([a, b, c]) =>
      triangleArea(geometry.vertices[a], geometry.vertices[b], geometry.vertices[c])
    );
    for (const area of areas.slice(1)) expect(area).toBeCloseTo(areas[0], 12);

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

  it('defines twelve structural edges including the bright square waist', () => {
    expect(geometry.edges).toHaveLength(12);
    expect(geometry.waistEdges).toEqual([
      [2, 3],
      [3, 4],
      [4, 5],
      [5, 2]
    ]);
  });

  it('keeps opposite waist vertices mirrored in orthographic projection', () => {
    const projected = projectOrthographic(geometry.vertices, 37, 8);
    expect(projected[2].x).toBeCloseTo(-projected[4].x, 12);
    expect(projected[2].y).toBeCloseTo(-projected[4].y, 12);
    expect(projected[3].x).toBeCloseTo(-projected[5].x, 12);
    expect(projected[3].y).toBeCloseTo(-projected[5].y, 12);
  });

  it('keeps every rotation phase inside the portrait camera with glow margin', () => {
    const { width, height } = renderConfig.profiles.preview;
    const horizontalCapacity =
      renderConfig.style.orthographicScale * (width / height);
    const glowMargin = renderConfig.style.edgeGlowRadius * 4;

    for (let phase = 0; phase < 360; phase += 1) {
      const projected = projectOrthographic(
        geometry.vertices,
        phase,
        renderConfig.style.cameraElevationDegrees
      );
      const horizontal = projected.map((point) => point.x);
      const projectedWidth = Math.max(...horizontal) - Math.min(...horizontal);
      expect(projectedWidth + glowMargin * 2).toBeLessThan(horizontalCapacity);
    }
  });

  it('closes exactly after two turns of a 24-second render', () => {
    const animation = { frameStart: 1, frameEnd: 720, turns: 2 } as const;
    expect(rotationAtFrame(animation.frameStart, animation)).toBeCloseTo(0, 12);
    expect(rotationAtFrame(animation.frameEnd, animation)).toBeCloseTo(0, 12);
    expect(
      rotationAtFrame((animation.frameStart + animation.frameEnd) / 2, animation)
    ).toBeCloseTo(0, 12);
  });

  it('rejects invalid frame ranges', () => {
    expect(() =>
      rotationAtFrame(1, { frameStart: 5, frameEnd: 4, turns: 1 })
    ).toThrow(RangeError);
  });

  it('classifies padded interior dust positions inside the square bipyramid', () => {
    expect(
      isInsideSquareBipyramid({ x: 0, y: 0, z: 0 }, DEFAULT_GEOMETRY, 0.08)
    ).toBe(true);
    expect(
      isInsideSquareBipyramid({ x: 0.8, y: 0.8, z: 0 }, DEFAULT_GEOMETRY, 0.08)
    ).toBe(true);
    expect(
      isInsideSquareBipyramid({ x: 1, y: 1, z: 0 }, DEFAULT_GEOMETRY, 0.08)
    ).toBe(false);
    expect(
      isInsideSquareBipyramid(
        { x: 0.2, y: 0.2, z: DEFAULT_GEOMETRY.halfHeight * 0.9 },
        DEFAULT_GEOMETRY,
        0.08
      )
    ).toBe(false);
  });

  it('loops each interior dust drift layer after one 12-second cycle', () => {
    const drift = {
      frameStart: 1,
      frameEnd: 720,
      turns: 2,
      angularAmplitudeDegrees: 0.7,
      verticalAmplitude: 0.016,
      phaseDegrees: 0
    } as const;
    expect(dustDriftAtFrame(1, drift)).toEqual(dustDriftAtFrame(720, drift));
    expect(dustDriftAtFrame(1 + 719 / 8, drift).rotationRadians).toBeCloseTo(
      (0.7 * Math.PI) / 180,
      12
    );
    expect(dustDriftAtFrame(1 + 719 / 8, drift).verticalOffset).toBeCloseTo(
      0.016,
      12
    );
    expect(dustDriftAtFrame(1 + (3 * 719) / 8, drift).rotationRadians).toBeCloseTo(
      (-0.7 * Math.PI) / 180,
      12
    );
  });
});
