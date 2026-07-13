export type Point3 = { x: number; y: number; z: number };

export type InterlockedRingsGeometry = {
  ringRadius: number;
  centerOffset: number;
  tubeHalfWidth: number;
  tubeHalfThickness: number;
};

export type RingId = 'a' | 'b';

export function ringCenterlinePoint(
  ring: RingId,
  angle: number,
  geometry: InterlockedRingsGeometry
): Point3 {
  const halfOffset = geometry.centerOffset / 2;
  if (ring === 'a') {
    return {
      x: -halfOffset + geometry.ringRadius * Math.cos(angle),
      y: geometry.ringRadius * Math.sin(angle),
      z: 0
    };
  }

  return {
    x: halfOffset + geometry.ringRadius * Math.cos(angle),
    y: 0,
    z: geometry.ringRadius * Math.sin(angle)
  };
}

export function ringSurfacePoint(
  ring: RingId,
  majorAngle: number,
  minorAngle: number,
  geometry: InterlockedRingsGeometry
): Point3 {
  const center = ringCenterlinePoint(ring, majorAngle, geometry);
  const radial = geometry.tubeHalfWidth * Math.cos(minorAngle);
  const axial = geometry.tubeHalfThickness * Math.sin(minorAngle);

  if (ring === 'a') {
    return {
      x: center.x + radial * Math.cos(majorAngle),
      y: center.y + radial * Math.sin(majorAngle),
      z: center.z + axial
    };
  }

  return {
    x: center.x + radial * Math.cos(majorAngle),
    y: center.y - axial,
    z: center.z + radial * Math.sin(majorAngle)
  };
}

export function rotateX(point: Point3, angle: number): Point3 {
  return {
    x: point.x,
    y: point.y * Math.cos(angle) - point.z * Math.sin(angle),
    z: point.y * Math.sin(angle) + point.z * Math.cos(angle)
  };
}

export function rotateZ(point: Point3, angle: number): Point3 {
  return {
    x: point.x * Math.cos(angle) - point.y * Math.sin(angle),
    y: point.x * Math.sin(angle) + point.y * Math.cos(angle),
    z: point.z
  };
}

export function rotateY(point: Point3, angle: number): Point3 {
  return {
    x: point.x * Math.cos(angle) + point.z * Math.sin(angle),
    y: point.y,
    z: -point.x * Math.sin(angle) + point.z * Math.cos(angle)
  };
}

export function presentPoint(
  point: Point3,
  tiltX: number,
  turnZ: number,
  standY: number
): Point3 {
  return rotateY(rotateZ(rotateX(point, tiltX), turnZ), standY);
}
