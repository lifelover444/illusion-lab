import { describe, expect, it } from 'vitest';

import {
  createWavyCrownPoint,
  crownCenterHeight,
  maximumOuterRadius,
  minimumHoleRadius,
  type WavyCrownGeometry
} from '../src/wavyCrownGeometry';

const geometry: WavyCrownGeometry = {
  majorRadius: 1,
  bandHalfWidth: 0.28,
  bandHalfThickness: 0.025,
  waveCount: 4,
  waveHeight: 0.09,
  wavePhase: Math.PI / 4
};

describe('wavy crown band geometry', () => {
  it('keeps a large, clearly open center hole', () => {
    expect(minimumHoleRadius(geometry)).toBeCloseTo(0.72);
    expect(minimumHoleRadius(geometry) / maximumOuterRadius(geometry)).toBeGreaterThan(0.55);
  });

  it('has four broad peaks around one revolution', () => {
    const firstPeak = -geometry.wavePhase / geometry.waveCount;
    for (let index = 0; index < geometry.waveCount; index += 1) {
      const angle = firstPeak + index * Math.PI * 2 / geometry.waveCount;
      expect(crownCenterHeight(angle, geometry)).toBeCloseTo(geometry.waveHeight);
    }
  });

  it('keeps the ring flat across its width at each angle', () => {
    const inner = createWavyCrownPoint(0.42, -geometry.bandHalfWidth, 0, geometry);
    const outer = createWavyCrownPoint(0.42, geometry.bandHalfWidth, 0, geometry);
    expect(inner.z).toBeCloseTo(outer.z);
  });

  it('preserves only a very thin depth around the band surface', () => {
    const upper = createWavyCrownPoint(0.42, 0, geometry.bandHalfThickness, geometry);
    const lower = createWavyCrownPoint(0.42, 0, -geometry.bandHalfThickness, geometry);
    expect(upper.z - lower.z).toBeCloseTo(geometry.bandHalfThickness * 2);
  });

  it('closes seamlessly after one revolution', () => {
    const point = createWavyCrownPoint(0.37, 0.12, 0.01, geometry);
    const wrapped = createWavyCrownPoint(0.37 + Math.PI * 2, 0.12, 0.01, geometry);
    expect(wrapped.x).toBeCloseTo(point.x);
    expect(wrapped.y).toBeCloseTo(point.y);
    expect(wrapped.z).toBeCloseTo(point.z);
  });
});
