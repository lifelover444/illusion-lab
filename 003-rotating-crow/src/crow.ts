export type ImageDataLike = {
  width: number;
  height: number;
  data: ArrayLike<number>;
};

export type SilhouettePoint = {
  x: number;
  y: number;
};

export type CrowSilhouette = {
  width: number;
  height: number;
  points: SilhouettePoint[];
  bounds: {
    minX: number;
    minY: number;
    maxX: number;
    maxY: number;
  };
};

export type CrowSilhouetteOptions = {
  threshold?: number;
  sampleStride?: number;
  targetHeight?: number;
};

export type CrowProjectionRow = {
  y: number;
  minX: number;
  maxX: number;
  centerX: number;
  width: number;
  profileWidth: number;
};

export type CrowProjectionRows = {
  rows: CrowProjectionRow[];
  bounds: CrowSilhouette['bounds'];
  axisX: number;
  width: number;
  height: number;
};

export type CrowProjectionRowsOptions = {
  threshold?: number;
  profileWidthRatio?: number;
};

export type CrowProjectionState = {
  sideProjection: number;
  edgeProjection: number;
  depthPhase?: number;
};

export type ProjectedCrowRow = {
  y: number;
  left: number;
  right: number;
  width: number;
};

export type ProjectCrowRowOptions = {
  verticalPosition?: number;
};

const EDGE_EXPANSION_POWER = 0.62;
const TAIL_WIDTH_CUE = 0.052;
const BODY_EDGE_CUE = 0.018;

function isDarkPixel(data: ArrayLike<number>, offset: number, threshold: number) {
  const alpha = data[offset + 3] ?? 255;

  if (alpha < 32) {
    return false;
  }

  const red = data[offset] ?? 255;
  const green = data[offset + 1] ?? 255;
  const blue = data[offset + 2] ?? 255;
  const luma = red * 0.2126 + green * 0.7152 + blue * 0.0722;

  return luma < threshold;
}

function roundCoordinate(value: number) {
  return Number(value.toFixed(6));
}

function clamp01(value: number) {
  return Math.min(1, Math.max(0, value));
}

function smoothstep(edge0: number, edge1: number, value: number) {
  const t = clamp01((value - edge0) / (edge1 - edge0));
  return t * t * (3 - 2 * t);
}

function createEmptyBounds() {
  return {
    minX: Number.POSITIVE_INFINITY,
    minY: Number.POSITIVE_INFINITY,
    maxX: Number.NEGATIVE_INFINITY,
    maxY: Number.NEGATIVE_INFINITY
  };
}

export function createCrowSilhouette(
  imageData: ImageDataLike,
  options: CrowSilhouetteOptions = {}
): CrowSilhouette {
  const threshold = options.threshold ?? 96;
  const sampleStride = options.sampleStride ?? 1;
  const targetHeight = options.targetHeight ?? 2.75;
  const bounds = createEmptyBounds();
  const darkPixels: Array<{ x: number; y: number }> = [];

  for (let y = 0; y < imageData.height; y += 1) {
    for (let x = 0; x < imageData.width; x += 1) {
      const offset = (y * imageData.width + x) * 4;

      if (!isDarkPixel(imageData.data, offset, threshold)) {
        continue;
      }

      darkPixels.push({ x, y });
      bounds.minX = Math.min(bounds.minX, x);
      bounds.minY = Math.min(bounds.minY, y);
      bounds.maxX = Math.max(bounds.maxX, x);
      bounds.maxY = Math.max(bounds.maxY, y);
    }
  }

  if (darkPixels.length === 0) {
    throw new Error('Crow silhouette image does not contain dark pixels');
  }

  const spanY = bounds.maxY - bounds.minY + 1;
  const centerX = (bounds.minX + bounds.maxX) / 2;
  const centerY = (bounds.minY + bounds.maxY) / 2;
  const scale = targetHeight / spanY;
  const points = darkPixels
    .filter((pixel) => (pixel.x - bounds.minX) % sampleStride === 0)
    .filter((pixel) => (pixel.y - bounds.minY) % sampleStride === 0)
    .map((pixel) => ({
      x: roundCoordinate((pixel.x - centerX) * scale),
      y: roundCoordinate((centerY - pixel.y) * scale)
    }));

  return {
    width: imageData.width,
    height: imageData.height,
    points,
    bounds
  };
}

