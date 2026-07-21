export type Point2 = { x: number; y: number };
export type Point3 = { x: number; y: number; z: number };
export type Edge = readonly [number, number];
export type TriangleFace = readonly [number, number, number];
export type TetrahedronId = 'A' | 'B';

export type GeometryConfig = {
  cubeHalfExtent: number;
  initialPhaseDegrees: number;
};

export type DisplayBasis = {
  eX: Point3;
  eY: Point3;
  eZ: Point3;
};

export type SegmentIntersection = {
  point: Point3;
  edgeA: Edge;
  edgeB: Edge;
  tA: number;
  tB: number;
};

export type StellaOctangula = {
  sourceVertices: readonly Point3[];
  vertices: readonly Point3[];
  vertexLabels: readonly string[];
  tetraA: readonly number[];
  tetraB: readonly number[];
  edgesA: readonly Edge[];
  edgesB: readonly Edge[];
  edges: readonly Edge[];
  facesA: readonly TriangleFace[];
  facesB: readonly TriangleFace[];
  faces: readonly TriangleFace[];
  intersections: readonly SegmentIntersection[];
};

export type RotationFrames = {
  frameStart: number;
  frameCount: number;
  turns: number;
  initialPhaseDegrees: number;
};

export const DEFAULT_GEOMETRY = {
  cubeHalfExtent: 1,
  initialPhaseDegrees: 0
} as const;

export const DISPLAY_BASIS: DisplayBasis = {
  eX: { x: 1 / Math.SQRT2, y: -1 / Math.SQRT2, z: 0 },
  eY: { x: 1 / Math.sqrt(6), y: 1 / Math.sqrt(6), z: -2 / Math.sqrt(6) },
  eZ: { x: 1 / Math.sqrt(3), y: 1 / Math.sqrt(3), z: 1 / Math.sqrt(3) }
};

const TETRA_A_SIGNS = [
  [1, 1, 1],
  [1, -1, -1],
  [-1, 1, -1],
  [-1, -1, 1]
] as const;

const TETRA_B_SIGNS = [
  [-1, -1, -1],
  [-1, 1, 1],
  [1, -1, 1],
  [1, 1, -1]
] as const;

export function add(a: Point3, b: Point3): Point3 {
  return { x: a.x + b.x, y: a.y + b.y, z: a.z + b.z };
}

export function subtract(a: Point3, b: Point3): Point3 {
  return { x: a.x - b.x, y: a.y - b.y, z: a.z - b.z };
}

export function scale(point: Point3, factor: number): Point3 {
  return { x: point.x * factor, y: point.y * factor, z: point.z * factor };
}

export function dot(a: Point3, b: Point3): number {
  return a.x * b.x + a.y * b.y + a.z * b.z;
}

export function cross(a: Point3, b: Point3): Point3 {
  return {
    x: a.y * b.z - a.z * b.y,
    y: a.z * b.x - a.x * b.z,
    z: a.x * b.y - a.y * b.x
  };
}

export function vectorLength(point: Point3): number {
  return Math.hypot(point.x, point.y, point.z);
}

export function distance(a: Point3, b: Point3): number {
  return vectorLength(subtract(b, a));
}

export function transformToDisplayBasis(
  point: Point3,
  basis: DisplayBasis = DISPLAY_BASIS
): Point3 {
  return {
    x: dot(point, basis.eX),
    y: dot(point, basis.eY),
    z: dot(point, basis.eZ)
  };
}

export function faceNormal(
  face: TriangleFace,
  vertices: readonly Point3[]
): Point3 {
  const [a, b, c] = face.map((index) => vertices[index]);
  return cross(subtract(b, a), subtract(c, a));
}

export function faceCentroid(
  face: TriangleFace,
  vertices: readonly Point3[]
): Point3 {
  const [a, b, c] = face.map((index) => vertices[index]);
  return scale(add(add(a, b), c), 1 / 3);
}

export function triangleArea(a: Point3, b: Point3, c: Point3): number {
  return vectorLength(cross(subtract(b, a), subtract(c, a))) / 2;
}

function orientOutward(
  face: TriangleFace,
  vertices: readonly Point3[]
): TriangleFace {
  return dot(faceNormal(face, vertices), faceCentroid(face, vertices)) > 0
    ? face
    : [face[0], face[2], face[1]];
}

function completeEdges(indices: readonly number[]): Edge[] {
  const edges: Edge[] = [];
  for (let first = 0; first < indices.length; first += 1) {
    for (let second = first + 1; second < indices.length; second += 1) {
      edges.push([indices[first], indices[second]]);
    }
  }
  return edges;
}

function tetrahedronFaces(
  indices: readonly number[],
  vertices: readonly Point3[]
): TriangleFace[] {
  const candidates: TriangleFace[] = [
    [indices[0], indices[1], indices[2]],
    [indices[0], indices[3], indices[1]],
    [indices[0], indices[2], indices[3]],
    [indices[1], indices[3], indices[2]]
  ];
  return candidates.map((face) => orientOutward(face, vertices));
}

