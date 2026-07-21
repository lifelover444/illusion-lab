export type Point2 = { x: number; y: number };
export type Point3 = { x: number; y: number; z: number };
export type Edge = readonly [number, number];
export type QuadFace = readonly [number, number, number, number];

export type GeometryConfig = {
  waistRadius: number;
  halfHeight: number;
  initialPhaseDegrees: number;
  lowerRingTwistDegrees: number;
};

export type TetragonalTrapezohedron = {
  vertices: readonly Point3[];
  edges: readonly Edge[];
  beltEdges: readonly Edge[];
  faces: readonly QuadFace[];
  beltHalfHeight: number;
};

export type RotationFrames = {
  frameStart: number;
  frameCount: number;
  turns: number;
};

export type VerticalDriftFrames = {
  frameStart: number;
  framesPerCycle: number;
  amplitude: number;
  phaseRadians: number;
};

export const DEFAULT_GEOMETRY = {
  waistRadius: 1.34,
  halfHeight: 1.72,
  initialPhaseDegrees: 22.5,
  lowerRingTwistDegrees: 45
} as const;

const DEGREES_TO_RADIANS = Math.PI / 180;

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

export function dot(a: Point3, b: Point3): number {
  return a.x * b.x + a.y * b.y + a.z * b.z;
}

export function vectorLength(point: Point3): number {
  return Math.hypot(point.x, point.y, point.z);
}

export function faceCentroid(
  face: QuadFace,
  vertices: readonly Point3[]
): Point3 {
  return face.reduce(
    (sum, index) => ({
      x: sum.x + vertices[index].x / 4,
      y: sum.y + vertices[index].y / 4,
      z: sum.z + vertices[index].z / 4
    }),
    { x: 0, y: 0, z: 0 }
  );
}

export function faceNormal(
  face: QuadFace,
  vertices: readonly Point3[]
): Point3 {
  const [a, b, c] = face.map((index) => vertices[index]);
  return cross(subtract(b, a), subtract(c, a));
}

function orientOutward(
  face: QuadFace,
  vertices: readonly Point3[]
): QuadFace {
  if (dot(faceNormal(face, vertices), faceCentroid(face, vertices)) > 0) {
    return face;
  }
  return [face[0], face[3], face[2], face[1]];
}

export function triangleArea(a: Point3, b: Point3, c: Point3): number {
  return vectorLength(cross(subtract(b, a), subtract(c, a))) / 2;
}

export function quadArea(
  face: QuadFace,
  vertices: readonly Point3[]
): number {
  const [a, b, c, d] = face.map((index) => vertices[index]);
  return triangleArea(a, b, c) + triangleArea(a, c, d);
}

export function facePlanarityError(
  face: QuadFace,
  vertices: readonly Point3[]
): number {
  const [a, b, c, d] = face.map((index) => vertices[index]);
  const normal = cross(subtract(b, a), subtract(c, a));
  const magnitude = vectorLength(normal);
  if (magnitude === 0) return Number.POSITIVE_INFINITY;
  return Math.abs(dot(normal, subtract(d, a))) / magnitude;
}

export function canonicalEdge([a, b]: Edge): string {
  return a < b ? `${a},${b}` : `${b},${a}`;
}

export function faceBoundaryEdges(face: QuadFace): readonly Edge[] {
  return face.map((vertex, index) => [vertex, face[(index + 1) % 4]] as const);
}

export function edgeFaceIncidence(
  faces: readonly QuadFace[]
): ReadonlyMap<string, number> {
  const incidence = new Map<string, number>();
  for (const face of faces) {
    for (const edge of faceBoundaryEdges(face)) {
      const key = canonicalEdge(edge);
      incidence.set(key, (incidence.get(key) ?? 0) + 1);
    }
  }
  return incidence;
}

