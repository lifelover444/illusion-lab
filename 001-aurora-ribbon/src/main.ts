import './styles.css';
import * as THREE from 'three';
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js';
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js';
import { createRibbonSurface } from './ribbon';

const canvas = document.querySelector<HTMLCanvasElement>('#scene');

if (!canvas) {
  throw new Error('Scene canvas is missing');
}

const renderer = new THREE.WebGLRenderer({
  canvas,
  antialias: true,
  alpha: false,
  powerPreference: 'high-performance'
});
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setClearColor(0x08080a, 1);

const scene = new THREE.Scene();
scene.fog = new THREE.FogExp2(0x08080a, 0.055);

const camera = new THREE.OrthographicCamera(-4, 4, 3, -3, 0.1, 80);
camera.position.set(0, 0.24, 8);
camera.lookAt(0, 0, 0);

const ribbonGroup = new THREE.Group();
scene.add(ribbonGroup);

const clock = new THREE.Clock();
const pointer = new THREE.Vector2(0, 0);

const auroraMaterial = new THREE.ShaderMaterial({
  transparent: true,
  depthWrite: false,
  depthTest: false,
  side: THREE.DoubleSide,
  blending: THREE.AdditiveBlending,
  uniforms: {
    uTime: { value: 0 },
    uOpacity: { value: 0.38 }
  },
  vertexShader: `
    varying vec3 vWorldPosition;
    varying vec3 vLocalPosition;

    void main() {
      vLocalPosition = position;
      vec4 worldPosition = modelMatrix * vec4(position, 1.0);
      vWorldPosition = worldPosition.xyz;
      gl_Position = projectionMatrix * viewMatrix * worldPosition;
    }
  `,
  fragmentShader: `
    precision highp float;

    uniform float uTime;
    uniform float uOpacity;
    varying vec3 vWorldPosition;
    varying vec3 vLocalPosition;

    vec3 palette(float t) {
      vec3 jade = vec3(0.08, 0.95, 0.76);
      vec3 violet = vec3(0.82, 0.36, 1.0);
      vec3 gold = vec3(1.0, 0.73, 0.34);
      vec3 blue = vec3(0.18, 0.38, 1.0);
      vec3 first = mix(jade, violet, smoothstep(-0.55, 0.7, sin(t)));
      vec3 second = mix(gold, blue, smoothstep(-0.35, 0.85, cos(t * 0.67)));
      return mix(first, second, 0.34 + 0.24 * sin(t * 1.7));
    }

    void main() {
      float flow = vLocalPosition.x * 1.55 + vLocalPosition.y * 2.3 + uTime * 0.55;
      float veil = 0.5 + 0.5 * sin(flow);
      float edge = smoothstep(0.04, 0.94, abs(sin(vLocalPosition.z * 2.1 + uTime * 0.34)));
      float verticalFade = smoothstep(-1.15, -0.05, vLocalPosition.y) * (1.0 - smoothstep(0.65, 1.5, vLocalPosition.y));
      vec3 color = palette(flow) * (0.56 + veil * 0.7 + edge * 0.24);
      float alpha = uOpacity * verticalFade * (0.24 + veil * 0.4 + edge * 0.22);
      gl_FragColor = vec4(color, alpha);
    }
  `
});

const surface = createRibbonSurface({
  radialSegments: 196,
  strands: 5,
  widthSegments: 8,
  radius: 1.95,
  ribbonWidth: 0.5,
  twist: 1.24,
  verticalDrift: 0.64
});

const ribbonGeometry = new THREE.BufferGeometry();
ribbonGeometry.setAttribute('position', new THREE.BufferAttribute(surface.positions, 3));
ribbonGeometry.setIndex(new THREE.BufferAttribute(surface.indices, 1));
ribbonGeometry.computeBoundingSphere();

const ribbon = new THREE.Mesh(ribbonGeometry, auroraMaterial);
ribbon.rotation.x = -0.11;
ribbonGroup.add(ribbon);

