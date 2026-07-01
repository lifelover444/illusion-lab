import { describe, expect, it } from 'vitest';
import {
  createCrowProjectionRows,
  createCrowSilhouette,
  projectCrowRow
} from '../src/crow';
import { getCrowStageLayout } from '../src/layout';
import { LOOP_DURATION, getAmbiguousProjection, getEyeOpacity, getLoopRotation } from '../src/rotation';

function imageDataFromPixels(width: number, height: number, pixels: number[][]) {
  const data = new Uint8ClampedArray(width * height * 4);

  pixels.forEach(([x, y, r, g, b, a = 255]) => {
    const index = (y * width + x) * 4;
    data[index] = r;
    data[index + 1] = g;
    data[index + 2] = b;
    data[index + 3] = a;
  });

  for (let index = 0; index < width * height; index += 1) {
    const offset = index * 4;
    if (data[offset + 3] === 0) {
      data[offset] = 255;
      data[offset + 1] = 255;
      data[offset + 2] = 255;
      data[offset + 3] = 255;
    }
  }

  return { width, height, data };
}

describe('createCrowSilhouette', () => {
  it('extracts dark crow pixels while ignoring white background and the pale eye ring', () => {
    const imageData = imageDataFromPixels(5, 4, [
      [1, 1, 0, 0, 0],
      [2, 1, 255, 255, 255],
      [3, 1, 18, 18, 18],
      [1, 2, 32, 31, 30],
      [2, 2, 246, 246, 246],
      [3, 2, 15, 15, 15]
    ]);

    const silhouette = createCrowSilhouette(imageData, {
      threshold: 80,
      targetHeight: 2
    });

    expect(silhouette.width).toBe(5);
    expect(silhouette.height).toBe(4);
    expect(silhouette.points).toHaveLength(4);
    expect(silhouette.bounds).toEqual({ minX: 1, minY: 1, maxX: 3, maxY: 2 });
    expect(silhouette.points).toEqual([
      { x: -1, y: 0.5 },
      { x: 1, y: 0.5 },
      { x: -1, y: -0.5 },
      { x: 1, y: -0.5 }
    ]);
  });

  it('samples dense silhouettes with a configurable stride', () => {
    const pixels: number[][] = [];

    for (let y = 1; y < 5; y += 1) {
      for (let x = 1; x < 5; x += 1) {
        pixels.push([x, y, 0, 0, 0]);
      }
    }

    const imageData = imageDataFromPixels(6, 6, pixels);
    const silhouette = createCrowSilhouette(imageData, {
      threshold: 80,
      sampleStride: 2,
      targetHeight: 4
    });

    expect(silhouette.points).toHaveLength(4);
    expect(silhouette.points[0]).toEqual({ x: -1.5, y: 1.5 });
    expect(silhouette.points[3]).toEqual({ x: 0.5, y: -0.5 });
  });
});

describe('createCrowProjectionRows', () => {
  it('compresses every dark row into row spans for a dancer-style silhouette turntable', () => {
    const rows = createCrowProjectionRows(
      imageDataFromPixels(6, 5, [
        [2, 1, 0, 0, 0],
        [3, 1, 0, 0, 0],
        [1, 2, 0, 0, 0],
        [2, 2, 0, 0, 0],
        [3, 2, 0, 0, 0],
        [4, 2, 0, 0, 0],
        [2, 3, 0, 0, 0]
      ]),
      { threshold: 80, profileWidthRatio: 0.25 }
    );

    expect(rows.bounds).toEqual({ minX: 1, minY: 1, maxX: 4, maxY: 3 });
    expect(rows.axisX).toBe(2.5);
    expect(rows.rows).toEqual([
      { y: 1, minX: 2, maxX: 3, centerX: 2.5, width: 2, profileWidth: 1 },
      { y: 2, minX: 1, maxX: 4, centerX: 2.5, width: 4, profileWidth: 1 },
      { y: 3, minX: 2, maxX: 2, centerX: 2, width: 1, profileWidth: 1 }
    ]);
  });
});

describe('projectCrowRow', () => {
  const row = { y: 12, minX: 10, maxX: 18, centerX: 14, width: 9, profileWidth: 3 };

  it('keeps the side silhouette at the side-facing angle', () => {
    expect(projectCrowRow(row, { sideProjection: 1, edgeProjection: 0 }, 16)).toEqual({
      y: 12,
      left: 9.5,
      right: 18.5,
      width: 9
    });
  });

  it('collapses to a centered narrow profile at the edge-on angle', () => {
    expect(projectCrowRow(row, { sideProjection: 0, edgeProjection: 1 }, 16)).toEqual({
      y: 12,
      left: 14.5,
      right: 17.5,
      width: 3
    });
  });

  it('mirrors the row after half a turn without exposing any depth order', () => {
    expect(projectCrowRow(row, { sideProjection: -1, edgeProjection: 0 }, 16)).toEqual({
      y: 12,
      left: 13.5,
      right: 22.5,
      width: 9
    });
  });

  it('expands quickly away from the edge-on pose instead of sticking on a narrow plateau', () => {
    const wideRow = { y: 12, minX: 10, maxX: 110, centerX: 60, width: 101, profileWidth: 18 };
    const projected = projectCrowRow(
      wideRow,
      {
        sideProjection: Math.cos((85 * Math.PI) / 180),
        edgeProjection: Math.sin((85 * Math.PI) / 180)
      },
      60
    );

    expect(projected.width).toBeGreaterThan(34);
    expect(projected.width).toBeLessThan(38);
  });

  it('varies lower feather rows slightly between front and back edge-on phases', () => {
    const front = projectCrowRow(
      row,
      { sideProjection: 0, edgeProjection: 1, depthPhase: 1 },
      16,
      { verticalPosition: 0.86 }
    );
    const back = projectCrowRow(
      row,
      { sideProjection: 0, edgeProjection: 1, depthPhase: -1 },
      16,
      { verticalPosition: 0.86 }
    );

    expect(front.width).toBeGreaterThan(back.width);
    expect(front.width / back.width).toBeGreaterThan(1.08);
    expect(front.width / back.width).toBeLessThan(1.13);
  });
});

