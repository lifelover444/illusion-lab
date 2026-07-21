import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';

import {
  DEFAULT_GEOMETRY,
  DISPLAY_BASIS,
  createStellaOctangula,
  cross,
  distance,
  dot,
  faceCentroid,
  faceNormal,
  projectOrthographic,
  rotationAtFrame,
  transformToDisplayBasis,
  triangleArea,
  vectorLength,
  type Edge,
  type Point3
} from '../src/stellaOctangulaGeometry';

const EPSILON = 1e-10;
const geometry = createStellaOctangula(DEFAULT_GEOMETRY);
const renderConfig = JSON.parse(
  readFileSync(
    new URL('../scripts/stella-octangula-config.json', import.meta.url),
    'utf8'
  )
);
const packageConfig = JSON.parse(
  readFileSync(new URL('../package.json', import.meta.url), 'utf8')
);

function pointKey(point: Point3): string {
  return [point.x, point.y, point.z]
    .map((value) => (Math.abs(value) < 1e-11 ? 0 : value).toFixed(10))
    .join(',');
}

function canonicalEdge([a, b]: Edge): string {
  return a < b ? `${a},${b}` : `${b},${a}`;
}

function rotateZ(point: Point3, degrees: number): Point3 {
  const angle = (degrees * Math.PI) / 180;
  const cosine = Math.cos(angle);
  const sine = Math.sin(angle);
  return {
    x: point.x * cosine - point.y * sine,
    y: point.x * sine + point.y * cosine,
    z: point.z
  };
}

