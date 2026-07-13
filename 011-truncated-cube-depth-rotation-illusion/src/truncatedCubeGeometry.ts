export type Point3 = { x: number; y: number; z: number };

export type Sign = -1 | 1;

export type TruncatedCubeGeometry = {
  edgeLength: number;
  cutDepth: number;
};

export type Axis = 'x' | 'y' | 'z';

export function cornerTriangleVertices(
  sx: Sign,
  sy: Sign,
  sz: Sign,
  geometry: TruncatedCubeGeometry
): [Point3, Point3, Point3] {
  const half = geometry.edgeLength / 2;
  const inset = half - geometry.cutDepth;
  return [
    { x: sx * inset, y: sy * half, z: sz * half },
    { x: sx * half, y: sy * inset, z: sz * half },
    { x: sx * half, y: sy * half, z: sz * inset }
  ];
}

export function isOnLargeFace(
  u: number,
  v: number,
  geometry: TruncatedCubeGeometry
): boolean {
  const half = geometry.edgeLength / 2;
  return (
    Math.abs(u) <= half &&
    Math.abs(v) <= half &&
    Math.abs(u) + Math.abs(v) <= geometry.edgeLength - geometry.cutDepth
  );
}

export function largeFacePoint(
  axis: Axis,
  sign: Sign,
  u: number,
  v: number,
  geometry: TruncatedCubeGeometry
): Point3 {
  if (!isOnLargeFace(u, v, geometry)) {
    throw new RangeError('Point lies outside the truncated large face.');
  }

  const half = geometry.edgeLength / 2;
  if (axis === 'x') return { x: sign * half, y: u, z: v };
  if (axis === 'y') return { x: u, y: sign * half, z: v };
  return { x: u, y: v, z: sign * half };
}

export function pointOnTriangle(
  vertices: [Point3, Point3, Point3],
  u: number,
  v: number
): Point3 {
  if (u < 0 || v < 0 || u + v > 1) {
    throw new RangeError('Triangle barycentric coordinates must satisfy u >= 0, v >= 0, u + v <= 1.');
  }

  const [a, b, c] = vertices;
  return {
    x: a.x + u * (b.x - a.x) + v * (c.x - a.x),
    y: a.y + u * (b.y - a.y) + v * (c.y - a.y),
    z: a.z + u * (b.z - a.z) + v * (c.z - a.z)
  };
}

export function cutPlaneValue(point: Point3, sx: Sign, sy: Sign, sz: Sign): number {
  return sx * point.x + sy * point.y + sz * point.z;
}