export function createCrowProjectionRows(
  imageData: ImageDataLike,
  options: CrowProjectionRowsOptions = {}
): CrowProjectionRows {
  const threshold = options.threshold ?? 96;
  const profileWidthRatio = options.profileWidthRatio ?? 0.18;
  const bounds = createEmptyBounds();
  const rowMap = new Map<number, { minX: number; maxX: number; count: number }>();

  for (let y = 0; y < imageData.height; y += 1) {
    for (let x = 0; x < imageData.width; x += 1) {
      const offset = (y * imageData.width + x) * 4;

      if (!isDarkPixel(imageData.data, offset, threshold)) {
        continue;
      }

      bounds.minX = Math.min(bounds.minX, x);
      bounds.minY = Math.min(bounds.minY, y);
      bounds.maxX = Math.max(bounds.maxX, x);
      bounds.maxY = Math.max(bounds.maxY, y);

      const row = rowMap.get(y);

      if (row) {
        row.minX = Math.min(row.minX, x);
        row.maxX = Math.max(row.maxX, x);
        row.count += 1;
      } else {
        rowMap.set(y, { minX: x, maxX: x, count: 1 });
      }
    }
  }

  if (rowMap.size === 0) {
    throw new Error('Crow projection image does not contain dark pixels');
  }

  const fullWidth = bounds.maxX - bounds.minX + 1;
  const maxCount = Math.max(...Array.from(rowMap.values(), (row) => row.count));
  const maxProfileWidth = Math.max(1, Math.round(fullWidth * profileWidthRatio));
  const rows = Array.from(rowMap.entries())
    .sort(([a], [b]) => a - b)
    .map(([y, row]) => {
      const width = row.maxX - row.minX + 1;
      const density = Math.sqrt(row.count / maxCount);

      return {
        y,
        minX: row.minX,
        maxX: row.maxX,
        centerX: roundCoordinate((row.minX + row.maxX) / 2),
        width,
        profileWidth: roundCoordinate(Math.max(1, maxProfileWidth * density))
      };
    });

  return {
    rows,
    bounds,
    axisX: roundCoordinate((bounds.minX + bounds.maxX) / 2),
    width: imageData.width,
    height: imageData.height
  };
}

export function projectCrowRow(
  row: CrowProjectionRow,
  projection: CrowProjectionState,
  axisX: number,
  options: ProjectCrowRowOptions = {}
): ProjectedCrowRow {
  const center = axisX + (row.centerX - axisX) * projection.sideProjection;
  const sideAmount = Math.abs(projection.sideProjection);
  const baseWidth = roundCoordinate(
    row.profileWidth + (row.width - row.profileWidth) * Math.pow(sideAmount, EDGE_EXPANSION_POWER)
  );
  const depthPhase = projection.depthPhase ?? 0;
  const verticalPosition = options.verticalPosition ?? 0.5;
  const tailCue = smoothstep(0.62, 0.96, verticalPosition);
  const bodyCue = smoothstep(0.28, 0.55, verticalPosition) * (1 - smoothstep(0.68, 0.92, verticalPosition));
  const featherWidth = Math.max(1, baseWidth * (1 + depthPhase * TAIL_WIDTH_CUE * tailCue));
  let left = center - featherWidth / 2;
  let right = center + featherWidth / 2;
  const bodyEdgeGrowth = featherWidth * Math.abs(depthPhase) * bodyCue * BODY_EDGE_CUE;

  if (depthPhase > 0) {
    right += bodyEdgeGrowth;
  } else if (depthPhase < 0) {
    left -= bodyEdgeGrowth;
  }

  return {
    y: row.y,
    left: roundCoordinate(left),
    right: roundCoordinate(right),
    width: roundCoordinate(right - left)
  };
}