describe('stella octangula compound geometry', () => {
  it('enforces a low-resolution-only equal-material render contract', () => {
    expect(renderConfig.renderMode).toBe(
      'particle-surface-object-space-spectral-gradient-stella-octangula'
    );
    expect(renderConfig.geometry).toEqual(DEFAULT_GEOMETRY);
    expect(renderConfig.style).toMatchObject({
      cameraProjection: 'ORTHO',
      showBackEdges: true,
      sameMaterialForBothTetrahedra: true,
      continuousIntersectionEdges: true,
      overUnderCues: false,
      largeFacePanels: false,
      edgeCurves: false,
      particleSurface: true,
      solidNonconvexShell: false,
      directionalLighting: false,
      depthColorGradient: false,
      independentParticleMotion: false,
      vertexAccents: false,
      intersectionAccents: false,
      interiorDustCount: 0,
      edgeParticleCount: 960,
      edgeParticleSlotsPerEdge: 96,
      edgeParticleStrength: 1.05,
      edgeHaloStride: 5,
      edgeHaloInheritsParticleColor: true,
      edgeHaloOpacity: 0.16,
      spectralGradient: {
        mode: 'OBJECT_SPACE_LINEAR_CYCLIC',
        direction: [0.61, -0.37, 0.7],
        cyclesAcrossObject: 1.35,
        phase: 0.06,
        bandCount: 24,
        sameFieldForAllParticles: true,
        cameraDriven: false,
        depthDriven: false,
        animated: false
      },
      faceParticleCount: 6400,
      faceParticleLayers: {
        baseDust: {
          count: 4160,
          colorMode: 'OBJECT_SPACE_SPECTRAL',
          gradientStyle: 'baseDust',
          strength: 0.38
        },
        colorGrains: {
          count: 2240,
          colorMode: 'OBJECT_SPACE_SPECTRAL',
          gradientStyle: 'colorGrains',
          strength: 0.72
        }
      },
      cameraElevationDegrees: 7,
      orthographicScale: 5.87,
      rotationCycleSeconds: 12
    });
    expect(renderConfig.profiles).toEqual({
      preview: {
        width: 360,
        height: 640,
        fps: 15,
        seconds: 24,
        samples: 10,
        output: 'output/wireframe-stella-octangula-preview.mp4'
      }
    });
    expect(renderConfig.style.edgeParticleCount % geometry.edges.length).toBe(0);
    expect(renderConfig.style.edgeParticleCount / geometry.edges.length).toBeLessThan(
      renderConfig.style.edgeParticleSlotsPerEdge
    );
    const gradient = renderConfig.style.spectralGradient;
    expect(vectorLength({
      x: gradient.direction[0],
      y: gradient.direction[1],
      z: gradient.direction[2]
    })).toBeGreaterThan(0);
    expect(gradient.bandCount).toBeGreaterThanOrEqual(18);
    expect(gradient.cyclesAcrossObject).toBeGreaterThan(0);
    expect(Object.keys(gradient.styles).sort()).toEqual(
      ['edge', 'halo', 'baseDust', 'colorGrains'].sort()
    );
    Object.values(gradient.styles).forEach((style) => {
      const typedStyle = style as { saturation: number; value: number; whiteMix: number };
      expect(typedStyle.saturation).toBeGreaterThan(0);
      expect(typedStyle.saturation).toBeLessThanOrEqual(1);
      expect(typedStyle.value).toBeGreaterThan(0);
      expect(typedStyle.value).toBeLessThanOrEqual(1);
      expect(typedStyle.whiteMix).toBeGreaterThanOrEqual(0);
      expect(typedStyle.whiteMix).toBeLessThan(0.2);
    });
    expect(
      Object.values(renderConfig.style.faceParticleLayers).reduce(
        (sum: number, layer) => sum + (layer as { count: number }).count,
        0
      )
    ).toBe(renderConfig.style.faceParticleCount);
    Object.values(renderConfig.style.faceParticleLayers).forEach((layer) => {
      const typedLayer = layer as {
        count: number;
        colorMode: string;
        gradientStyle: string;
      };
      const particlesPerFace = typedLayer.count / geometry.faces.length;
      expect(Number.isInteger(particlesPerFace)).toBe(true);
      expect(typedLayer.colorMode).toBe('OBJECT_SPACE_SPECTRAL');
      expect(gradient.styles).toHaveProperty(typedLayer.gradientStyle);
    });
    expect(Object.keys(packageConfig.scripts).sort()).toEqual(
      ['build', 'render:preview', 'render:stills', 'scene', 'test'].sort()
    );
    expect(Object.keys(packageConfig.scripts).some((name) => /final|hd/i.test(name))).toBe(
      false
    );
  });

  it('creates eight unique external vertices split by sign product', () => {
    expect(geometry.vertices).toHaveLength(8);
    expect(new Set(geometry.vertices.map(pointKey)).size).toBe(8);
    expect(geometry.tetraA).toHaveLength(4);
    expect(geometry.tetraB).toHaveLength(4);
    expect(new Set([...geometry.tetraA, ...geometry.tetraB]).size).toBe(8);
    geometry.tetraA.forEach((index) => {
      const point = geometry.sourceVertices[index];
      expect(point.x * point.y * point.z).toBeGreaterThan(0);
    });
    geometry.tetraB.forEach((index) => {
      const point = geometry.sourceVertices[index];
      expect(point.x * point.y * point.z).toBeLessThan(0);
    });
  });

  it('gives each tetrahedron V=4, E=6, F=4, Euler=2 and vertex degree 3', () => {
    for (const [indices, edges, faces] of [
      [geometry.tetraA, geometry.edgesA, geometry.facesA],
      [geometry.tetraB, geometry.edgesB, geometry.facesB]
    ] as const) {
      expect(indices.length - edges.length + faces.length).toBe(2);
      expect(new Set(edges.map(canonicalEdge)).size).toBe(6);
      expect(
        new Set(faces.map((face) => [...face].sort((a, b) => a - b).join(','))).size
      ).toBe(4);
      const degree = new Map(indices.map((index) => [index, 0]));
      edges.forEach(([a, b]) => {
        degree.set(a, degree.get(a)! + 1);
        degree.set(b, degree.get(b)! + 1);
      });
      expect([...degree.values()]).toEqual([3, 3, 3, 3]);
    }
    expect(geometry.edges).toHaveLength(12);
    expect(geometry.faces).toHaveLength(8);
  });

  it('contains no shared external vertices or A-B structural edges', () => {
    const groupA = new Set(geometry.tetraA);
    const groupB = new Set(geometry.tetraB);
    expect([...groupA].some((index) => groupB.has(index))).toBe(false);
    geometry.edgesA.forEach(([a, b]) => {
      expect(groupA.has(a) && groupA.has(b)).toBe(true);
    });
    geometry.edgesB.forEach(([a, b]) => {
      expect(groupB.has(a) && groupB.has(b)).toBe(true);
    });
    geometry.edges.forEach(([a, b]) => {
      expect(groupA.has(a) === groupA.has(b)).toBe(true);
    });
  });

  it('makes all twelve structural edges equal to 2 sqrt(2) a', () => {
    const expected = 2 * Math.SQRT2 * DEFAULT_GEOMETRY.cubeHalfExtent;
    geometry.edges.forEach(([a, b]) => {
      expect(distance(geometry.vertices[a], geometry.vertices[b])).toBeCloseTo(
        expected,
        12
      );
    });
  });

  it('makes eight equal equilateral large faces with outward normals', () => {
    const expectedSide = 2 * Math.SQRT2 * DEFAULT_GEOMETRY.cubeHalfExtent;
    const expectedArea = 2 * Math.sqrt(3) * DEFAULT_GEOMETRY.cubeHalfExtent ** 2;
    geometry.faces.forEach((face) => {
      const points = face.map((index) => geometry.vertices[index]);
      const sides = [
        distance(points[0], points[1]),
        distance(points[1], points[2]),
        distance(points[2], points[0])
      ];
      sides.forEach((side) => expect(side).toBeCloseTo(expectedSide, 12));
      expect(triangleArea(points[0], points[1], points[2])).toBeCloseTo(
        expectedArea,
        12
      );
      expect(
        dot(faceNormal(face, geometry.vertices), faceCentroid(face, geometry.vertices))
      ).toBeGreaterThan(EPSILON);
    });
  });

  it('uses an orthonormal right-handed display basis', () => {
    const { eX, eY, eZ } = DISPLAY_BASIS;
    [eX, eY, eZ].forEach((axis) => expect(vectorLength(axis)).toBeCloseTo(1, 12));
    expect(dot(eX, eY)).toBeCloseTo(0, 12);
    expect(dot(eX, eZ)).toBeCloseTo(0, 12);
    expect(dot(eY, eZ)).toBeCloseTo(0, 12);
    const handed = cross(eX, eY);
    expect(handed.x).toBeCloseTo(eZ.x, 12);
    expect(handed.y).toBeCloseTo(eZ.y, 12);
    expect(handed.z).toBeCloseTo(eZ.z, 12);
    const mappedDiagonal = transformToDisplayBasis({ x: 1, y: 1, z: 1 });
    expect(mappedDiagonal.x).toBeCloseTo(0, 12);
    expect(mappedDiagonal.y).toBeCloseTo(0, 12);
    expect(mappedDiagonal.z).toBeCloseTo(Math.sqrt(3), 12);
  });

  it('places vertices on the four specified Z levels', () => {
    const a = DEFAULT_GEOMETRY.cubeHalfExtent;
    const sorted = geometry.vertices.map((point) => point.z).sort((x, y) => x - y);
    expect(sorted[0]).toBeCloseTo(-Math.sqrt(3) * a, 12);
    sorted.slice(1, 4).forEach((z) => expect(z).toBeCloseTo(-a / Math.sqrt(3), 12));
    sorted.slice(4, 7).forEach((z) => expect(z).toBeCloseTo(a / Math.sqrt(3), 12));
    expect(sorted[7]).toBeCloseTo(Math.sqrt(3) * a, 12);
  });

  it('preserves vertices and swaps tetrahedra under central inversion', () => {
    const indexByPoint = new Map(
      geometry.vertices.map((point, index) => [pointKey(point), index])
    );
    const edgesB = new Set(geometry.edgesB.map(canonicalEdge));
    geometry.tetraA.forEach((index) => {
      const point = geometry.vertices[index];
      const opposite = indexByPoint.get(pointKey({ x: -point.x, y: -point.y, z: -point.z }));
      expect(opposite).toBeDefined();
      expect(geometry.tetraB).toContain(opposite);
    });
    geometry.edgesA.forEach(([a, b]) => {
      const inverseA = indexByPoint.get(
        pointKey({
          x: -geometry.vertices[a].x,
          y: -geometry.vertices[a].y,
          z: -geometry.vertices[a].z
        })
      )!;
      const inverseB = indexByPoint.get(
        pointKey({
          x: -geometry.vertices[b].x,
          y: -geometry.vertices[b].y,
          z: -geometry.vertices[b].z
        })
      )!;
      expect(edgesB.has(canonicalEdge([inverseA, inverseB]))).toBe(true);
    });
  });

  it('finds exactly six unique internal A-B edge intersections at t = 0.5', () => {
    expect(geometry.intersections).toHaveLength(6);
    expect(new Set(geometry.intersections.map(({ point }) => pointKey(point))).size).toBe(6);
    geometry.intersections.forEach(({ point, tA, tB, edgeA, edgeB }) => {
      expect(tA).toBeCloseTo(0.5, 12);
      expect(tB).toBeCloseTo(0.5, 12);
      expect(geometry.edgesA.map(canonicalEdge)).toContain(canonicalEdge(edgeA));
      expect(geometry.edgesB.map(canonicalEdge)).toContain(canonicalEdge(edgeB));
      expect(geometry.vertices.some((vertex) => distance(vertex, point) < EPSILON)).toBe(false);
    });
  });

  it('places the six intersections at transformed cube-face centers in two Z triangles', () => {
    const a = DEFAULT_GEOMETRY.cubeHalfExtent;
    const expectedSource = [
      { x: a, y: 0, z: 0 },
      { x: -a, y: 0, z: 0 },
      { x: 0, y: a, z: 0 },
      { x: 0, y: -a, z: 0 },
      { x: 0, y: 0, z: a },
      { x: 0, y: 0, z: -a }
    ];
    const expected = new Set(
      expectedSource.map((point) => transformToDisplayBasis(point)).map(pointKey)
    );
    expect(new Set(geometry.intersections.map(({ point }) => pointKey(point)))).toEqual(
      expected
    );
    const layers = geometry.intersections
      .map(({ point }) => point.z)
      .sort((x, y) => x - y);
    layers.slice(0, 3).forEach((z) => expect(z).toBeCloseTo(-a / Math.sqrt(3), 12));
    layers.slice(3).forEach((z) => expect(z).toBeCloseTo(a / Math.sqrt(3), 12));
  });

  it('does not promote intersections to vertices or split structural edges', () => {
    expect(geometry.vertices).toHaveLength(8);
    expect(geometry.edges).toHaveLength(12);
    geometry.intersections.forEach(({ point }) => {
      expect(new Set(geometry.vertices.map(pointKey)).has(pointKey(point))).toBe(false);
    });
  });

  it('has threefold rotational symmetry around world Z', () => {
    const vertexSet = new Set(geometry.vertices.map(pointKey));
    geometry.vertices.forEach((point) => {
      expect(vertexSet.has(pointKey(rotateZ(point, 120)))).toBe(true);
      expect(vertexSet.has(pointKey(rotateZ(point, 240)))).toBe(true);
    });
  });

  it('projects 0 and 360 degrees identically and fills the low-res frame safely', () => {
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
      renderConfig.style.edgeParticleSizeMax * renderConfig.style.edgeHaloSizeMultiplier;
    let maximumHeight = 0;
    for (let phase = 0; phase < 360; phase += 1) {
      const projected = projectOrthographic(
        geometry.vertices,
        phase,
        renderConfig.style.cameraElevationDegrees,
        renderConfig.style.cameraAzimuthDegrees
      );
      const xs = projected.map((point) => point.x);
      const ys = projected.map((point) => point.y);
      const projectedHeight = Math.max(...ys) - Math.min(...ys);
      maximumHeight = Math.max(maximumHeight, projectedHeight);
      expect(Math.max(...xs) - Math.min(...xs) + margin * 2).toBeLessThan(
        horizontalCapacity
      );
      expect(projectedHeight + margin * 2).toBeLessThan(
        renderConfig.style.orthographicScale
      );
    }
    expect(maximumHeight / renderConfig.style.orthographicScale).toBeGreaterThan(0.58);
    expect(maximumHeight / renderConfig.style.orthographicScale).toBeLessThan(0.60);
  });

  it('closes exactly on the conceptual frame after two low-res turns', () => {
    const animation = {
      frameStart: 1,
      frameCount: 360,
      turns: 2,
      initialPhaseDegrees: DEFAULT_GEOMETRY.initialPhaseDegrees
    } as const;
    const first = rotationAtFrame(1, animation);
    expect(first).toBeCloseTo(0, 12);
    expect(rotationAtFrame(181, animation)).toBeCloseTo(first, 12);
    expect(rotationAtFrame(361, animation)).toBeCloseTo(first, 12);
    expect(rotationAtFrame(360, animation)).not.toBeCloseTo(first, 8);
    expect(() => rotationAtFrame(1, { ...animation, frameCount: 0 })).toThrow(
      RangeError
    );
  });
});
