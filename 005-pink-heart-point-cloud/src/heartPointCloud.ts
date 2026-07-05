export interface HeartPointCloudConfig {
  count: number;
  seed: number;
  width: number;
  height: number;
  depth: number;
  lobeLift: number;
  pointSizeMin: number;
  pointSizeMax: number;
}

export interface HeartPoint {
  x: number;
  y: number;
  z: number;
  size: number;
  normalizedX: number;
  normalizedY: number;
}

export interface HeartPointCloud {
  points: HeartPoint[];
}

export interface PointCloudBounds {
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
  minZ: number;
  maxZ: number;
}

const HEART_X_LIMIT = 1.35;
const HEART_Y_MIN = -1.15;
const HEART_Y_MAX = 1.25;

const mulberry32 = (seed: number): (() => number) => {
  let state = seed >>> 0;

  return () => {
    state += 0x6D2B79F5;
    let value = state;
    value = Math.imul(value ^ value >>> 15, value | 1);
    value ^= value + Math.imul(value ^ value >>> 7, value | 61);
    return ((value ^ value >>> 14) >>> 0) / 4294967296;
  };
};

const randomBetween = (random: () => number, min: number, max: number): number =>
  min + (max - min) * random();

const assertPositiveFinite = (fieldName: string, value: number): void => {
  if (!Number.isFinite(value) || value <= 0) {
    throw new Error(`${fieldName} must be a positive finite number.`);
  }
};

const validateConfig = (config: HeartPointCloudConfig): void => {
  if (!Number.isInteger(config.count) || config.count <= 0) {
    throw new Error('count must be a positive integer.');
  }

  assertPositiveFinite('width', config.width);
  assertPositiveFinite('height', config.height);
  assertPositiveFinite('depth', config.depth);
  assertPositiveFinite('pointSizeMin', config.pointSizeMin);
  assertPositiveFinite('pointSizeMax', config.pointSizeMax);

  if (config.pointSizeMin > config.pointSizeMax) {
    throw new Error('pointSizeMin must be less than or equal to pointSizeMax.');
  }
};

export const isInsideHeart = (x: number, y: number): boolean => {
  const value = (x * x + y * y - 1) ** 3 - x * x * y ** 3;
  return value <= 0;
};

export const createHeartPointCloud = (config: HeartPointCloudConfig): HeartPointCloud => {
  validateConfig(config);

  const random = mulberry32(config.seed);
  const points: HeartPoint[] = [];
  let attempts = 0;
  const maxAttempts = config.count * 180;

  while (points.length < config.count && attempts < maxAttempts) {
    attempts += 1;
    const normalizedX = randomBetween(random, -HEART_X_LIMIT, HEART_X_LIMIT);
    const normalizedY = randomBetween(random, HEART_Y_MIN, HEART_Y_MAX);

    if (!isInsideHeart(normalizedX, normalizedY)) {
      continue;
    }

    const centerBias = 1 - Math.min(1, Math.abs(normalizedX) / HEART_X_LIMIT);
    const depthJitter = randomBetween(random, -0.5, 0.5);
    const normalizedYCenter = (HEART_Y_MIN + HEART_Y_MAX) / 2;
    const y = (normalizedY - normalizedYCenter) / (HEART_Y_MAX - HEART_Y_MIN) * config.height + config.lobeLift;

    points.push({
      x: normalizedX / HEART_X_LIMIT * config.width / 2,
      y,
      z: depthJitter * config.depth * (0.62 + centerBias * 0.38),
      size: randomBetween(random, config.pointSizeMin, config.pointSizeMax),
      normalizedX,
      normalizedY
    });
  }

  if (points.length !== config.count) {
    throw new Error(`Generated ${points.length} heart points after ${attempts} attempts; expected ${config.count}.`);
  }

  return { points };
};

export const getPointCloudBounds = (points: HeartPoint[]): PointCloudBounds => {
  if (points.length === 0) {
    throw new Error('Cannot compute bounds for an empty point cloud.');
  }

  return points.reduce<PointCloudBounds>(
    (bounds, point) => ({
      minX: Math.min(bounds.minX, point.x),
      maxX: Math.max(bounds.maxX, point.x),
      minY: Math.min(bounds.minY, point.y),
      maxY: Math.max(bounds.maxY, point.y),
      minZ: Math.min(bounds.minZ, point.z),
      maxZ: Math.max(bounds.maxZ, point.z)
    }),
    {
      minX: Number.POSITIVE_INFINITY,
      maxX: Number.NEGATIVE_INFINITY,
      minY: Number.POSITIVE_INFINITY,
      maxY: Number.NEGATIVE_INFINITY,
      minZ: Number.POSITIVE_INFINITY,
      maxZ: Number.NEGATIVE_INFINITY
    }
  );
};
