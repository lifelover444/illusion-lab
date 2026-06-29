export type SpherePoint = {
  x: number;
  y: number;
  z: number;
};

export const SPHERE_POINT_COUNT = 96;
export const LOOP_DURATION = 16;
export const ANGULAR_SPEED = (Math.PI * 2) / LOOP_DURATION;

const GOLDEN_ANGLE = Math.PI * (3 - Math.sqrt(5));

export function createFibonacciSphere(count = SPHERE_POINT_COUNT): SpherePoint[] {
  return Array.from({ length: count }, (_, index) => {
    const y = 1 - ((index + 0.5) / count) * 2;
    const radius = Math.sqrt(1 - y * y);
    const angle = index * GOLDEN_ANGLE;

    return {
      x: Math.cos(angle) * radius,
      y,
      z: Math.sin(angle) * radius
    };
  });
}
