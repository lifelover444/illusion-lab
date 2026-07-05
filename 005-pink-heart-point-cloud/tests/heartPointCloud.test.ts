import { describe, expect, it } from 'vitest';
import {
  createHeartPointCloud,
  getPointCloudBounds,
  isInsideHeart,
  type HeartPointCloudConfig
} from '../src/heartPointCloud';

const baseConfig: HeartPointCloudConfig = {
  count: 640,
  seed: 20260705,
  width: 3.0,
  height: 2.72,
  depth: 0.42,
  lobeLift: 0.1,
  pointSizeMin: 0.018,
  pointSizeMax: 0.038
};

describe('heart point cloud generation', () => {
  it('generates the configured number of points inside the heart silhouette', () => {
    const cloud = createHeartPointCloud(baseConfig);

    expect(cloud.points).toHaveLength(baseConfig.count);
    for (const point of cloud.points) {
      expect(isInsideHeart(point.normalizedX, point.normalizedY)).toBe(true);
      expect(point.x).toBeGreaterThanOrEqual(-baseConfig.width / 2);
      expect(point.x).toBeLessThanOrEqual(baseConfig.width / 2);
      expect(point.y).toBeGreaterThanOrEqual(-baseConfig.height / 2 + baseConfig.lobeLift);
      expect(point.y).toBeLessThanOrEqual(baseConfig.height / 2 + baseConfig.lobeLift);
    }
  });

  it('is deterministic for a fixed seed', () => {
    const first = createHeartPointCloud(baseConfig);
    const second = createHeartPointCloud(baseConfig);

    expect(second.points.slice(0, 12)).toEqual(first.points.slice(0, 12));
  });

  it('keeps depth shallow and centered around the rotation axis', () => {
    const cloud = createHeartPointCloud(baseConfig);
    const bounds = getPointCloudBounds(cloud.points);

    expect(bounds.minZ).toBeGreaterThanOrEqual(-baseConfig.depth / 2);
    expect(bounds.maxZ).toBeLessThanOrEqual(baseConfig.depth / 2);
    expect(Math.abs((bounds.minX + bounds.maxX) / 2)).toBeLessThan(0.08);
    expect(Math.abs((bounds.minZ + bounds.maxZ) / 2)).toBeLessThan(0.06);
  });

  it('assigns visible low-density point sizes', () => {
    const cloud = createHeartPointCloud(baseConfig);

    for (const point of cloud.points) {
      expect(point.size).toBeGreaterThanOrEqual(baseConfig.pointSizeMin);
      expect(point.size).toBeLessThanOrEqual(baseConfig.pointSizeMax);
    }
  });

  it('rejects points outside the classic heart equation', () => {
    expect(isInsideHeart(0, 0)).toBe(true);
    expect(isInsideHeart(0, 0.72)).toBe(true);
    expect(isInsideHeart(1.32, 0.9)).toBe(false);
    expect(isInsideHeart(0, -1.18)).toBe(false);
  });
});
