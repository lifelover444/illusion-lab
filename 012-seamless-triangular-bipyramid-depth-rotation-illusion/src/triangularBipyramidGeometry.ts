export type Point3 = { x: number; y: number; z: number };

export type TriangleFace = readonly [number, number, number];

export type GeometryConfig = {
  radius: number;
  halfHeight: number;
  initialPhaseDegrees: number;
};

export type TriangularBipyramid = {
  vertices: readonly Point3[];
  faces: readonly TriangleFace[];
  dedicatedEdges: readonly never[];
};

export type RotationFrames = {
  frameStart: number;
  frameEnd: number;
  turns: number;
};

export const DEFAULT_GEOMETRY = {
  radius: 1,
  halfHeight: Math.SQRT2,
  initialPhaseDegrees: 30
} as const;

function subtract(a: Point3, b: Point3): Point3 {
  return { x: a.x - b.x, y: a.y - b.y, z: a.z - b.z };
}

function cross(a: Point3, b: Point3): Point3 {
  return {
    x: a.y * b.z - a.z * b.y,
    y: a.z * b.x - a.x * b.z,
    z: a.x * b.y - a.y * b.x
  };
}

function dot(a: Point3, b: Point3): number {
  return a.x * b.x + a.y * b.y + a.z * b.z;
}

function length(point: Point3): number {
  return Math.hypot(point.x, point.y, point.z);
}

function faceCentroid(face: TriangleFace, vertices: readonly Point3[]): Point3 {
  const [a, b, c] = face.map((index) => vertices[index]);
  return {
    x: (a.x + b.x + c.x) / 3,
    y: (a.y + b.y + c.y) / 3,
    z: (a.z + b.z + c.z) / 3
  };
}

function orientOutward(face: TriangleFace, vertices: readonly Point3[]): TriangleFace {
  return dot(faceNormal(face, vertices), faceCentroid(face, vertices)) > 0
    ? face
    : [face[0], face[2], face[1]];
}

export function createTriangularBipyramid(
  config: GeometryConfig = DEFAULT_GEOMETRY
): TriangularBipyramid {
  const phase = (config.initialPhaseDegrees * Math.PI) / 180;
  const vertices: Point3[] = [
    { x: 0, y: 0, z: config.halfHeight },
    { x: 0, y: 0, z: -config.halfHeight }
  ];

  for (let index = 0; index < 3; index += 1) {
    const angle = phase + (index * Math.PI * 2) / 3;
    vertices.push({
      x: config.radius * Math.cos(angle),
      y: config.radius * Math.sin(angle),
      z: 0
    });
  }

  const faces: TriangleFace[] = [];
  for (let index = 0; index < 3; index += 1) {
    const current = 2 + index;
    const next = 2 + ((index + 1) % 3);
    faces.push(orientOutward([0, current, next], vertices));
    faces.push(orientOutward([1, next, current], vertices));
  }

  return { vertices, faces, dedicatedEdges: [] };
}

export function faceNormal(
  face: TriangleFace,
  vertices: readonly Point3[]
): Point3 {
  const [a, b, c] = face.map((index) => vertices[index]);
  return cross(subtract(b, a), subtract(c, a));
}

export function triangleArea(a: Point3, b: Point3, c: Point3): number {
  return length(cross(subtract(b, a), subtract(c, a))) / 2;
}

export function projectedWidth(
  vertices: readonly Point3[],
  rotationDegrees: number
): number {
  const angle = (rotationDegrees * Math.PI) / 180;
  const cosine = Math.cos(angle);
  const sine = Math.sin(angle);
  const horizontal = vertices.map((point) => point.x * cosine - point.y * sine);
  return Math.max(...horizontal) - Math.min(...horizontal);
}

export function rotationAtFrame(frame: number, animation: RotationFrames): number {
  const loopSpan = animation.frameEnd - animation.frameStart + 1;
  if (loopSpan <= 0) throw new RangeError('frameEnd must be at least frameStart.');
  const radians =
    ((frame - animation.frameStart) / loopSpan) * animation.turns * Math.PI * 2;
  const normalized = radians % (Math.PI * 2);
  return normalized < 0 ? normalized + Math.PI * 2 : normalized;
}
