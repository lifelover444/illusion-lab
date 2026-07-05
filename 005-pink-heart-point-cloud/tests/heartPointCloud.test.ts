import { describe, expect, it } from 'vitest';
import {
  createHeartPointCloud,
  getPointCloudBounds,
  isInsideHeart,
  type HeartPointCloudConfig
} from '../src/heartPointCloud';
import config from '../scripts/heart-config.json';

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

describe('render config', () => {
  it('uses a 9:16 final render profile', () => {
    expect(config.profiles.final.width / config.profiles.final.height).toBe(9 / 16);
  });

  it('uses the target final timing and two rotation cycles', () => {
    expect(config.profiles.final.fps).toBe(30);
    expect(config.profiles.final.seconds).toBe(12);
    expect(config.style.rotationCycleSeconds).toBe(6);
    expect(config.profiles.final.seconds / config.style.rotationCycleSeconds).toBe(2);
  });

  it('keeps the point cloud sparse, shallow, and unshadowed', () => {
    expect(config.geometry.count).toBeGreaterThanOrEqual(500);
    expect(config.geometry.count).toBeLessThanOrEqual(900);
    expect(config.geometry.depth).toBeLessThanOrEqual(0.5);
    expect(config.style.shadowOpacity).toBe(0);
  });
});

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

  it('changes point placement for a different seed', () => {
    const first = createHeartPointCloud(baseConfig);
    const second = createHeartPointCloud({ ...baseConfig, seed: baseConfig.seed + 1 });

    expect(second.points.slice(0, 12)).not.toEqual(first.points.slice(0, 12));
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

  it('rejects a non-positive point count', () => {
    expect(() => createHeartPointCloud({ ...baseConfig, count: 0 })).toThrow(/count/i);
  });

  it('rejects a fractional point count', () => {
    expect(() => createHeartPointCloud({ ...baseConfig, count: 1.5 })).toThrow(/count/i);
  });

  it('rejects a non-finite seed', () => {
    expect(() => createHeartPointCloud({ ...baseConfig, seed: Number.NaN })).toThrow(/seed/i);
  });

  it('rejects a fractional seed', () => {
    expect(() => createHeartPointCloud({ ...baseConfig, seed: 1.5 })).toThrow(/seed/i);
  });

  it('rejects a non-positive width', () => {
    expect(() => createHeartPointCloud({ ...baseConfig, width: 0 })).toThrow(/width/i);
  });

  it('rejects a non-finite width', () => {
    expect(() => createHeartPointCloud({ ...baseConfig, width: Number.POSITIVE_INFINITY })).toThrow(/width/i);
  });

  it('rejects a non-positive height', () => {
    expect(() => createHeartPointCloud({ ...baseConfig, height: 0 })).toThrow(/height/i);
  });

  it('rejects a non-finite height', () => {
    expect(() => createHeartPointCloud({ ...baseConfig, height: Number.NaN })).toThrow(/height/i);
  });

  it('rejects a non-positive depth', () => {
    expect(() => createHeartPointCloud({ ...baseConfig, depth: 0 })).toThrow(/depth/i);
  });

  it('rejects a non-finite depth', () => {
    expect(() => createHeartPointCloud({ ...baseConfig, depth: Number.NEGATIVE_INFINITY })).toThrow(/depth/i);
  });

  it('rejects a non-finite lobeLift', () => {
    expect(() => createHeartPointCloud({ ...baseConfig, lobeLift: Number.NaN })).toThrow(/lobeLift/i);
  });

  it('rejects a non-positive pointSizeMin with the config field name', () => {
    expect(() => createHeartPointCloud({ ...baseConfig, pointSizeMin: 0 })).toThrow(/pointSizeMin/);
  });

  it('rejects a non-finite pointSizeMin with the config field name', () => {
    expect(() => createHeartPointCloud({ ...baseConfig, pointSizeMin: Number.NaN })).toThrow(/pointSizeMin/);
  });

  it('rejects a non-positive pointSizeMax with the config field name', () => {
    expect(() => createHeartPointCloud({ ...baseConfig, pointSizeMax: 0 })).toThrow(/pointSizeMax/);
  });

  it('rejects a non-finite pointSizeMax with the config field name', () => {
    expect(() => createHeartPointCloud({ ...baseConfig, pointSizeMax: Number.POSITIVE_INFINITY })).toThrow(
      /pointSizeMax/
    );
  });

  it('rejects an inverted point size range', () => {
    expect(() =>
      createHeartPointCloud({ ...baseConfig, pointSizeMin: 0.05, pointSizeMax: 0.01 })
    ).toThrow(/pointSizeMin.*pointSizeMax|pointSizeMax.*pointSizeMin/);
  });
});
