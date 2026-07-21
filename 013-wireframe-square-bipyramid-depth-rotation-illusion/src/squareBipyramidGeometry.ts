export type Point2 = { x: number; y: number };
export type Point3 = { x: number; y: number; z: number };
export type TriangleFace = readonly [number, number, number];
export type Edge = readonly [number, number];

export type GeometryConfig = {
  waistRadius: number;
  halfHeight: number;
  initialPhaseDegrees: number;
};

export type SquareBipyramid = {
  vertices: readonly Point3[];
  faces: readonly TriangleFace[];
  edges: readonly Edge[];
  waistEdges: readonly Edge[];
};

export type RotationFrames = {
  frameStart: number;
  frameEnd: number;
  turns: number;
};

export type DustDriftConfig = {
  frameStart: number;
  frameEnd: number;
  turns: number;
  angularAmplitudeDegrees: number;
  verticalAmplitude: number;
  phaseDegrees: number;
};

export type DustDriftTransform = {
  rotationRadians: number;
  verticalOffset: number;
};

export const DEFAULT_GEOMETRY = {
  waistRadius: 1.42,
  halfHeight: 1.72,
  initialPhaseDegrees: 45
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

export function createSquareBipyramid(
  config: GeometryConfig = DEFAULT_GEOMETRY
): SquareBipyramid {
  const phase = (config.initialPhaseDegrees * Math.PI) / 180;
  const vertices: Point3[] = [
    { x: 0, y: 0, z: config.halfHeight },
    { x: 0, y: 0, z: -config.halfHeight }
  ];

  for (let index = 0; index < 4; index += 1) {
    const angle = phase + (index * Math.PI) / 2;
    vertices.push({
      x: config.waistRadius * Math.cos(angle),
      y: config.waistRadius * Math.sin(angle),
      z: 0
    });
  }

  const waistEdges: Edge[] = [];
  const edges: Edge[] = [];
  const faces: TriangleFace[] = [];
  for (let index = 0; index < 4; index += 1) {
    const current = 2 + index;
    const next = 2 + ((index + 1) % 4);
    waistEdges.push([current, next]);
    edges.push([0, current], [1, current], [current, next]);
    faces.push(orientOutward([0, current, next], vertices));
    faces.push(orientOutward([1, next, current], vertices));
  }

  return { vertices, faces, edges, waistEdges };
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

export function projectOrthographic(
  vertices: readonly Point3[],
  rotationDegrees: number,
  cameraElevationDegrees: number
): readonly Point2[] {
  const rotation = (rotationDegrees * Math.PI) / 180;
  const elevation = (cameraElevationDegrees * Math.PI) / 180;
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

export function rotationAtFrame(frame: number, animation: RotationFrames): number {
  const loopSpan = animation.frameEnd - animation.frameStart;
  if (loopSpan <= 0) throw new RangeError('frameEnd must be at least frameStart.');
  const turns = ((frame - animation.frameStart) / loopSpan) * animation.turns;
  const normalizedTurns = ((turns % 1) + 1) % 1;
  return normalizedTurns * Math.PI * 2;
}

export function isInsideSquareBipyramid(
  point: Point3,
  config: GeometryConfig = DEFAULT_GEOMETRY,
  boundaryPadding = 0
): boolean {
  const orientation =
    (config.initialPhaseDegrees * Math.PI) / 180 - Math.PI / 4;
  const cosine = Math.cos(orientation);
  const sine = Math.sin(orientation);
  const localX = point.x * cosine + point.y * sine;
  const localY = -point.x * sine + point.y * cosine;
  const halfSide = config.waistRadius / Math.SQRT2;
  const normalizedRadius = Math.max(Math.abs(localX), Math.abs(localY)) / halfSide;
  const normalizedHeight = Math.abs(point.z) / config.halfHeight;
  return normalizedRadius + normalizedHeight <= 1 - boundaryPadding + 1e-12;
}

export function dustDriftAtFrame(
  frame: number,
  config: DustDriftConfig
): DustDriftTransform {
  const loopSpan = config.frameEnd - config.frameStart;
  if (loopSpan <= 0) throw new RangeError('frameEnd must be greater than frameStart.');
  const turns = ((frame - config.frameStart) / loopSpan) * config.turns;
  const normalizedTurns = ((turns % 1) + 1) % 1;
  const phase =
    normalizedTurns * Math.PI * 2 +
    (config.phaseDegrees * Math.PI) / 180;
  const signal = Math.sin(phase);
  return {
    rotationRadians: ((config.angularAmplitudeDegrees * Math.PI) / 180) * signal,
    verticalOffset: config.verticalAmplitude * signal
  };
}