export function createTetragonalTrapezohedron(
  config: GeometryConfig = DEFAULT_GEOMETRY
): TetragonalTrapezohedron {
  if (config.waistRadius <= 0 || config.halfHeight <= 0) {
    throw new RangeError('waistRadius and halfHeight must be positive.');
  }
  if (Math.abs(config.lowerRingTwistDegrees - 45) > 1e-12) {
    throw new RangeError('A regular tetragonal trapezohedron requires a 45-degree lower-ring twist.');
  }

  const radius = config.waistRadius;
  const halfHeight = config.halfHeight;
  const beltHalfHeight = halfHeight * (3 - 2 * Math.SQRT2);
  const phase = config.initialPhaseDegrees * DEGREES_TO_RADIANS;
  const twist = config.lowerRingTwistDegrees * DEGREES_TO_RADIANS;
  const vertices: Point3[] = [
    { x: 0, y: 0, z: halfHeight },
    { x: 0, y: 0, z: -halfHeight }
  ];

  for (let index = 0; index < 4; index += 1) {
    const angle = phase + (index * Math.PI) / 2;
    vertices.push({
      x: radius * Math.cos(angle),
      y: radius * Math.sin(angle),
      z: beltHalfHeight
    });
  }
  for (let index = 0; index < 4; index += 1) {
    const angle = phase + twist + (index * Math.PI) / 2;
    vertices.push({
      x: radius * Math.cos(angle),
      y: radius * Math.sin(angle),
      z: -beltHalfHeight
    });
  }

  const edges: Edge[] = [];
  const beltEdges: Edge[] = [];
  const faces: QuadFace[] = [];
  for (let index = 0; index < 4; index += 1) {
    const upper = 2 + index;
    const nextUpper = 2 + ((index + 1) % 4);
    const lower = 6 + index;
    const nextLower = 6 + ((index + 1) % 4);
    edges.push([0, upper]);
    edges.push([1, lower]);
    edges.push([lower, upper], [lower, nextUpper]);
    beltEdges.push([lower, upper], [lower, nextUpper]);
    faces.push(orientOutward([0, upper, lower, nextUpper], vertices));
    faces.push(orientOutward([1, lower, nextUpper, nextLower], vertices));
  }

  return { vertices, edges, beltEdges, faces, beltHalfHeight };
}

export function rotateReflectZ(point: Point3, rotationDegrees = 45): Point3 {
  const angle = rotationDegrees * DEGREES_TO_RADIANS;
  const cosine = Math.cos(angle);
  const sine = Math.sin(angle);
  return {
    x: point.x * cosine - point.y * sine,
    y: point.x * sine + point.y * cosine,
    z: -point.z
  };
}

function approximatelyEqual(a: Point3, b: Point3, epsilon: number): boolean {
  return (
    Math.abs(a.x - b.x) <= epsilon &&
    Math.abs(a.y - b.y) <= epsilon &&
    Math.abs(a.z - b.z) <= epsilon
  );
}

export function hasS8RotoreflectionSymmetry(
  vertices: readonly Point3[],
  epsilon = 1e-10
): boolean {
  return vertices.every((vertex) =>
    vertices.some((candidate) =>
      approximatelyEqual(rotateReflectZ(vertex), candidate, epsilon)
    )
  );
}

export function hasCentralInversionSymmetry(
  vertices: readonly Point3[],
  epsilon = 1e-10
): boolean {
  return vertices.every((vertex) =>
    vertices.some((candidate) =>
      approximatelyEqual(
        { x: -vertex.x, y: -vertex.y, z: -vertex.z },
        candidate,
        epsilon
      )
    )
  );
}

export function projectOrthographic(
  vertices: readonly Point3[],
  rotationDegrees: number,
  cameraElevationDegrees: number
): readonly Point2[] {
  const rotation = rotationDegrees * DEGREES_TO_RADIANS;
  const elevation = cameraElevationDegrees * DEGREES_TO_RADIANS;
  const cosine = Math.cos(rotation);
  const sine = Math.sin(rotation);
  const elevationCosine = Math.cos(elevation);
  const elevationSine = Math.sin(elevation);
  return vertices.map((point) => {
    const rotatedX = point.x * cosine - point.y * sine;
    const rotatedY = point.x * sine + point.y * cosine;
    return {
      x: rotatedX,
      y: point.z * elevationCosine - rotatedY * elevationSine
    };
  });
}

export function rotationAtFrame(
  frame: number,
  animation: RotationFrames
): number {
  if (animation.frameCount <= 0) {
    throw new RangeError('frameCount must be positive.');
  }
  const turns =
    ((frame - animation.frameStart) / animation.frameCount) * animation.turns;
  const normalizedTurns = ((turns % 1) + 1) % 1;
  return normalizedTurns * Math.PI * 2;
}

export function verticalDriftOffsetAtFrame(
  frame: number,
  animation: VerticalDriftFrames
): number {
  if (animation.framesPerCycle <= 0) {
    throw new RangeError('framesPerCycle must be positive.');
  }
  const elapsed = frame - animation.frameStart;
  const normalizedFrame =
    ((elapsed % animation.framesPerCycle) + animation.framesPerCycle) %
    animation.framesPerCycle;
  const phase =
    (normalizedFrame / animation.framesPerCycle) * Math.PI * 2 +
    animation.phaseRadians;
  return animation.amplitude * Math.sin(phase);
}

export function isInsideTetragonalTrapezohedron(
  point: Point3,
  geometry: TetragonalTrapezohedron = createTetragonalTrapezohedron(),
  boundaryPadding = 0
): boolean {
  return geometry.faces.every((face) => {
    const normal = faceNormal(face, geometry.vertices);
    const origin = geometry.vertices[face[0]];
    const signedDistance = dot(normal, subtract(point, origin)) / vectorLength(normal);
    return signedDistance <= -boundaryPadding + 1e-12;
  });
}
