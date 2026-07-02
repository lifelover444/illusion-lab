export type Vec3 = [number, number, number];

export type EdgeRole = 'rim' | 'strut';

export interface HourglassGeometryConfig {
  sides: number;
  baseRadius: number;
  pyramidHeight: number;
  maxApexSeparation: number;
  topPhaseDegrees: number;
  bottomPhaseDegrees: number;
}

export interface HourglassEdge {
  from: number;
  to: number;
  role: EdgeRole;
  label: string;
}

export interface HourglassGeometry {
  vertices: Vec3[];
  edges: HourglassEdge[];
  faces: [];
}

const degreesToRadians = (degrees: number): number => degrees * Math.PI / 180;

const createRing = (
  sides: number,
  radius: number,
  z: number,
  phaseDegrees: number
): Vec3[] => {
  const phase = degreesToRadians(phaseDegrees);

  return Array.from({ length: sides }, (_, index) => {
    const angle = phase + index * Math.PI * 2 / sides;
    return [
      radius * Math.cos(angle),
      radius * Math.sin(angle),
      z
    ];
  });
};

const addRingEdges = (
  edges: HourglassEdge[],
  start: number,
  sides: number,
  label: string
): void => {
  for (let index = 0; index < sides; index += 1) {
    edges.push({
      from: start + index,
      to: start + ((index + 1) % sides),
      role: 'rim',
      label: `${label}-${index}`
    });
  }
};

export const createHourglassGeometry = (
  config: HourglassGeometryConfig
): HourglassGeometry => {
  const topApex: Vec3 = [0, 0, 0];
  const bottomApex: Vec3 = [0, 0, 0];
  const topRing = createRing(config.sides, config.baseRadius, config.pyramidHeight, config.topPhaseDegrees);
  const bottomRing = createRing(config.sides, config.baseRadius, -config.pyramidHeight, config.bottomPhaseDegrees);
  const vertices = [topApex, ...topRing, bottomApex, ...bottomRing];
  const topApexIndex = 0;
  const topStart = 1;
  const bottomApexIndex = config.sides + 1;
  const bottomStart = bottomApexIndex + 1;
  const edges: HourglassEdge[] = [];

  addRingEdges(edges, topStart, config.sides, 'top-rim');
  addRingEdges(edges, bottomStart, config.sides, 'bottom-rim');
  for (let index = 0; index < config.sides; index += 1) {
    edges.push({
      from: topStart + index,
      to: topApexIndex,
      role: 'strut',
      label: `top-to-apex-${index}`
    });
    edges.push({
      from: bottomStart + index,
      to: bottomApexIndex,
      role: 'strut',
      label: `bottom-to-apex-${index}`
    });
  }

  return {
    vertices,
    edges,
    faces: []
  };
};