export function intersectSegments3D(
  startA: Point3,
  endA: Point3,
  startB: Point3,
  endB: Point3,
  tolerance = 1e-10
): { point: Point3; tA: number; tB: number } | null {
  const u = subtract(endA, startA);
  const v = subtract(endB, startB);
  const w = subtract(startA, startB);
  const uu = dot(u, u);
  const uv = dot(u, v);
  const vv = dot(v, v);
  const uw = dot(u, w);
  const vw = dot(v, w);
  const denominator = uu * vv - uv * uv;
  if (Math.abs(denominator) <= tolerance * Math.max(1, uu * vv)) return null;

  const tA = (uv * vw - vv * uw) / denominator;
  const tB = (uu * vw - uv * uw) / denominator;
  if (tA <= tolerance || tA >= 1 - tolerance || tB <= tolerance || tB >= 1 - tolerance) {
    return null;
  }
  const pointA = add(startA, scale(u, tA));
  const pointB = add(startB, scale(v, tB));
  if (distance(pointA, pointB) > tolerance) return null;
  return { point: scale(add(pointA, pointB), 0.5), tA, tB };
}

export function findTetrahedronIntersections(
  vertices: readonly Point3[],
  edgesA: readonly Edge[],
  edgesB: readonly Edge[],
  tolerance = 1e-10
): SegmentIntersection[] {
  const intersections: SegmentIntersection[] = [];
  for (const edgeA of edgesA) {
    for (const edgeB of edgesB) {
      const match = intersectSegments3D(
        vertices[edgeA[0]],
        vertices[edgeA[1]],
        vertices[edgeB[0]],
        vertices[edgeB[1]],
        tolerance
      );
      if (match) intersections.push({ ...match, edgeA, edgeB });
    }
  }
  return intersections;
}

function signLabel(sign: number): string {
  return sign > 0 ? '+' : '-';
}

export function createStellaOctangula(
  config: GeometryConfig = DEFAULT_GEOMETRY
): StellaOctangula {
  if (!(config.cubeHalfExtent > 0)) {
    throw new RangeError('cubeHalfExtent must be positive.');
  }
  const signs = [...TETRA_A_SIGNS, ...TETRA_B_SIGNS];
  const sourceVertices = signs.map(([sx, sy, sz]) => ({
    x: sx * config.cubeHalfExtent,
    y: sy * config.cubeHalfExtent,
    z: sz * config.cubeHalfExtent
  }));
  const vertices = sourceVertices.map((point) => transformToDisplayBasis(point));
  const vertexLabels = signs.map(
    ([sx, sy, sz]) => `P(${signLabel(sx)},${signLabel(sy)},${signLabel(sz)})`
  );
  const tetraA = [0, 1, 2, 3] as const;
  const tetraB = [4, 5, 6, 7] as const;
  const edgesA = completeEdges(tetraA);
  const edgesB = completeEdges(tetraB);
  const facesA = tetrahedronFaces(tetraA, vertices);
  const facesB = tetrahedronFaces(tetraB, vertices);
  const intersections = findTetrahedronIntersections(vertices, edgesA, edgesB);
  return {
    sourceVertices,
    vertices,
    vertexLabels,
    tetraA,
    tetraB,
    edgesA,
    edgesB,
    edges: [...edgesA, ...edgesB],
    facesA,
    facesB,
    faces: [...facesA, ...facesB],
    intersections
  };
}

function rotateAboutZ(point: Point3, rotationRadians: number): Point3 {
  const cosine = Math.cos(rotationRadians);
  const sine = Math.sin(rotationRadians);
  return {
    x: point.x * cosine - point.y * sine,
    y: point.x * sine + point.y * cosine,
    z: point.z
  };
}

export function projectOrthographic(
  vertices: readonly Point3[],
  rotationDegrees: number,
  cameraElevationDegrees: number,
  cameraAzimuthDegrees = -90
): readonly Point2[] {
  const rotation = (rotationDegrees * Math.PI) / 180;
  const elevation = (cameraElevationDegrees * Math.PI) / 180;
  const azimuth = (cameraAzimuthDegrees * Math.PI) / 180;
  const viewFrom = {
    x: Math.cos(elevation) * Math.cos(azimuth),
    y: Math.cos(elevation) * Math.sin(azimuth),
    z: Math.sin(elevation)
  };
  const horizontalLength = Math.hypot(viewFrom.x, viewFrom.y);
  const right = {
    x: -viewFrom.y / horizontalLength,
    y: viewFrom.x / horizontalLength,
    z: 0
  };
  const up = cross(viewFrom, right);
  return vertices.map((point) => {
    const rotated = rotateAboutZ(point, rotation);
    return { x: dot(rotated, right), y: dot(rotated, up) };
  });
}

export function rotationAtFrame(
  frame: number,
  animation: RotationFrames
): number {
  if (!(animation.frameCount > 0)) {
    throw new RangeError('frameCount must be positive.');
  }
  const initialTurns = animation.initialPhaseDegrees / 360;
  const elapsedTurns =
    ((frame - animation.frameStart) / animation.frameCount) * animation.turns;
  const normalizedTurns = ((initialTurns + elapsedTurns) % 1 + 1) % 1;
  return normalizedTurns * Math.PI * 2;
}
