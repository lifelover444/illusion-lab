import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';

import {
  DEFAULT_GEOMETRY,
  canonicalEdge,
  createTetragonalTrapezohedron,
  dot,
  edgeFaceIncidence,
  faceCentroid,
  faceNormal,
  facePlanarityError,
  hasCentralInversionSymmetry,
  hasS8RotoreflectionSymmetry,
  isInsideTetragonalTrapezohedron,
  projectOrthographic,
  quadArea,
  rotationAtFrame,
  verticalDriftOffsetAtFrame,
  type Point3
} from '../src/tetragonalTrapezohedronGeometry';

const EPSILON = 1e-10;
const geometry = createTetragonalTrapezohedron(DEFAULT_GEOMETRY);
const renderConfig = JSON.parse(
  readFileSync(
    new URL('../scripts/tetragonal-trapezohedron-config.json', import.meta.url),
    'utf8'
  )
);

function pointKey(point: Point3): string {
  return [point.x, point.y, point.z]
    .map((value) => value.toFixed(12))
    .join(',');
}

function polarDegrees(point: Point3): number {
  return (Math.atan2(point.y, point.x) * 180) / Math.PI;
}

function normalizedDegrees(value: number): number {
  return ((value % 360) + 360) % 360;
}

describe('regular tetragonal trapezohedron geometry', () => {
  it('uses the approved wireframe-and-stardust render contract', () => {
    expect(renderConfig.renderMode).toBe(
      'depth-independent-contour-tetragonal-trapezohedron'
    );
    expect(renderConfig.geometry).toEqual(DEFAULT_GEOMETRY);
    expect(renderConfig.style).toMatchObject({
      cameraProjection: 'ORTHO',
      showBackEdges: true,
      continuousShell: true,
      directionalLighting: false,
      independentParticleMotion: true,
      particleMotionAxes: ['Z'],
      particleAngularMotion: false,
      faceParticleCount: 7600,
      faceParticleSizeMin: 0.0022,
      faceParticleSizeMax: 0.0045,
      faceParticleSizeExponent: 1,
      faceParticleJitter: 0.0015,
      faceParticleEdgeTrenchWidth: 0.035,
      faceParticleEdgeTrenchDensityReduction: 0.22,
      faceParticlePalette: [[0.76, 0.87, 1]],
      faceParticleStrengthMin: 1,
      faceParticleStrengthMax: 1,
      edgeFilamentSlotsPerUnit: 24,
      edgeFilamentKeepRatio: 0.82,
      edgeFilamentSlotJitter: 0.24,
      edgeFilamentPointSizeMin: 0.0025,
      edgeFilamentPointSizeMax: 0.0043,
      edgeFilamentSurfaceOffset: 0.004,
      edgeFilamentColor: [0.69, 0.76, 1],
      edgeFilamentStrength: 1.47,
      edgeHaloStride: 5,
      edgeHaloSizeMultiplier: 2.3,
      edgeHaloColor: [0.52, 0.61, 1],
      edgeHaloStrength: 1.1,
      edgeHaloOpacity: 0.28,
      edgeBreathAmount: 0.06,
      edgeBreathCycleSeconds: 6,
      rotationCycleSeconds: 12,
      cameraAzimuthDegrees: -90,
      cameraElevationDegrees: 7,
      orthographicScale: 5.25,
      glowThreshold: 1.25,
      glowSize: 3
    });
    expect(renderConfig.style.facePanel).toEqual({
      enabled: true,
      color: [0.025, 0.055, 0.13],
      alpha: 0.24,
      emissionStrength: 0.35,
      renderMethod: 'DITHERED',
      doubleSided: true,
      transparencyOverlap: true,
      castShadows: false,
      refraction: false,
      fresnel: false
    });
    expect(renderConfig.style.guideLine).toEqual({
      enabled: true,
      color: [0.45, 0.58, 0.9],
      maskEmissionStrength: 1,
      radius: 0.002,
      opaque: true,
      breathing: false,
      directionalWeighting: false,
      depthIndependent: true,
      panelOcclusion: false,
      internalOpacity: 0.1,
      outerSilhouetteOpacity: 0.2,
      intersectionAccumulation: false,
      compositeMethod: 'ALPHA_OVER_MAX_MASK'
    });
    expect(renderConfig.style.guideLine.internalOpacity).toBeLessThan(
      renderConfig.style.guideLine.outerSilhouetteOpacity
    );
    expect(1 - renderConfig.style.facePanel.alpha).toBeCloseTo(0.76, 12);
    expect(renderConfig.style.axialStarStream).toMatchObject({
      count: 64,
      motion: 'LOCKED',
      radius: 0.035
    });
    expect(renderConfig.style.galaxyDust).toMatchObject({
      count: 280,
      layerCount: 8,
      periodSeconds: 12
    });
    expect(renderConfig.style.phaseDegrees).toEqual([
      0, 22.5, 45, 67.5, 90, 135, 180, 270, 360
    ]);
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

  it('creates V=10, E=16, F=8 with Euler characteristic 2', () => {
    expect(geometry.vertices).toHaveLength(10);
    expect(geometry.edges).toHaveLength(16);
    expect(geometry.faces).toHaveLength(8);
    expect(geometry.vertices.length - geometry.edges.length + geometry.faces.length).toBe(2);
    expect(new Set(geometry.vertices.map(pointKey)).size).toBe(10);
  });

  it('uses only unique valid edges and gives every edge two incident faces', () => {
    const canonicalEdges = geometry.edges.map(canonicalEdge);
    expect(new Set(canonicalEdges).size).toBe(16);
    for (const [a, b] of geometry.edges) {
      expect(a).toBeGreaterThanOrEqual(0);
      expect(b).toBeGreaterThanOrEqual(0);
      expect(a).toBeLessThan(geometry.vertices.length);
      expect(b).toBeLessThan(geometry.vertices.length);
      expect(a).not.toBe(b);
    }
    for (const face of geometry.faces) {
      expect(new Set(face).size).toBe(4);
      for (const index of face) {
        expect(index).toBeGreaterThanOrEqual(0);
        expect(index).toBeLessThan(geometry.vertices.length);
      }
    }
    const incidence = edgeFaceIncidence(geometry.faces);
    expect(new Set(incidence.keys())).toEqual(new Set(canonicalEdges));
    expect([...incidence.values()].every((count) => count === 2)).toBe(true);
  });

  it('derives the coplanar belt half-height from H', () => {
    expect(geometry.beltHalfHeight).toBeCloseTo(
      DEFAULT_GEOMETRY.halfHeight * (3 - 2 * Math.SQRT2),
      14
    );
    expect(geometry.beltHalfHeight).toBeCloseTo(0.2951053454, 9);
  });

  it('places equal-radius rings at an exact 45-degree offset', () => {
    const upper = geometry.vertices.slice(2, 6);
    const lower = geometry.vertices.slice(6, 10);
    for (let index = 0; index < 4; index += 1) {
      expect(Math.hypot(upper[index].x, upper[index].y)).toBeCloseTo(
        DEFAULT_GEOMETRY.waistRadius,
        12
      );
      expect(Math.hypot(lower[index].x, lower[index].y)).toBeCloseTo(
        DEFAULT_GEOMETRY.waistRadius,
        12
      );
      expect(
        normalizedDegrees(polarDegrees(lower[index]) - polarDegrees(upper[index]))
      ).toBeCloseTo(45, 12);
    }
  });

  it('has planar, nonzero-area kite faces with outward winding', () => {
    const areas = geometry.faces.map((face) => quadArea(face, geometry.vertices));
    for (const face of geometry.faces) {
      expect(facePlanarityError(face, geometry.vertices)).toBeLessThan(EPSILON);
      expect(quadArea(face, geometry.vertices)).toBeGreaterThan(EPSILON);
      expect(dot(faceNormal(face, geometry.vertices), faceCentroid(face, geometry.vertices))).toBeGreaterThan(EPSILON);
    }
    for (const area of areas.slice(1)) expect(area).toBeCloseTo(areas[0], 12);
  });

  it('contains no horizontal upper or lower waist-ring edges', () => {
    const horizontalRingEdge = geometry.edges.some(([a, b]) => {
      const first = geometry.vertices[a];
      const second = geometry.vertices[b];
      const sameRing =
        (a >= 2 && a <= 5 && b >= 2 && b <= 5) ||
        (a >= 6 && a <= 9 && b >= 6 && b <= 9);
      return sameRing && Math.abs(first.z - second.z) <= EPSILON;
    });
    expect(horizontalRingEdge).toBe(false);
    expect(geometry.beltEdges).toHaveLength(8);
  });

  it('is centered and has the correct S8 rotoreflection symmetry', () => {
    const centroid = geometry.vertices.reduce(
      (sum, point) => ({
        x: sum.x + point.x / geometry.vertices.length,
        y: sum.y + point.y / geometry.vertices.length,
        z: sum.z + point.z / geometry.vertices.length
      }),
      { x: 0, y: 0, z: 0 }
    );
    expect(centroid.x).toBeCloseTo(0, 12);
    expect(centroid.y).toBeCloseTo(0, 12);
    expect(centroid.z).toBeCloseTo(0, 12);
    expect(hasS8RotoreflectionSymmetry(geometry.vertices)).toBe(true);

    // A 45-degree lower-ring twist is mathematically incompatible with v -> -v
    // for four vertices per ring; D4d/S8 rotoreflection is the actual symmetry.
    expect(hasCentralInversionSymmetry(geometry.vertices)).toBe(false);
  });

  it('keeps the origin inside and rejects exterior or padded-boundary points', () => {
    expect(isInsideTetragonalTrapezohedron({ x: 0, y: 0, z: 0 }, geometry)).toBe(true);
    expect(isInsideTetragonalTrapezohedron({ x: 2, y: 0, z: 0 }, geometry)).toBe(false);
    expect(
      isInsideTetragonalTrapezohedron(geometry.vertices[2], geometry, 0.02)
    ).toBe(false);
  });

  it('projects 0 and 360 degrees identically and stays inside the portrait camera', () => {
    const projectedZero = projectOrthographic(
      geometry.vertices,
      0,
      renderConfig.style.cameraElevationDegrees
    );
    const projectedFullTurn = projectOrthographic(
      geometry.vertices,
      360,
      renderConfig.style.cameraElevationDegrees
    );
    for (let index = 0; index < projectedZero.length; index += 1) {
      expect(projectedFullTurn[index].x).toBeCloseTo(projectedZero[index].x, 12);
      expect(projectedFullTurn[index].y).toBeCloseTo(projectedZero[index].y, 12);
    }

    const { width, height } = renderConfig.profiles.preview;
    const horizontalCapacity = renderConfig.style.orthographicScale * (width / height);
    const margin =
      renderConfig.style.edgeFilamentPointSizeMax *
      renderConfig.style.edgeHaloSizeMultiplier *
      4;
    for (let phase = 0; phase < 360; phase += 1) {
      const projected = projectOrthographic(
        geometry.vertices,
        phase,
        renderConfig.style.cameraElevationDegrees
      );
      const horizontal = projected.map((point) => point.x);
      expect(Math.max(...horizontal) - Math.min(...horizontal) + margin * 2).toBeLessThan(
        horizontalCapacity
      );
    }
  });

  it('closes on the frame after the video without repeating the tail frame', () => {
    const animation = { frameStart: 1, frameCount: 720, turns: 2 } as const;
    expect(rotationAtFrame(1, animation)).toBeCloseTo(0, 12);
    expect(rotationAtFrame(721, animation)).toBeCloseTo(0, 12);
    expect(rotationAtFrame(720, animation)).not.toBeCloseTo(0, 4);
    expect(rotationAtFrame(361, animation)).toBeCloseTo(0, 12);
    expect(() =>
      rotationAtFrame(1, { frameStart: 1, frameCount: 0, turns: 2 })
    ).toThrow(RangeError);
  });

  it('loops vertical particle drift exactly without angular motion', () => {
    const drift = {
      frameStart: 1,
      framesPerCycle: 180,
      amplitude: 0.11,
      phaseRadians: 0.37
    } as const;
    expect(verticalDriftOffsetAtFrame(1, drift)).toBe(
      verticalDriftOffsetAtFrame(181, drift)
    );
    expect(verticalDriftOffsetAtFrame(1, drift)).toBe(
      verticalDriftOffsetAtFrame(361, drift)
    );
    expect(() =>
      verticalDriftOffsetAtFrame(1, { ...drift, framesPerCycle: 0 })
    ).toThrow(RangeError);
  });
});
