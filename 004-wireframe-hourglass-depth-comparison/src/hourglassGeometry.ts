export type Vec3 = [number, number, number];

export type EdgeRole = 'rim' | 'strut';
export type FaceRole = 'side' | 'cap';
export type RotationDirection = 'clockwise' | 'counterclockwise' | 'ambiguous';
export type ComparisonRole = 'illusion' | 'depth-control';
export type DepthCue = 'wireframe-only' | 'solid-color';

export interface HourglassGeometryConfig {
  sides: number;
  baseRadius: number;
  pyramidHeight: number;
  maxApexSeparation: number;
  topPhaseDegrees: number;
  bottomPhaseDegrees: number;
}

export interface HourglassEdge {
  from: number;
  to: number;
  role: EdgeRole;
  label: string;
}

export interface HourglassFace {
  vertices: number[];
  role: FaceRole;
  label: string;
}

export interface HourglassGeometry {
  vertices: Vec3[];
  edges: HourglassEdge[];
  faces: HourglassFace[];
}

export interface HourglassLayoutConfig {
  leftXOffset: number;
  centerXOffset: number;
  rightXOffset: number;
  groupScale: number;
}

export interface HourglassControlConfig {
  id: string;
  xOffset: number;
  perceivedDirection: string;
  rotationSign: number;
  depthInterpretationSign: number;
}

export interface HourglassComparisonConfig {
  geometry: HourglassGeometryConfig;
  layout: HourglassLayoutConfig;
  controls: HourglassControlConfig[];
}

export interface HourglassRenderProfile {
  width: number;
  height: number;
  fps: number;
  seconds: number;
  samples: number;
  output: string;
}

export interface HourglassStyleConfig {
  rotationCycleSeconds: number;
}

export interface HourglassMotionConfig extends HourglassComparisonConfig {
  profiles: Record<string, HourglassRenderProfile>;
  style: HourglassStyleConfig;
}

export interface HourglassComparisonGroup {
  id: string;
  role: ComparisonRole;
  depthCue: DepthCue;
  xOffset: number;
  scale: number;
  rotationSign: -1 | 0 | 1;
  perceivedDirection: RotationDirection;
  depthInterpretationSign: -1 | 0 | 1;
  topRotationDirection: RotationDirection;
  bottomRotationDirection: RotationDirection;
  geometry: HourglassGeometry;
}

export interface GapKeyframe {
  frame: number;
  apexSeparation: number;
}

export interface HourglassMotionPlan {
  groupId: string;
  durationSeconds: number;
  durationFrames: number;
  startFrame: number;
  midpointFrame: number;
  endFrame: number;
  loopFrame: number;
  rotationSign: -1 | 0 | 1;
  rotationDegrees: number;
  absoluteRotationDegrees: number;
  rotationDegreesPerSecond: number;
  gapKeyframes: GapKeyframe[];
}

const parseControlDirection = (value: string): Exclude<RotationDirection, 'ambiguous'> => {
  if (value === 'clockwise' || value === 'counterclockwise') {
    return value;
  }

  throw new Error(`Unsupported control rotation direction: ${value}`);
};

const parseRotationSign = (value: number): -1 | 1 => {
  if (value === -1 || value === 1) {
    return value;
  }

  throw new Error(`Unsupported control rotation sign: ${value}`);
};

const parseDepthInterpretationSign = (value: number): -1 | 1 => {
  if (value === -1 || value === 1) {
    return value;
  }

  throw new Error(`Unsupported depth interpretation sign: ${value}`);
};

const degreesToRadians = (degrees: number): number => degrees * Math.PI / 180;

const createRing = (
  sides: number,
  radius: number,
  z: number,
  phaseDegrees: number
): Vec3[] => {
  const phase = degreesToRadians(phaseDegrees);

  return Array.from({ length: sides }, (_, index) => {
    const angle = phase + index * Math.PI * 2 / sides;
    return [
      radius * Math.cos(angle),
      radius * Math.sin(angle),
      z
    ];
  });
};

const addRingEdges = (
  edges: HourglassEdge[],
  start: number,
  sides: number,
  label: string
): void => {
  for (let index = 0; index < sides; index += 1) {
    edges.push({
      from: start + index,
      to: start + ((index + 1) % sides),
      role: 'rim',
      label: `${label}-${index}`
    });
  }
};

export const createHourglassGeometry = (
  config: HourglassGeometryConfig
): HourglassGeometry => {
  const topApex: Vec3 = [0, 0, 0];
  const bottomApex: Vec3 = [0, 0, 0];
  const topRing = createRing(config.sides, config.baseRadius, config.pyramidHeight, config.topPhaseDegrees);
  const bottomRing = createRing(config.sides, config.baseRadius, -config.pyramidHeight, config.bottomPhaseDegrees);
  const vertices = [topApex, ...topRing, bottomApex, ...bottomRing];
  const topApexIndex = 0;
  const topStart = 1;
  const bottomApexIndex = config.sides + 1;
  const bottomStart = bottomApexIndex + 1;
  const edges: HourglassEdge[] = [];

  addRingEdges(edges, topStart, config.sides, 'top-rim');
  addRingEdges(edges, bottomStart, config.sides, 'bottom-rim');
  for (let index = 0; index < config.sides; index += 1) {
    edges.push({
      from: topStart + index,
      to: topApexIndex,
      role: 'strut',
      label: `top-to-apex-${index}`
    });
    edges.push({
      from: bottomStart + index,
      to: bottomApexIndex,
      role: 'strut',
      label: `bottom-to-apex-${index}`
    });
  }

  return {
    vertices,
    edges,
    faces: []
  };
};

