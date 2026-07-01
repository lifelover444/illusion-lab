export const LOOP_DURATION = 7.2;
export const EYE_MAX_OPACITY = 0.58;
export const EDGE_DRIFT_RATIO = 0.018;
export const LOWER_OCCLUSION_RATIO = 0.045;
export const SHADOW_DRIFT_RATIO = 0.032;
export const SHADOW_EDGE_NARROWING = 0.16;

export type ContinuityCues = {
  edgeDriftRatio: number;
  lowerOcclusionRatio: number;
  shadowDriftRatio: number;
  shadowScaleX: number;
};

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

  return {
    angle,
    sideProjection: clampTrig(Math.cos(angle)),
    edgeProjection: clampTrig(Math.abs(Math.sin(angle)))
  };
}

export function getEyeOpacity(rotationRadians: number, visible = true) {
  if (!visible) {
    return 0;
  }

  const sideFacing = Math.abs(Math.cos(rotationRadians));
  return EYE_MAX_OPACITY * sideFacing * sideFacing * sideFacing;
}

export function getContinuityCues(rotationRadians: number): ContinuityCues {
  const edgeProjection = Math.abs(Math.sin(rotationRadians));
  const throughAxis = Math.sin(rotationRadians) * Math.pow(edgeProjection, 1.18);

  return {
    edgeDriftRatio: clampTrig(EDGE_DRIFT_RATIO * throughAxis),
    lowerOcclusionRatio: clampTrig(LOWER_OCCLUSION_RATIO * throughAxis),
    shadowDriftRatio: clampTrig(SHADOW_DRIFT_RATIO * throughAxis),
    shadowScaleX: clampTrig(1 - SHADOW_EDGE_NARROWING * edgeProjection)
  };
}
