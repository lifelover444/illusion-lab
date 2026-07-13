export type WavyCrownGeometry = {
  majorRadius: number;
  bandHalfWidth: number;
  bandHalfThickness: number;
  waveCount: number;
  waveHeight: number;
  wavePhase: number;
};

export type Point3 = {
  x: number;
  y: number;
  z: number;
};

export function crownCenterHeight(
  majorAngle: number,
  geometry: WavyCrownGeometry
): number {
  return geometry.waveHeight * Math.cos(
    geometry.waveCount * majorAngle + geometry.wavePhase
  );
}

export function createWavyCrownPoint(
  majorAngle: number,
  radialOffset: number,
  thicknessOffset: number,
  geometry: WavyCrownGeometry
): Point3 {
  const radialDistance = geometry.majorRadius + radialOffset;
  return {
    x: radialDistance * Math.cos(majorAngle),
    y: radialDistance * Math.sin(majorAngle),
    z: crownCenterHeight(majorAngle, geometry) + thicknessOffset
  };
}

export function minimumHoleRadius(geometry: WavyCrownGeometry): number {
  return geometry.majorRadius - geometry.bandHalfWidth;
}

export function maximumOuterRadius(geometry: WavyCrownGeometry): number {
  return geometry.majorRadius + geometry.bandHalfWidth;
}
