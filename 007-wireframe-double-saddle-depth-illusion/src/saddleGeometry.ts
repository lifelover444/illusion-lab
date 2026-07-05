export type Vec3 = [number, number, number];

export type EdgeRole = 'grid-u' | 'grid-v' | 'cross-brace';

export interface SaddleGeometryConfig {
  gridSize: number;
  span: number;
  saddleHeight: number;
  crossBraceInterval: number;
}

export interface SaddleEdge {
  from: number;
  to: number;
  role: EdgeRole;
  label: string;
}

export interface SaddleGeometry {
  vertices: Vec3[];
  edges: SaddleEdge[];
  faces: [];
}

const assertOddGridSize = (gridSize: number): void => {
  if (!Number.isInteger(gridSize) || gridSize < 3 || gridSize % 2 === 0) {
    throw new Error('Saddle gridSize must be an odd integer greater than or equal to 3.');
  }
};

const vertexIndex = (row: number, column: number, gridSize: number): number => row * gridSize + column;

const normalizeZero = (value: number): number => Object.is(value, -0) || Math.abs(value) < 1e-12 ? 0 : value;

export const createSaddleGeometry = (config: SaddleGeometryConfig): SaddleGeometry => {
  assertOddGridSize(config.gridSize);

  const half = config.span / 2;
  const maxIndex = config.gridSize - 1;
  const vertices: Vec3[] = [];
  const edges: SaddleEdge[] = [];

  for (let row = 0; row < config.gridSize; row += 1) {
    const yRatio = 1 - row / maxIndex * 2;
    const y = yRatio * half;

    for (let column = 0; column < config.gridSize; column += 1) {
      const xRatio = column / maxIndex * 2 - 1;
      const x = xRatio * half;
      const z = -config.saddleHeight * xRatio * yRatio;
      vertices.push([normalizeZero(x), normalizeZero(y), normalizeZero(z)]);
    }
  }

  for (let row = 0; row < config.gridSize; row += 1) {
    for (let column = 0; column < config.gridSize - 1; column += 1) {
      edges.push({
        from: vertexIndex(row, column, config.gridSize),
        to: vertexIndex(row, column + 1, config.gridSize),
        role: 'grid-u',
        label: `row-${row}-segment-${column}`
      });
    }
  }

  for (let column = 0; column < config.gridSize; column += 1) {
    for (let row = 0; row < config.gridSize - 1; row += 1) {
      edges.push({
        from: vertexIndex(row, column, config.gridSize),
        to: vertexIndex(row + 1, column, config.gridSize),
        role: 'grid-v',
        label: `column-${column}-segment-${row}`
      });
    }
  }

  return {
    vertices,
    edges,
    faces: []
  };
};
