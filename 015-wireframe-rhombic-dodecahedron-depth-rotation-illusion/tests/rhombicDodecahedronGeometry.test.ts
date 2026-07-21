import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';

import {
  DEFAULT_GEOMETRY,
  createRhombicDodecahedron,
  dot,
  faceCentroid,
  faceNormal,
  facePlanarityError,
  isInsideRhombicDodecahedron,
  projectOrthographic,
  rhombusArea,
  rotationAtFrame,
  vectorLength,
  type Edge,
  type Point3
} from '../src/rhombicDodecahedronGeometry';

const EPSILON = 1e-10;
const geometry = createRhombicDodecahedron(DEFAULT_GEOMETRY);
const renderConfig = JSON.parse(
  readFileSync(
    new URL('../scripts/rhombic-dodecahedron-config.json', import.meta.url),
    'utf8'
  )
);
const packageConfig = JSON.parse(
  readFileSync(new URL('../package.json', import.meta.url), 'utf8')
);

function pointKey(point: Point3): string {
  return [point.x, point.y, point.z]
    .map((value) => value.toFixed(12))
    .join(',');
}

function canonicalEdge([a, b]: Edge): string {
  return a < b ? `${a},${b}` : `${b},${a}`;
}

function distance(a: Point3, b: Point3): number {
  return vectorLength({ x: b.x - a.x, y: b.y - a.y, z: b.z - a.z });
}