const haloMaterial = new THREE.LineBasicMaterial({
  color: 0xb9fff1,
  transparent: true,
  opacity: 0.16,
  blending: THREE.AdditiveBlending,
  depthTest: false,
  depthWrite: false
});
const halo = new THREE.LineSegments(new THREE.EdgesGeometry(ribbonGeometry, 26), haloMaterial);
halo.rotation.copy(ribbon.rotation);
ribbonGroup.add(halo);

const innerGlow = new THREE.Mesh(
  new THREE.TorusGeometry(1.08, 0.014, 12, 220),
  new THREE.MeshBasicMaterial({
    color: 0xffd98c,
    transparent: true,
    opacity: 0.14,
    blending: THREE.AdditiveBlending,
    depthTest: false,
    depthWrite: false
  })
);
innerGlow.scale.set(1, 0.36, 1);
innerGlow.rotation.x = Math.PI * 0.5;
ribbonGroup.add(innerGlow);

function createParticleField(count: number) {
  const positions = new Float32Array(count * 3);
  const colors = new Float32Array(count * 3);
  const palette = [
    new THREE.Color(0x6fffe6),
    new THREE.Color(0xb869ff),
    new THREE.Color(0xffcc73)
  ];

  for (let index = 0; index < count; index += 1) {
    const radius = 2.6 + Math.random() * 2.8;
    const angle = Math.random() * Math.PI * 2;
    const y = (Math.random() - 0.5) * 3.2;
    positions[index * 3] = Math.cos(angle) * radius;
    positions[index * 3 + 1] = y;
    positions[index * 3 + 2] = Math.sin(angle) * radius - 1.2;

    const color = palette[index % palette.length].clone().lerp(new THREE.Color(0xffffff), Math.random() * 0.22);
    colors[index * 3] = color.r;
    colors[index * 3 + 1] = color.g;
    colors[index * 3 + 2] = color.b;
  }

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
  geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));

  return new THREE.Points(
    geometry,
    new THREE.PointsMaterial({
      size: 0.025,
      vertexColors: true,
      transparent: true,
      opacity: 0.42,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      depthTest: false
    })
  );
}

const particles = createParticleField(520);
scene.add(particles);

const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, camera));
composer.addPass(new UnrealBloomPass(new THREE.Vector2(1, 1), 0.52, 0.72, 0.16));

function resize() {
  const width = window.innerWidth;
  const height = window.innerHeight;
  const aspect = width / height;
  const frustumHeight = width < 720 ? 6.25 : 5.65;
  camera.left = (-frustumHeight * aspect) / 2;
  camera.right = (frustumHeight * aspect) / 2;
  camera.top = frustumHeight / 2;
  camera.bottom = -frustumHeight / 2;
  camera.updateProjectionMatrix();
  renderer.setSize(width, height, false);
  composer.setSize(width, height);

  if (width < 720) {
    ribbonGroup.position.set(0, -0.88, 0);
    ribbonGroup.scale.setScalar(0.64);
  } else {
    ribbonGroup.position.set(0, -0.62, 0);
    ribbonGroup.scale.setScalar(0.92);
  }
}

function animate() {
  const elapsed = clock.getElapsedTime();
  auroraMaterial.uniforms.uTime.value = elapsed;

  ribbonGroup.rotation.y = elapsed * 0.34;
  ribbonGroup.rotation.z = Math.sin(elapsed * 0.22) * 0.035 + pointer.x * 0.045;
  ribbonGroup.rotation.x = pointer.y * 0.045;

  innerGlow.rotation.z = -elapsed * 0.18;
  particles.rotation.y = -elapsed * 0.025;
  particles.rotation.z = Math.sin(elapsed * 0.13) * 0.02;

  composer.render();
  window.requestAnimationFrame(animate);
}

window.addEventListener('resize', resize);
window.addEventListener('pointermove', (event) => {
  pointer.x = (event.clientX / window.innerWidth - 0.5) * 2;
  pointer.y = -(event.clientY / window.innerHeight - 0.5) * 2;
});

resize();
animate();
