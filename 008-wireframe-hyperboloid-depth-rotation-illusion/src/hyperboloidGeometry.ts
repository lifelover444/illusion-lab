export type Vec3 = [number, number, number];

export type HyperboloidEdgeRole = 'latitude-ring' | 'generator-rib';

export interface HyperboloidGeometryConfig {
  ribCount: number;
  ringRadius: number;
  height: number;
  twistDegrees: number;
  latitudeRingRatios: number[];
}

export interface HyperboloidEdge {
  from: number;
  to: number;
  role: HyperboloidEdgeRole;
  label: string;
}

export interface HyperboloidGeometry {
  vertices: Vec3[];
  edges: HyperboloidEdge[];
  faces: [];
  levelRatios: number[];
}

const degreesToRadians = (degrees: number): number => degrees * Math.PI / 180;

const lerp = (from: number, to: number, ratio: number): number => from + (to - from) * ratio;

const pointOnGenerator = (
  config: HyperboloidGeometryConfig,
  ribIndex: number,
  ratio: number
): Vec3 => {
  const baseAngle = ribIndex * Math.PI * 2 / config.ribCount;
  const twist = degreesToRadians(config.twistDegrees);
  const bottom: Vec3 = [
    config.ringRadius * Math.cos(baseAngle),
    config.ringRadius * Math.sin(baseAngle),
    -config.height / 2
  ];
  const topAngle = baseAngle + twist;
  const top: Vec3 = [
    config.ringRadius * Math.cos(topAngle),
    config.ringRadius * Math.sin(topAngle),
    config.height / 2
  ];

  return [
    lerp(bottom[0], top[0], ratio),
    lerp(bottom[1], top[1], ratio),
    lerp(bottom[2], top[2], ratio)
  ];
};

export const createHyperboloidGeometry = (
  config: HyperboloidGeometryConfig
): HyperboloidGeometry => {
  const levelRatios = [
    0,
    ...config.latitudeRingRatios.filter((ratio) => ratio > 0 && ratio < 1),
    1
  ];
  const vertices: Vec3[] = [];

  for (const ratio of levelRatios) {
    for (let ribIndex = 0; ribIndex < config.ribCount; ribIndex += 1) {
      vertices.push(pointOnGenerator(config, ribIndex, ratio));
    }
  }

  const edges: HyperboloidEdge[] = [];
  for (let levelIndex = 0; levelIndex < levelRatios.length; levelIndex += 1) {
    const levelStart = levelIndex * config.ribCount;
    for (let ribIndex = 0; ribIndex < config.ribCount; ribIndex += 1) {
      edges.push({
        from: levelStart + ribIndex,
        to: levelStart + ((ribIndex + 1) % config.ribCount),
        role: 'latitude-ring',
        label: `latitude-${levelIndex}-${ribIndex}`
      });
    }
  }

  for (let levelIndex = 0; levelIndex < levelRatios.length - 1; levelIndex += 1) {
    const currentStart = levelIndex * config.ribCount;
    const nextStart = (levelIndex + 1) * config.ribCount;
    for (let ribIndex = 0; ribIndex < config.ribCount; ribIndex += 1) {
      edges.push({
        from: currentStart + ribIndex,
        to: nextStart + ribIndex,
        role: 'generator-rib',
        label: `generator-${ribIndex}-${levelIndex}`
      });
    }
  }

  return {
    vertices,
    edges,
    faces: [],
    levelRatios
  };
};
