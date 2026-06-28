export type RibbonSurfaceOptions = {
  radialSegments: number;
  strands: number;
  widthSegments: number;
  radius: number;
  ribbonWidth: number;
  twist: number;
  verticalDrift: number;
};

export type RibbonSurface = {
  positions: Float32Array;
  indices: Uint32Array;
  strandAnchors: number[];
};

export function createRibbonSurface(options: RibbonSurfaceOptions): RibbonSurface {
  const { radialSegments, strands, widthSegments, radius, ribbonWidth, twist, verticalDrift } = options;
  const positions = new Float32Array(radialSegments * strands * widthSegments * 3);
  const indices = new Uint32Array(radialSegments * strands * (widthSegments - 1) * 6);
  const strandAnchors = Array.from({ length: strands }, (_, strand) => (strand / strands) * Math.PI * 2);

  let positionOffset = 0;
  let indexOffset = 0;

  for (let strand = 0; strand < strands; strand += 1) {
    const phase = strandAnchors[strand];
    const strandBase = strand * radialSegments * widthSegments;

    for (let radial = 0; radial < radialSegments; radial += 1) {
      const angle = (radial / radialSegments) * Math.PI * 2 + phase;
      const pulse = Math.sin(angle * 3 + phase * 0.7) * 0.14;
      const ringRadius = radius + pulse;
      const centerX = Math.cos(angle) * ringRadius;
      const centerZ = Math.sin(angle) * ringRadius;
      const centerY = Math.sin(angle * 2 + phase * 0.35) * verticalDrift;
      const twistAngle = angle * twist + phase * 0.5;
      const radialX = Math.cos(angle);
      const radialZ = Math.sin(angle);
      const radialWeight = Math.sin(twistAngle) * 0.55;
      const verticalWeight = Math.cos(twistAngle) * 0.85;

      for (let width = 0; width < widthSegments; width += 1) {
        const centeredWidth = widthSegments === 1 ? 0 : width / (widthSegments - 1) - 0.5;
        const bandOffset = centeredWidth * ribbonWidth;

        positions[positionOffset] = centerX + radialX * radialWeight * bandOffset;
        positions[positionOffset + 1] = centerY + verticalWeight * bandOffset;
        positions[positionOffset + 2] = centerZ + radialZ * radialWeight * bandOffset;
        positionOffset += 3;
      }
    }

    for (let radial = 0; radial < radialSegments; radial += 1) {
      const nextRadial = (radial + 1) % radialSegments;

      for (let width = 0; width < widthSegments - 1; width += 1) {
        const v00 = strandBase + radial * widthSegments + width;
        const v01 = v00 + 1;
        const v10 = strandBase + nextRadial * widthSegments + width;
        const v11 = v10 + 1;

        indices[indexOffset] = v00;
        indices[indexOffset + 1] = v10;
        indices[indexOffset + 2] = v01;
        indices[indexOffset + 3] = v10;
        indices[indexOffset + 4] = v11;
        indices[indexOffset + 5] = v01;
        indexOffset += 6;
      }
    }
  }

  return {
    positions,
    indices,
    strandAnchors
  };
}
