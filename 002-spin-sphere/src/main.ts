import './styles.css';
import * as THREE from 'three';
import { ANGULAR_SPEED, LOOP_DURATION, createFibonacciSphere } from './sphere';

const FRUSTUM_HEIGHT = 4.35;
const POINT_SIZE = 18;
const DOT_COLOR = new THREE.Color('#a0e8ff');

const canvas = document.querySelector<HTMLCanvasElement>('#scene');

if (!canvas) {
  throw new Error('Scene canvas is missing');
}

const sceneCanvas = canvas;

const renderer = new THREE.WebGLRenderer({
  canvas: sceneCanvas,
  antialias: true,
  alpha: true,
  preserveDrawingBuffer: true,
  powerPreference: 'high-performance'
});
renderer.setClearColor(0x000000, 0);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

const scene = new THREE.Scene();
const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 10);
camera.position.set(0, 0, 4);
camera.lookAt(0, 0, 0);

const spherePoints = createFibonacciSphere();
const spherePositions = new Float32Array(spherePoints.length * 3);
spherePoints.forEach((point, index) => {
  spherePositions[index * 3] = point.x;
  spherePositions[index * 3 + 1] = point.y;
  spherePositions[index * 3 + 2] = point.z;
});

const geometry = new THREE.BufferGeometry();
geometry.setAttribute('position', new THREE.BufferAttribute(spherePositions, 3));
geometry.computeBoundingSphere();

const material = new THREE.ShaderMaterial({
  transparent: true,
  depthTest: false,
  depthWrite: false,
  uniforms: {
    uColor: { value: DOT_COLOR },
    uPointSize: { value: POINT_SIZE * renderer.getPixelRatio() }
  },
  vertexShader: `
    uniform float uPointSize;

    void main() {
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      gl_PointSize = uPointSize;
    }
  `,
  fragmentShader: `
    precision highp float;

    uniform vec3 uColor;

    void main() {
      vec2 point = gl_PointCoord - vec2(0.5);
      float radius = length(point) * 2.0;

      if (radius > 1.0) {
        discard;
      }

      float core = smoothstep(0.48, 0.38, radius);
      float halo = smoothstep(1.0, 0.16, radius) * 0.34;
      float alpha = max(core * 0.86, halo);

      gl_FragColor = vec4(uColor, alpha);
    }
  `
});

const points = new THREE.Points(geometry, material);
points.frustumCulled = false;
scene.add(points);

let startTimestamp: number | null = null;
let paused = false;
let pauseStartedAt = 0;
let accumulatedPausedTime = 0;

function resize() {
  const width = Math.max(1, sceneCanvas.clientWidth);
  const height = Math.max(1, sceneCanvas.clientHeight);
  const aspect = width / height;

  camera.left = (-FRUSTUM_HEIGHT * aspect) / 2;
  camera.right = (FRUSTUM_HEIGHT * aspect) / 2;
  camera.top = FRUSTUM_HEIGHT / 2;
  camera.bottom = -FRUSTUM_HEIGHT / 2;
  camera.updateProjectionMatrix();

  renderer.setSize(width, height, false);
  material.uniforms.uPointSize.value = POINT_SIZE * renderer.getPixelRatio();
}

function getSimulationTime(timestamp: number) {
  if (startTimestamp === null) {
    startTimestamp = timestamp;
  }

  const activeTimestamp = paused ? pauseStartedAt : timestamp;
  const elapsed = (activeTimestamp - startTimestamp - accumulatedPausedTime) / 1000;
  return ((elapsed % LOOP_DURATION) + LOOP_DURATION) % LOOP_DURATION;
}

function animate(timestamp: number) {
  const simulationTime = getSimulationTime(timestamp);
  points.rotation.y = simulationTime * ANGULAR_SPEED;

  renderer.render(scene, camera);
  window.requestAnimationFrame(animate);
}

function togglePause() {
  const now = performance.now();

  if (paused) {
    accumulatedPausedTime += now - pauseStartedAt;
    paused = false;
    return;
  }

  pauseStartedAt = now;
  paused = true;
}

window.addEventListener('resize', resize);
window.addEventListener('pointerdown', togglePause);

resize();
window.requestAnimationFrame(animate);
