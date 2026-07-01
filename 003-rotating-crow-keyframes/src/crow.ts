export type ImageDataLike = {
  width: number;
  height: number;
  data: ArrayLike<number>;
};

export type CrowBounds = {
  minX: number;
  minY: number;
  maxX: number;
  maxY: number;
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
  bounds: CrowBounds;
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
};

export type ProjectedCrowRow = {
  y: number;
  left: number;
  right: number;
  width: number;
};

const EDGE_EXPANSION_POWER = 0.62;

function createEmptyBounds(): CrowBounds {
  return {
    minX: Number.POSITIVE_INFINITY,
    minY: Number.POSITIVE_INFINITY,
    maxX: Number.NEGATIVE_INFINITY,
    maxY: Number.NEGATIVE_INFINITY
  };
}

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
  const rounded = Number(value.toFixed(6));
  return Object.is(rounded, -0) ? 0 : rounded;
}

export function createCrowProjectionRows(
  imageData: ImageDataLike,
  options: CrowProjectionRowsOptions = {}
): CrowProjectionRows {
  const threshold = options.threshold ?? 96;
  const profileWidthRatio = options.profileWidthRatio ?? 0.17;
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
  axisX: number
): ProjectedCrowRow {
  const center = axisX + (row.centerX - axisX) * projection.sideProjection;
  const sideAmount = Math.abs(projection.sideProjection);
  const width = roundCoordinate(
    row.profileWidth + (row.width - row.profileWidth) * Math.pow(sideAmount, EDGE_EXPANSION_POWER)
  );

  return {
    y: row.y,
    left: roundCoordinate(center - width / 2),
    right: roundCoordinate(center + width / 2),
    width
  };
}