describe('getLoopRotation', () => {
  it('returns to the same direction over a faster illusion-tuned default duration', () => {
    expect(LOOP_DURATION).toBe(7.2);
    expect(getLoopRotation(LOOP_DURATION)).toBeCloseTo(getLoopRotation(0), 12);
  });

  it('wraps elapsed time into a stable looping rotation', () => {
    expect(getLoopRotation(0)).toBeCloseTo(0, 12);
    expect(getLoopRotation(LOOP_DURATION * 2 + LOOP_DURATION / 4)).toBeCloseTo(Math.PI / 2, 12);
    expect(getLoopRotation(-LOOP_DURATION / 4)).toBeCloseTo(Math.PI * 1.5, 12);
  });
});

describe('getAmbiguousProjection', () => {
  it('matches the spinning-dancer sequence side, edge, mirrored side, edge', () => {
    const side = getAmbiguousProjection(0);
    const front = getAmbiguousProjection(LOOP_DURATION / 4);
    const mirroredSide = getAmbiguousProjection(LOOP_DURATION / 2);
    const back = getAmbiguousProjection((LOOP_DURATION * 3) / 4);

    expect(side.angle).toBeCloseTo(0, 12);
    expect(side.sideProjection).toBe(1);
    expect(side.edgeProjection).toBe(0);

    expect(front.angle).toBeCloseTo(Math.PI / 2, 12);
    expect(front.sideProjection).toBe(0);
    expect(front.edgeProjection).toBe(1);

    expect(mirroredSide.angle).toBeCloseTo(Math.PI, 12);
    expect(mirroredSide.sideProjection).toBe(-1);
    expect(mirroredSide.edgeProjection).toBe(0);

    expect(back.angle).toBeCloseTo((Math.PI * 3) / 2, 12);
    expect(back.sideProjection).toBe(0);
    expect(back.edgeProjection).toBe(1);
  });

  it('adds weak phase cues only around the edge-on front and back poses', () => {
    const side = getAmbiguousProjection(0);
    const front = getAmbiguousProjection(LOOP_DURATION / 4);
    const mirroredSide = getAmbiguousProjection(LOOP_DURATION / 2);
    const back = getAmbiguousProjection((LOOP_DURATION * 3) / 4);

    expect(side.edgeOffsetRatio).toBe(0);
    expect(side.depthPhase).toBe(0);
    expect(mirroredSide.edgeOffsetRatio).toBe(0);
    expect(mirroredSide.depthPhase).toBe(0);

    expect(front.edgeOffsetRatio).toBeCloseTo(0.015, 12);
    expect(front.depthPhase).toBe(1);
    expect(back.edgeOffsetRatio).toBeCloseTo(-0.015, 12);
    expect(back.depthPhase).toBe(-1);
  });
});

describe('getEyeOpacity', () => {
  it('keeps the eye visible at side silhouette angles and hidden at edge-on angles', () => {
    expect(getEyeOpacity(0)).toBeCloseTo(0.72, 12);
    expect(getEyeOpacity(Math.PI)).toBeCloseTo(0.72, 12);
    expect(getEyeOpacity(Math.PI / 2)).toBeCloseTo(0, 12);
    expect(getEyeOpacity((Math.PI * 3) / 2)).toBeCloseTo(0, 12);
  });

  it('respects the user eye visibility toggle', () => {
    expect(getEyeOpacity(0, false)).toBe(0);
  });
});

describe('getCrowStageLayout', () => {
  it('shrinks and raises the crow to leave room for a lower half-body reflection', () => {
    const layout = getCrowStageLayout({
      sceneWidth: 405,
      sceneHeight: 720,
      maskWidth: 220,
      maskHeight: 360,
      edgeOffsetRatio: 0.015
    });

    expect(layout.targetHeight).toBeLessThan(720 * 0.56);
    expect(layout.drawY).toBeLessThan(720 * 0.1);
    expect(layout.drawX - layout.baseDrawX).toBeCloseTo(405 * 0.015, 6);
    expect(layout.reflectionTop).toBeGreaterThan(layout.drawY + layout.targetHeight * 0.9);
    expect(layout.reflectionHeight).toBeCloseTo(layout.targetHeight * 0.42, 6);
    expect(layout.reflectionBottom).toBeLessThan(720 * 0.8);
  });
});
