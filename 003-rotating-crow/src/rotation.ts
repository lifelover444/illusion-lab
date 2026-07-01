export const LOOP_DURATION = 7.2;
export const EYE_MAX_OPACITY = 0.72;
export const EDGE_OFFSET_RATIO = 0.015;

function clampTrig(value: number) {
  if (Math.abs(value) < 1e-12) {
    return 0;
  }

  if (Math.abs(value - 1) < 1e-12) {
    return 1;
  }

  if (Math.abs(value + 1) < 1e-12) {
    return -1;
  }

  return Number(value.toFixed(12));
}

export function getLoopRotation(elapsedSeconds: number, loopDuration = LOOP_DURATION) {
  const wrappedTime = ((elapsedSeconds % loopDuration) + loopDuration) % loopDuration;
  return (wrappedTime / loopDuration) * Math.PI * 2;
}

export function getAmbiguousProjection(elapsedSeconds: number, loopDuration = LOOP_DURATION) {
  const angle = getLoopRotation(elapsedSeconds, loopDuration);
  const edgeProjection = clampTrig(Math.abs(Math.sin(angle)));
  const depthPhase = clampTrig(Math.sin(angle) * edgeProjection);

  return {
    angle,
    sideProjection: clampTrig(Math.cos(angle)),
    edgeProjection,
    depthPhase,
    edgeOffsetRatio: clampTrig(depthPhase * EDGE_OFFSET_RATIO)
  };
}

export function getEyeOpacity(rotationRadians: number, visible = true) {
  if (!visible) {
    return 0;
  }

  const sideFacing = Math.abs(Math.cos(rotationRadians));
  return EYE_MAX_OPACITY * sideFacing * sideFacing * sideFacing;
}
