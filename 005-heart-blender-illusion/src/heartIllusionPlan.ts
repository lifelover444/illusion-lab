export type ImplementationStatus = 'planning-only' | 'modeling-started';
export type IllusionSubject = 'heart' | 'mobius-heart-ring';

export interface HeartIllusionPlan {
  implementationStatus: ImplementationStatus;
  renderer: 'blender';
  subject: IllusionSubject;
  rotationAxis: 'vertical';
  cameraProjection: 'orthographic';
  rotationTiming: {
    cycleSeconds: number;
    totalSeconds: number;
    easing: 'linear';
  };
  recommendedGeometry: string[];
  directionLockingCues: string[];
  ambiguityPreservingCues: string[];
}

export const heartIllusionPlan: HeartIllusionPlan = {
  implementationStatus: 'modeling-started',
  renderer: 'blender',
  subject: 'mobius-heart-ring',
  rotationAxis: 'vertical',
  cameraProjection: 'orthographic',
  rotationTiming: {
    cycleSeconds: 6,
    totalSeconds: 12,
    easing: 'linear'
  },
  recommendedGeometry: [
    'continuous Mobius ribbon surface',
    'heart-shaped parametric centerline',
    'emissive rim curves',
    'semi-transparent double-sided surface'
  ],
  directionLockingCues: [
    'perspective camera',
    'cast shadow',
    'asymmetric texture',
    'glass refraction',
    'one-sided highlight',
    'different front and back colors'
  ],
  ambiguityPreservingCues: [
    'orthographic projection',
    'constant angular velocity',
    'matching front and back material',
    'semi-transparent ribbon surface',
    'visible continuous ribbon',
    'minimal symmetric lighting'
  ]
};

export const hasModelingStarted = (plan: HeartIllusionPlan = heartIllusionPlan): boolean =>
  plan.implementationStatus === 'modeling-started';

export const canSupportBistableRotation = (plan: HeartIllusionPlan = heartIllusionPlan): boolean =>
  plan.renderer === 'blender'
  && plan.subject === 'mobius-heart-ring'
  && plan.rotationAxis === 'vertical'
  && plan.cameraProjection === 'orthographic'
  && plan.rotationTiming.easing === 'linear'
  && plan.rotationTiming.totalSeconds / plan.rotationTiming.cycleSeconds === 2
  && plan.recommendedGeometry.includes('continuous Mobius ribbon surface')
  && plan.ambiguityPreservingCues.includes('matching front and back material');

export const cueLocksDirection = (cue: string, plan: HeartIllusionPlan = heartIllusionPlan): boolean =>
  plan.directionLockingCues.includes(cue);
