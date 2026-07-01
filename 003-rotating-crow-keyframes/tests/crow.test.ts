import { describe, expect, it } from 'vitest';
import {
  createCrowProjectionRows,
  projectCrowRow,
  type CrowProjectionRows
} from '../src/crow';
import {
  EYE_MAX_OPACITY,
  EDGE_DRIFT_RATIO,
  LOWER_OCCLUSION_RATIO,
  LOOP_DURATION,
  SHADOW_DRIFT_RATIO,
  SHADOW_EDGE_NARROWING,
  getAmbiguousProjection,
  getContinuityCues,
  getEyeOpacity,
  getLoopRotation
} from '../src/rotation';

function makeImageData(width: number, height: number, darkPixels: Array<[number, number]>) {
  const data = new Uint8ClampedArray(width * height * 4);

  for (let index = 0; index < data.length; index += 4) {
    data[index] = 255;
    data[index + 1] = 255;
    data[index + 2] = 255;
    data[index + 3] = 255;
  }

  for (const [x, y] of darkPixels) {
    const offset = (y * width + x) * 4;
    data[offset] = 0;
    data[offset + 1] = 0;
    data[offset + 2] = 0;
    data[offset + 3] = 255;
  }

  return { width, height, data };
}

describe('crow projection rows', () => {
  it('extracts dark row spans and ignores the white background', () => {
    const rows = createCrowProjectionRows(
      makeImageData(6, 5, [
        [1, 1],
        [2, 1],
        [3, 1],
        [2, 2],
        [3, 2]
      ]),
      { threshold: 96, profileWidthRatio: 0.2 }
    );

    expect(rows.bounds).toEqual({ minX: 1, minY: 1, maxX: 3, maxY: 2 });
    expect(rows.axisX).toBe(2);
    expect(rows.rows).toHaveLength(2);
    expect(rows.rows[0]).toMatchObject({
      y: 1,
      minX: 1,
      maxX: 3,
      centerX: 2,
      width: 3
    });
  });

  it('keeps the side silhouette wide and compresses edge-on rows', () => {
    const rows: CrowProjectionRows = createCrowProjectionRows(
      makeImageData(7, 3, [
        [1, 1],
        [2, 1],
        [3, 1],
        [4, 1],
        [5, 1]
      ]),
      { profileWidthRatio: 0.2 }
    );
    const row = rows.rows[0];
    const side = projectCrowRow(row, { sideProjection: 1 }, rows.axisX);
    const edge = projectCrowRow(row, { sideProjection: 0 }, rows.axisX);

    expect(side.width).toBe(row.width);
    expect(edge.width).toBe(row.profileWidth);
    expect(edge.width).toBeLessThan(side.width);
  });

  it('mirrors row centers around the shared rotation axis', () => {
    const row = {
      y: 10,
      minX: 10,
      maxX: 20,
      centerX: 15,
      width: 11,
      profileWidth: 3
    };
    const forward = projectCrowRow(row, { sideProjection: 1 }, 30);
    const mirrored = projectCrowRow(row, { sideProjection: -1 }, 30);
    const forwardCenter = (forward.left + forward.right) / 2;
    const mirroredCenter = (mirrored.left + mirrored.right) / 2;

    expect(forwardCenter).toBe(15);
    expect(mirroredCenter).toBe(45);
  });
});

describe('ambiguous rotation', () => {
  it('wraps elapsed time into a stable looping rotation', () => {
    expect(getLoopRotation(0)).toBe(0);
    expect(getLoopRotation(LOOP_DURATION)).toBe(0);
    expect(getLoopRotation(LOOP_DURATION / 4)).toBeCloseTo(Math.PI / 2, 12);
    expect(getLoopRotation(-LOOP_DURATION / 4)).toBeCloseTo((Math.PI * 3) / 2, 12);
  });

  it('uses cosine as the ambiguous side projection', () => {
    expect(getAmbiguousProjection(0).sideProjection).toBe(1);
    expect(getAmbiguousProjection(LOOP_DURATION / 4).sideProjection).toBe(0);
    expect(getAmbiguousProjection(LOOP_DURATION / 2).sideProjection).toBe(-1);
  });

  it('keeps the eye strongest at side angles and hidden at edge-on angles', () => {
    expect(getEyeOpacity(0)).toBe(EYE_MAX_OPACITY);
    expect(getEyeOpacity(Math.PI / 2)).toBeCloseTo(0, 12);
    expect(getEyeOpacity(0, false)).toBe(0);
  });

  it('adds weak signed continuity cues only at edge-on phases', () => {
    expect(getContinuityCues(0)).toEqual({
      edgeDriftRatio: 0,
      lowerOcclusionRatio: 0,
      shadowDriftRatio: 0,
      shadowScaleX: 1
    });

    const firstEdge = getContinuityCues(Math.PI / 2);
    const secondEdge = getContinuityCues((Math.PI * 3) / 2);

    expect(firstEdge.edgeDriftRatio).toBeCloseTo(EDGE_DRIFT_RATIO, 12);
    expect(firstEdge.lowerOcclusionRatio).toBeCloseTo(LOWER_OCCLUSION_RATIO, 12);
    expect(secondEdge.edgeDriftRatio).toBeCloseTo(-EDGE_DRIFT_RATIO, 12);
    expect(secondEdge.lowerOcclusionRatio).toBeCloseTo(-LOWER_OCCLUSION_RATIO, 12);
    expect(firstEdge.shadowDriftRatio).toBeCloseTo(SHADOW_DRIFT_RATIO, 12);
    expect(secondEdge.shadowDriftRatio).toBeCloseTo(-SHADOW_DRIFT_RATIO, 12);
    expect(firstEdge.shadowScaleX).toBeCloseTo(1 - SHADOW_EDGE_NARROWING, 12);
  });
});