describe('radially compressed rhombic dodecahedron geometry', () => {
  it('keeps the approved rigid ambiguous-crystal contract across preview and HD profiles', () => {
    expect(renderConfig.renderMode).toBe(
      'depth-independent-contour-rhombic-dodecahedron-014-aligned'
    );
    expect(renderConfig.geometry).toEqual(DEFAULT_GEOMETRY);
    expect(renderConfig.style).toMatchObject({
      cameraProjection: 'ORTHO',
      showBackEdges: true,
      continuousShell: true,
      directionalLighting: false,
      depthColorGradient: false,
      independentParticleMotion: false,
      vertexAccents: false,
      interiorDustCount: 0,
      guideLine: {
        internalOpacity: 0.1,
        outerSilhouetteOpacity: 0.2,
        depthIndependent: true,
        panelOcclusion: false,
        intersectionAccumulation: false
      },
      edgeFilamentSlotsPerUnit: 24,
      edgeFilamentKeepRatio: 0.82,
      edgeBreathAmount: 0.06,
      faceParticleCount: 9300,
      faceParticleSizeMin: 0.0022,
      faceParticleSizeMax: 0.0045,
      faceParticlePalette: [[0.76, 0.87, 1]],
      faceParticleStrengthMin: 1,
      faceParticleStrengthMax: 1,
      facePanel: {
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
      },
      rotationCycleSeconds: 12,
      orthographicScale: 5.75,
      glowThreshold: 1.25,
      glowSize: 3
    });
    expect(renderConfig.profiles.preview).toMatchObject({
      width: 360,
      height: 640,
      fps: 15,
      seconds: 24,
      samples: 12
    });
    expect(renderConfig.profiles.hd).toEqual({
      width: 720,
      height: 1280,
      fps: 30,
      seconds: 24,
      samples: 24,
      output: 'output/wireframe-rhombic-dodecahedron-014-aligned-hd-720x1280.mp4'
    });
    expect(renderConfig.profiles.hd60).toEqual({
      width: 720,
      height: 1280,
      fps: 60,
      seconds: 24,
      samples: 24,
      output: 'output/wireframe-rhombic-dodecahedron-014-aligned-hd60-720x1280.mp4'
    });
    expect(Object.keys(renderConfig.profiles)).toEqual(['preview', 'hd', 'hd60']);
    expect(renderConfig.profiles.preview.output).toContain('014-aligned');
    expect(packageConfig.scripts['render:final']).toBeUndefined();
    expect(packageConfig.scripts['render:hd']).toBe('node scripts/run-blender.mjs hd');
    expect(packageConfig.scripts['render:hd60']).toBe('node scripts/run-blender.mjs hd60');
  });

  it('has V=14, E=24, F=12 and Euler characteristic 2', () => {
    expect(geometry.vertices).toHaveLength(14);
    expect(geometry.edges).toHaveLength(24);
    expect(geometry.faces).toHaveLength(12);
    expect(
      geometry.vertices.length - geometry.edges.length + geometry.faces.length
    ).toBe(2);
  });

  it('contains only unique vertices, unique edges and valid unique faces', () => {
    expect(new Set(geometry.vertices.map(pointKey)).size).toBe(14);
    expect(new Set(geometry.edges.map(canonicalEdge)).size).toBe(24);
    for (const face of geometry.faces) {
      expect(new Set(face).size).toBe(4);
      expect(face.every((index) => index >= 0 && index < 14)).toBe(true);
    }
    const canonicalFaces = geometry.faces.map((face) =>
      [...face].sort((a, b) => a - b).join(',')
    );
    expect(new Set(canonicalFaces).size).toBe(12);
  });

  it('compresses only the XY radius while keeping the Z tips unchanged', () => {
    const a = DEFAULT_GEOMETRY.latticeUnit;
    const radial = a * DEFAULT_GEOMETRY.radialWaistScale;
    geometry.vertices.slice(0, 8).forEach((point) => {
      expect(Math.abs(point.x)).toBeCloseTo(radial, 12);
      expect(Math.abs(point.y)).toBeCloseTo(radial, 12);
      expect(Math.abs(point.z)).toBeCloseTo(a, 12);
    });
    const byLabel = new Map(
      geometry.vertexLabels.map((label, index) => [label, geometry.vertices[index]])
    );
    expect(byLabel.get('X+')).toEqual({ x: 2 * radial, y: 0, z: 0 });
    expect(byLabel.get('Y+')).toEqual({ x: 0, y: 2 * radial, z: 0 });
    expect(byLabel.get('Z+')).toEqual({ x: 0, y: 0, z: 2 * a });
    expect(byLabel.get('Z-')).toEqual({ x: 0, y: 0, z: -2 * a });
  });

  it('is a closed manifold with exactly two faces incident on every edge', () => {
    const incidence = new Map<string, number>();
    for (const face of geometry.faces) {
      for (let index = 0; index < 4; index += 1) {
        const key = canonicalEdge([face[index], face[(index + 1) % 4]]);
        incidence.set(key, (incidence.get(key) ?? 0) + 1);
      }
    }
    expect(new Set(incidence.keys())).toEqual(
      new Set(geometry.edges.map(canonicalEdge))
    );
    expect([...incidence.values()].every((count) => count === 2)).toBe(true);
  });

  it('gives the eight cube corners degree 3 and six axis vertices degree 4', () => {
    const degree = new Array(14).fill(0) as number[];
    for (const [a, b] of geometry.edges) {
      degree[a] += 1;
      degree[b] += 1;
    }
    geometry.vertexKinds.forEach((kind, index) => {
      expect(degree[index]).toBe(kind === 'corner' ? 3 : 4);
    });
    expect(geometry.vertexKinds.filter((kind) => kind === 'corner')).toHaveLength(8);
    expect(geometry.vertexKinds.filter((kind) => kind === 'axis')).toHaveLength(6);
  });

  it('has twelve coplanar nonzero outward rhombi in two expected area classes', () => {
    const areas = geometry.faces.map((face) => rhombusArea(face, geometry.vertices));
    for (const [faceIndex, face] of geometry.faces.entries()) {
      expect(facePlanarityError(face, geometry.vertices)).toBeLessThan(EPSILON);
      expect(areas[faceIndex]).toBeGreaterThan(EPSILON);
      expect(
        dot(faceNormal(face, geometry.vertices), faceCentroid(face, geometry.vertices))
      ).toBeGreaterThan(EPSILON);

      const sideLengths = face.map((vertex, index) =>
        distance(
          geometry.vertices[vertex],
          geometry.vertices[face[(index + 1) % 4]]
        )
      );
      sideLengths.slice(1).forEach((length) =>
        expect(length).toBeCloseTo(sideLengths[0], 12)
      );
    }
    const a = DEFAULT_GEOMETRY.latticeUnit;
    const scale = DEFAULT_GEOMETRY.radialWaistScale;
    const expectedXyArea = 2 * Math.SQRT2 * a ** 2 * scale;
    const expectedSlopedArea = 2 * a ** 2 * scale * Math.sqrt(1 + scale ** 2);
    areas.slice(0, 4).forEach((area) =>
      expect(area).toBeCloseTo(expectedXyArea, 12)
    );
    areas.slice(4).forEach((area) =>
      expect(area).toBeCloseTo(expectedSlopedArea, 12)
    );
    expect(areas[0]).not.toBeCloseTo(areas[4], 8);
  });

  it('keeps all 24 structural edges equal after radial compression', () => {
    const expected =
      DEFAULT_GEOMETRY.latticeUnit *
      Math.sqrt(1 + 2 * DEFAULT_GEOMETRY.radialWaistScale ** 2);
    for (const [a, b] of geometry.edges) {
      expect(distance(geometry.vertices[a], geometry.vertices[b])).toBeCloseTo(
        expected,
        12
      );
    }
  });

  it('preserves every vertex and edge under central inversion', () => {
    const indexByPoint = new Map(
      geometry.vertices.map((point, index) => [pointKey(point), index])
    );
    const edgeSet = new Set(geometry.edges.map(canonicalEdge));
    for (const [index, point] of geometry.vertices.entries()) {
      const opposite = indexByPoint.get(
        pointKey({ x: -point.x, y: -point.y, z: -point.z })
      );
      expect(opposite, `missing inverse of vertex ${index}`).toBeDefined();
    }
    for (const [a, b] of geometry.edges) {
      const inverseA = indexByPoint.get(
        pointKey({
          x: -geometry.vertices[a].x,
          y: -geometry.vertices[a].y,
          z: -geometry.vertices[a].z
        })
      );
      const inverseB = indexByPoint.get(
        pointKey({
          x: -geometry.vertices[b].x,
          y: -geometry.vertices[b].y,
          z: -geometry.vertices[b].z
        })
      );
      expect(edgeSet.has(canonicalEdge([inverseA!, inverseB!]))).toBe(true);
    }
  });

  it('accepts the center and boundary vertices but rejects outside points', () => {
    expect(isInsideRhombicDodecahedron({ x: 0, y: 0, z: 0 })).toBe(true);
    for (const vertex of geometry.vertices) {
      expect(isInsideRhombicDodecahedron(vertex)).toBe(true);
    }
    expect(
      isInsideRhombicDodecahedron({
        x:
          2.01 *
          DEFAULT_GEOMETRY.latticeUnit *
          DEFAULT_GEOMETRY.radialWaistScale,
        y: 0.02,
        z: 0
      })
    ).toBe(false);
    expect(
      isInsideRhombicDodecahedron({
        x: DEFAULT_GEOMETRY.latticeUnit * 1.1,
        y: DEFAULT_GEOMETRY.latticeUnit * 1.1,
        z: DEFAULT_GEOMETRY.latticeUnit * 1.1
      })
    ).toBe(false);
  });

  it('projects identically at 0 and 360 degrees and remains inside the portrait frame', () => {
    const zero = projectOrthographic(
      geometry.vertices,
      0,
      renderConfig.style.cameraElevationDegrees,
      renderConfig.style.cameraAzimuthDegrees
    );
    const fullTurn = projectOrthographic(
      geometry.vertices,
      360,
      renderConfig.style.cameraElevationDegrees,
      renderConfig.style.cameraAzimuthDegrees
    );
    zero.forEach((point, index) => {
      expect(fullTurn[index].x).toBeCloseTo(point.x, 12);
      expect(fullTurn[index].y).toBeCloseTo(point.y, 12);
    });

    const { width, height } = renderConfig.profiles.preview;
    const horizontalCapacity = renderConfig.style.orthographicScale * (width / height);
    const margin =
      renderConfig.style.edgeFilamentPointSizeMax *
      renderConfig.style.edgeHaloSizeMultiplier *
      2;
    let maximumProjectedHeight = 0;
    for (let phase = 0; phase < 360; phase += 1) {
      const projected = projectOrthographic(
        geometry.vertices,
        phase,
        renderConfig.style.cameraElevationDegrees,
        renderConfig.style.cameraAzimuthDegrees
      );
      const xs = projected.map((point) => point.x);
      const ys = projected.map((point) => point.y);
      maximumProjectedHeight = Math.max(
        maximumProjectedHeight,
        Math.max(...ys) - Math.min(...ys)
      );
      expect(Math.max(...xs) - Math.min(...xs) + margin * 2).toBeLessThan(
        horizontalCapacity
      );
      expect(Math.max(...ys) - Math.min(...ys) + margin * 2).toBeLessThan(
        renderConfig.style.orthographicScale
      );
    }
    expect(maximumProjectedHeight / renderConfig.style.orthographicScale).toBeGreaterThan(
      0.59
    );
    expect(maximumProjectedHeight / renderConfig.style.orthographicScale).toBeLessThan(
      0.61
    );
  });

  it('closes two turns on the conceptual frame after the low-resolution video', () => {
    const animation = {
      frameStart: 1,
      frameCount: 360,
      turns: 2,
      initialPhaseDegrees: DEFAULT_GEOMETRY.initialPhaseDegrees
    } as const;
    const first = rotationAtFrame(1, animation);
    expect(first).toBeCloseTo((22.5 * Math.PI) / 180, 12);
    expect(rotationAtFrame(181, animation)).toBeCloseTo(first, 12);
    expect(rotationAtFrame(361, animation)).toBeCloseTo(first, 12);
    expect(rotationAtFrame(360, animation)).not.toBeCloseTo(first, 8);
  });

  it('rejects invalid animation frame counts', () => {
    expect(() =>
      rotationAtFrame(1, {
        frameStart: 1,
        frameCount: 0,
        turns: 2,
        initialPhaseDegrees: 22.5
      })
    ).toThrow(RangeError);
  });

  it('rejects invalid radial waist scales', () => {
    expect(() =>
      createRhombicDodecahedron({
        latticeUnit: 0.86,
        radialWaistScale: 0,
        initialPhaseDegrees: 22.5
      })
    ).toThrow(RangeError);
    expect(() =>
      createRhombicDodecahedron({
        latticeUnit: 0.86,
        radialWaistScale: 1.01,
        initialPhaseDegrees: 22.5
      })
    ).toThrow(RangeError);
  });

  it('contains no face diagonals, center spokes or structural extras', () => {
    const edgeSet = new Set(geometry.edges.map(canonicalEdge));
    for (const face of geometry.faces) {
      expect(edgeSet.has(canonicalEdge([face[0], face[2]]))).toBe(false);
      expect(edgeSet.has(canonicalEdge([face[1], face[3]]))).toBe(false);
    }
    expect(geometry.vertices.some((point) => pointKey(point) === pointKey({ x: 0, y: 0, z: 0 }))).toBe(false);
    expect(geometry.edges).toHaveLength(
      geometry.vertexKinds.filter((kind) => kind === 'corner').length * 3
    );
  });
});
