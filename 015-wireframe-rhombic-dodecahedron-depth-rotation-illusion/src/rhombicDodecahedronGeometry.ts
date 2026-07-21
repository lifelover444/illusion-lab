export type Point2 = { x: number; y: number };
export type Point3 = { x: number; y: number; z: number };
export type Edge = readonly [number, number];
export type RhombusFace = readonly [number, number, number, number];
export type VertexKind = 'corner' | 'axis';

export type GeometryConfig = {
  latticeUnit: number;
  radialWaistScale: number;
  initialPhaseDegrees: number;
};

export type RhombicDodecahedron = {
  vertices: readonly Point3[];
  vertexKinds: readonly VertexKind[];
  vertexLabels: readonly string[];
  edges: readonly Edge[];
  faces: readonly RhombusFace[];
};

export type RotationFrames = {
  frameStart: number;
  frameCount: number;
  turns: number;
  initialPhaseDegrees: number;
};

export const DEFAULT_GEOMETRY = {
  latticeUnit: 0.86,
  radialWaistScale: 0.92,
  initialPhaseDegrees: 22.5
} as const;

const SIGNS = [-1, 1] as const;

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

function pointKey(point: Point3): string {
  return `${point.x},${point.y},${point.z}`;
}

function signLabel(sign: number): string {
  return sign > 0 ? '+' : '-';
}

function cornerLabel(sx: number, sy: number, sz: number): string {
  return `C(${signLabel(sx)},${signLabel(sy)},${signLabel(sz)})`;
}

function axisLabel(axis: 'X' | 'Y' | 'Z', sign: number): string {
  return `${axis}${signLabel(sign)}`;
}

export function faceNormal(
  face: RhombusFace,
  vertices: readonly Point3[]
): Point3 {
  const [a, b, c] = face.map((index) => vertices[index]);
  return cross(subtract(b, a), subtract(c, a));
}

export function faceCentroid(
  face: RhombusFace,
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

function orientOutward(
  face: RhombusFace,
  vertices: readonly Point3[]
): RhombusFace {
  return dot(faceNormal(face, vertices), faceCentroid(face, vertices)) > 0
    ? face
    : [face[0], face[3], face[2], face[1]];
}

export function triangleArea(a: Point3, b: Point3, c: Point3): number {
  return vectorLength(cross(subtract(b, a), subtract(c, a))) / 2;
}

export function rhombusArea(
  face: RhombusFace,
  vertices: readonly Point3[]
): number {
  const [a, b, c, d] = face.map((index) => vertices[index]);
  return triangleArea(a, b, c) + triangleArea(a, c, d);
}

export function facePlanarityError(
  face: RhombusFace,
  vertices: readonly Point3[]
): number {
  const [a, b, c, d] = face.map((index) => vertices[index]);
  const normal = cross(subtract(b, a), subtract(c, a));
  return Math.abs(dot(normal, subtract(d, a))) / vectorLength(normal);
}

export function createRhombicDodecahedron(
  config: GeometryConfig = DEFAULT_GEOMETRY
): RhombicDodecahedron {
  if (!(config.latticeUnit > 0)) {
    throw new RangeError('latticeUnit must be positive.');
  }
  if (!(config.radialWaistScale > 0 && config.radialWaistScale <= 1)) {
    throw new RangeError('radialWaistScale must be in the range (0, 1].');
  }

  const a = config.latticeUnit;
  const radial = a * config.radialWaistScale;
  const vertices: Point3[] = [];
  const vertexKinds: VertexKind[] = [];
  const vertexLabels: string[] = [];
  const indexByLabel = new Map<string, number>();

  const addVertex = (label: string, point: Point3, kind: VertexKind): void => {
    indexByLabel.set(label, vertices.length);
    vertexLabels.push(label);
    vertexKinds.push(kind);
    vertices.push(point);
  };

  for (const sx of SIGNS) {
    for (const sy of SIGNS) {
      for (const sz of SIGNS) {
        addVertex(
          cornerLabel(sx, sy, sz),
          { x: sx * radial, y: sy * radial, z: sz * a },
          'corner'
        );
      }
    }
  }
  addVertex(axisLabel('X', 1), { x: 2 * radial, y: 0, z: 0 }, 'axis');
  addVertex(axisLabel('X', -1), { x: -2 * radial, y: 0, z: 0 }, 'axis');
  addVertex(axisLabel('Y', 1), { x: 0, y: 2 * radial, z: 0 }, 'axis');
  addVertex(axisLabel('Y', -1), { x: 0, y: -2 * radial, z: 0 }, 'axis');
  addVertex(axisLabel('Z', 1), { x: 0, y: 0, z: 2 * a }, 'axis');
  addVertex(axisLabel('Z', -1), { x: 0, y: 0, z: -2 * a }, 'axis');

  const getIndex = (label: string): number => {
    const index = indexByLabel.get(label);
    if (index === undefined) throw new Error(`Missing vertex ${label}.`);
    return index;
  };
  const corner = (sx: number, sy: number, sz: number): number =>
    getIndex(cornerLabel(sx, sy, sz));
  const axis = (name: 'X' | 'Y' | 'Z', sign: number): number =>
    getIndex(axisLabel(name, sign));

  const edges: Edge[] = [];
  for (const sx of SIGNS) {
    for (const sy of SIGNS) {
      for (const sz of SIGNS) {
        const c = corner(sx, sy, sz);
        edges.push([c, axis('X', sx)], [c, axis('Y', sy)], [c, axis('Z', sz)]);
      }
    }
  }

  const faces: RhombusFace[] = [];
  for (const sx of SIGNS) {
    for (const sy of SIGNS) {
      faces.push(
        orientOutward(
          [axis('X', sx), corner(sx, sy, 1), axis('Y', sy), corner(sx, sy, -1)],
          vertices
        )
      );
    }
  }
  for (const sx of SIGNS) {
    for (const sz of SIGNS) {
      faces.push(
        orientOutward(
          [axis('X', sx), corner(sx, 1, sz), axis('Z', sz), corner(sx, -1, sz)],
          vertices
        )
      );
    }
  }
  for (const sy of SIGNS) {
    for (const sz of SIGNS) {
      faces.push(
        orientOutward(
          [axis('Y', sy), corner(1, sy, sz), axis('Z', sz), corner(-1, sy, sz)],
          vertices
        )
      );
    }
  }

  if (new Set(vertices.map(pointKey)).size !== vertices.length) {
    throw new Error('Generated duplicate vertices.');
  }
  return { vertices, vertexKinds, vertexLabels, edges, faces };
}

export function isInsideRhombicDodecahedron(
  point: Point3,
  config: GeometryConfig = DEFAULT_GEOMETRY,
  tolerance = 1e-12
): boolean {
  const a = config.latticeUnit;
  const scale = config.radialWaistScale;
  return (
    Math.abs(point.x) + Math.abs(point.y) <= 2 * a * scale + tolerance &&
    Math.abs(point.x) / scale + Math.abs(point.z) <= 2 * a + tolerance &&
    Math.abs(point.y) / scale + Math.abs(point.z) <= 2 * a + tolerance
  );
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
  const rightLength = Math.hypot(viewFrom.x, viewFrom.y);
  const right = {
    x: -viewFrom.y / rightLength,
    y: viewFrom.x / rightLength,
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
  const phaseTurns = animation.initialPhaseDegrees / 360;
  const elapsedTurns =
    ((frame - animation.frameStart) / animation.frameCount) * animation.turns;
  const normalizedTurns = ((phaseTurns + elapsedTurns) % 1 + 1) % 1;
  return normalizedTurns * Math.PI * 2;
}
