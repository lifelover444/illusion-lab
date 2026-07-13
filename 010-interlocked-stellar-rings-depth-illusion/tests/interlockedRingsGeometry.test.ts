import { describe, expect, it } from 'vitest';

import {
  presentPoint,
  ringCenterlinePoint,
  ringSurfacePoint,
  type InterlockedRingsGeometry,
  type RingId
} from '../src/interlockedRingsGeometry';

const geometry: InterlockedRingsGeometry = {
  ringRadius: 1,
  centerOffset: 0.62,
  tubeHalfWidth: 0.068,
  tubeHalfThickness: 0.033
};

describe('interlocked stellar rings geometry', () => {
  it('places the two equal rings in perpendicular planes', () => {
    const aQuarter = ringCenterlinePoint('a', Math.PI / 2, geometry);
    const bQuarter = ringCenterlinePoint('b', Math.PI / 2, geometry);
    expect(aQuarter.z).toBeCloseTo(0);
    expect(bQuarter.y).toBeCloseTo(0);
    expect(aQuarter.y).toBeCloseTo(geometry.ringRadius);
    expect(bQuarter.z).toBeCloseTo(geometry.ringRadius);
  });

  it('keeps both centerlines closed', () => {
    for (const ring of ['a', 'b'] as RingId[]) {
      const start = ringCenterlinePoint(ring, 0.31, geometry);
      const wrapped = ringCenterlinePoint(ring, 0.31 + Math.PI * 2, geometry);
      expect(wrapped.x).toBeCloseTo(start.x);
      expect(wrapped.y).toBeCloseTo(start.y);
      expect(wrapped.z).toBeCloseTo(start.z);
    }
  });

  it('uses a flattened elliptical tube cross-section', () => {
    const center = ringCenterlinePoint('a', 0, geometry);
    const wide = ringSurfacePoint('a', 0, 0, geometry);
    const thick = ringSurfacePoint('a', 0, Math.PI / 2, geometry);
    expect(wide.x - center.x).toBeCloseTo(geometry.tubeHalfWidth);
    expect(thick.z - center.z).toBeCloseTo(geometry.tubeHalfThickness);
    expect(geometry.tubeHalfWidth / geometry.tubeHalfThickness).toBeGreaterThan(2);
  });

  it('leaves ample physical clearance between the two ring tubes', () => {
    expect(geometry.centerOffset).toBeGreaterThan(geometry.tubeHalfWidth * 4);
  });

  it('preserves distance when applying the presentation rotation', () => {
    const source = ringSurfacePoint('b', 0.74, 2.1, geometry);
    const shown = presentPoint(source, Math.PI / 4, Math.PI / 10, 0);
    const sourceLength = Math.hypot(source.x, source.y, source.z);
    const shownLength = Math.hypot(shown.x, shown.y, shown.z);
    expect(shownLength).toBeCloseTo(sourceLength);
  });
});
