export type CrowStageLayoutInput = {
  sceneWidth: number;
  sceneHeight: number;
  maskWidth: number;
  maskHeight: number;
  edgeOffsetRatio: number;
};

export type CrowStageLayout = {
  scale: number;
  targetWidth: number;
  targetHeight: number;
  baseDrawX: number;
  drawX: number;
  drawY: number;
  reflectionTop: number;
  reflectionHeight: number;
  reflectionBottom: number;
};

export function getCrowStageLayout({
  sceneWidth,
  sceneHeight,
  maskWidth,
  maskHeight,
  edgeOffsetRatio
}: CrowStageLayoutInput): CrowStageLayout {
  const targetHeight = Math.min(sceneHeight * 0.52, sceneWidth * 1.04);
  const scale = targetHeight / maskHeight;
  const targetWidth = maskWidth * scale;
  const baseDrawX = (sceneWidth - targetWidth) / 2;
  const drawX = baseDrawX + sceneWidth * edgeOffsetRatio;
  const drawY = Math.max(44, sceneHeight * 0.075);
  const reflectionTop = drawY + targetHeight * 0.94;
  const reflectionHeight = targetHeight * 0.42;

  return {
    scale,
    targetWidth,
    targetHeight,
    baseDrawX,
    drawX,
    drawY,
    reflectionTop,
    reflectionHeight,
    reflectionBottom: reflectionTop + reflectionHeight
  };
}