export const createSolidHourglassGeometry = (
  config: HourglassGeometryConfig
): HourglassGeometry => {
  const geometry = createHourglassGeometry(config);
  const topApexIndex = 0;
  const topStart = 1;
  const bottomApexIndex = config.sides + 1;
  const bottomStart = bottomApexIndex + 1;
  const faces: HourglassFace[] = [];

  for (let index = 0; index < config.sides; index += 1) {
    const nextIndex = (index + 1) % config.sides;

    faces.push({
      vertices: [topApexIndex, topStart + nextIndex, topStart + index],
      role: 'side',
      label: `top-side-${index}`
    });
    faces.push({
      vertices: [bottomApexIndex, bottomStart + index, bottomStart + nextIndex],
      role: 'side',
      label: `bottom-side-${index}`
    });
  }

  faces.push({
    vertices: Array.from({ length: config.sides }, (_, index) => topStart + index),
    role: 'cap',
    label: 'top-base-cap'
  });
  faces.push({
    vertices: Array.from({ length: config.sides }, (_, index) => bottomStart + config.sides - 1 - index),
    role: 'cap',
    label: 'bottom-base-cap'
  });

  return {
    ...geometry,
    faces
  };
};

export const createHourglassComparison = (
  config: HourglassComparisonConfig
): HourglassComparisonGroup[] => {
  const leftControl = config.controls.find((control) => control.id === 'left-clockwise-depth-control');
  const rightControl = config.controls.find((control) => control.id === 'right-counterclockwise-depth-control');

  if (!leftControl || !rightControl) {
    throw new Error('Expected left and right depth control configuration.');
  }

  const createControlGroup = (control: HourglassControlConfig): HourglassComparisonGroup => {
    const perceivedDirection = parseControlDirection(control.perceivedDirection);
    const rotationSign = parseRotationSign(control.rotationSign);
    const depthInterpretationSign = parseDepthInterpretationSign(control.depthInterpretationSign);

    return {
      id: control.id,
      role: 'depth-control',
      depthCue: 'solid-color',
      xOffset: control.xOffset,
      scale: config.layout.groupScale,
      rotationSign,
      perceivedDirection,
      depthInterpretationSign,
      topRotationDirection: perceivedDirection,
      bottomRotationDirection: perceivedDirection,
      geometry: createSolidHourglassGeometry(config.geometry)
    };
  };

  return [
    createControlGroup(leftControl),
    {
      id: 'center-wireframe-illusion',
      role: 'illusion',
      depthCue: 'wireframe-only',
      xOffset: config.layout.centerXOffset,
      scale: config.layout.groupScale,
      rotationSign: 1,
      perceivedDirection: 'ambiguous',
      depthInterpretationSign: 0,
      topRotationDirection: 'ambiguous',
      bottomRotationDirection: 'ambiguous',
      geometry: createHourglassGeometry(config.geometry)
    },
    createControlGroup(rightControl)
  ];
};

export const createSynchronizedMotionPlans = (
  config: HourglassMotionConfig,
  profileName: string
): HourglassMotionPlan[] => {
  const profile = config.profiles[profileName];

  if (!profile) {
    throw new Error(`Unknown render profile: ${profileName}`);
  }

  const startFrame = 1;
  const durationFrames = profile.fps * profile.seconds;
  const endFrame = durationFrames;
  const loopFrame = endFrame + 1;
  const midpointFrame = startFrame + profile.fps * config.style.rotationCycleSeconds;
  const rotationCycles = profile.seconds / config.style.rotationCycleSeconds;
  const absoluteRotationDegrees = rotationCycles * 360;
  const gapKeyframes: GapKeyframe[] = [
    { frame: startFrame, apexSeparation: 0 },
    { frame: midpointFrame, apexSeparation: config.geometry.maxApexSeparation },
    { frame: loopFrame, apexSeparation: 0 }
  ];

  return createHourglassComparison(config).map((group) => {
    const rotationDegrees = group.rotationSign * absoluteRotationDegrees;

    return {
      groupId: group.id,
      durationSeconds: profile.seconds,
      durationFrames,
      startFrame,
      midpointFrame,
      endFrame,
      loopFrame,
      rotationSign: group.rotationSign,
      rotationDegrees,
      absoluteRotationDegrees,
      rotationDegreesPerSecond: rotationDegrees / profile.seconds,
      gapKeyframes
    };
  });
};
