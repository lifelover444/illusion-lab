import './styles.css';
import {
  createCrowProjectionRows,
  projectCrowRow,
  type CrowProjectionRows
} from './crow';
import { getAmbiguousProjection, getEyeOpacity } from './rotation';

const CROW_IMAGE_URL = new URL('../assets/crow.png', import.meta.url).href;
const MASK_THRESHOLD = 112;
const MASK_PADDING = 18;
const PROFILE_WIDTH_RATIO = 0.17;
const EYE_IMAGE_POSITION = { x: 385, y: 183 };

type ProjectionMask = {
  rows: CrowProjectionRows;
  canvas: HTMLCanvasElement;
  context: CanvasRenderingContext2D;
  cropX: number;
  cropY: number;
  eyeX: number;
  eyeY: number;
};

function requireElement<T extends Element>(selector: string) {
  const element = document.querySelector<T>(selector);

  if (!element) {
    throw new Error(`Missing required element: ${selector}`);
  }

  return element;
}

const stage = requireElement<HTMLElement>('.stage');
const sceneCanvas = requireElement<HTMLCanvasElement>('#scene');
const prompt = requireElement<HTMLParagraphElement>('.prompt');
const speedInput = requireElement<HTMLInputElement>('#speed');
const speedValue = requireElement<HTMLOutputElement>('#speed-value');
const spotInput = requireElement<HTMLInputElement>('#spot');
const eyeInput = requireElement<HTMLInputElement>('#eye');
const pauseButton = requireElement<HTMLButtonElement>('#pause');

const rawSceneContext = sceneCanvas.getContext('2d', { alpha: true });

if (!rawSceneContext) {
  throw new Error('Canvas 2D context is unavailable');
}

const sceneContext: CanvasRenderingContext2D = rawSceneContext;

let projectionMask: ProjectionMask | null = null;
let elapsedSeconds = 0;
let previousTimestamp: number | null = null;
let paused = false;
let speedMultiplier = Number(speedInput.value);
let showEye = eyeInput.checked;
let pixelRatio = 1;

const initialParams = new URLSearchParams(window.location.search);
const initialTime = Number(initialParams.get('t'));

if (Number.isFinite(initialTime)) {
  elapsedSeconds = initialTime;
}

function loadImage(url: string) {
  return new Promise<HTMLImageElement>((resolve, reject) => {
    const image = new Image();
    image.decoding = 'async';
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error(`Could not load image: ${url}`));
    image.src = url;
  });
}

function readImageData(image: HTMLImageElement) {
  const canvas = document.createElement('canvas');
  canvas.width = image.naturalWidth;
  canvas.height = image.naturalHeight;

  const context = canvas.getContext('2d', { willReadFrequently: true });

  if (!context) {
    throw new Error('Canvas 2D context is unavailable');
  }

  context.drawImage(image, 0, 0);
  return context.getImageData(0, 0, canvas.width, canvas.height);
}

function createProjectionMask(imageData: ImageData): ProjectionMask {
  const rows = createCrowProjectionRows(imageData, {
    threshold: MASK_THRESHOLD,
    profileWidthRatio: PROFILE_WIDTH_RATIO
  });
  const cropX = Math.max(0, rows.bounds.minX - MASK_PADDING);
  const cropY = Math.max(0, rows.bounds.minY - MASK_PADDING);
  const cropRight = Math.min(imageData.width - 1, rows.bounds.maxX + MASK_PADDING);
  const cropBottom = Math.min(imageData.height - 1, rows.bounds.maxY + MASK_PADDING);
  const canvas = document.createElement('canvas');
  canvas.width = cropRight - cropX + 1;
  canvas.height = cropBottom - cropY + 1;

  const context = canvas.getContext('2d', { alpha: true });

  if (!context) {
    throw new Error('Canvas 2D context is unavailable');
  }

  return {
    rows,
    canvas,
    context,
    cropX,
    cropY,
    eyeX: EYE_IMAGE_POSITION.x - cropX,
    eyeY: EYE_IMAGE_POSITION.y - cropY
  };
}

function resize() {
  const width = Math.max(1, sceneCanvas.clientWidth);
  const height = Math.max(1, sceneCanvas.clientHeight);
  pixelRatio = Math.min(window.devicePixelRatio, 2);

  sceneCanvas.width = Math.round(width * pixelRatio);
  sceneCanvas.height = Math.round(height * pixelRatio);
  sceneContext.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
  render();
}

function drawProjectionMask(mask: ProjectionMask) {
  const projection = getAmbiguousProjection(elapsedSeconds);
  const { context } = mask;
  const spanY = Math.max(1, mask.rows.bounds.maxY - mask.rows.bounds.minY);

  context.clearRect(0, 0, mask.canvas.width, mask.canvas.height);
  context.fillStyle = '#000000';

  for (const row of mask.rows.rows) {
    const projected = projectCrowRow(row, projection, mask.rows.axisX, {
      verticalPosition: (row.y - mask.rows.bounds.minY) / spanY
    });
    const left = projected.left - mask.cropX;
    const y = row.y - mask.cropY;

    if (projected.width <= 0) {
      continue;
    }

    context.fillRect(left, y, projected.width, 1.2);
  }

  return projection;
}

function drawGroundShadow(
  projection: ReturnType<typeof getAmbiguousProjection>,
  baseDrawX: number,
  drawY: number,
  targetWidth: number,
  targetHeight: number,
  sceneWidth: number
) {
  const centerX = baseDrawX + targetWidth / 2 + sceneWidth * projection.edgeOffsetRatio * 0.8;
  const centerY = drawY + targetHeight * 0.92;
  const radiusX = targetWidth * (0.28 - projection.edgeProjection * 0.045);
  const radiusY = targetHeight * (0.026 + projection.edgeProjection * 0.004);

  sceneContext.save();
  sceneContext.filter = `blur(${Math.max(5, targetHeight * 0.014)}px)`;
  sceneContext.fillStyle = 'rgba(0, 0, 0, 0.14)';
  sceneContext.beginPath();
  sceneContext.ellipse(centerX, centerY, radiusX, radiusY, 0, 0, Math.PI * 2);
  sceneContext.fill();
  sceneContext.restore();
}

function drawEye(mask: ProjectionMask, scale: number, drawX: number, drawY: number) {
  const projection = getAmbiguousProjection(elapsedSeconds);
  const opacity = getEyeOpacity(projection.angle, showEye) * 0.62;

  if (opacity <= 0.01) {
    return;
  }

  const projectedEyeX =
    mask.rows.axisX + (EYE_IMAGE_POSITION.x - mask.rows.axisX) * projection.sideProjection - mask.cropX;
  const x = drawX + projectedEyeX * scale;
  const y = drawY + mask.eyeY * scale;
  const radiusX = Math.max(4, scale * 11.5);
  const radiusY = Math.max(5, scale * 14.5);

  sceneContext.save();
  sceneContext.globalAlpha = opacity;
  sceneContext.strokeStyle = '#f5f5ee';
  sceneContext.lineWidth = Math.max(2, scale * 4);
  sceneContext.beginPath();
  sceneContext.ellipse(x, y, radiusX, radiusY, 0, 0, Math.PI * 2);
  sceneContext.stroke();
  sceneContext.restore();
}

function render() {
  const width = sceneCanvas.clientWidth;
  const height = sceneCanvas.clientHeight;

  sceneContext.clearRect(0, 0, width, height);

  if (!projectionMask) {
    return;
  }

  const projection = drawProjectionMask(projectionMask);

  const targetHeight = Math.min(height * 0.58, width * 1.16);
  const scale = targetHeight / projectionMask.canvas.height;
  const targetWidth = projectionMask.canvas.width * scale;
  const baseDrawX = (width - targetWidth) / 2;
  const drawX = baseDrawX + width * projection.edgeOffsetRatio;
  const drawY = Math.max(64, height * 0.14);

  drawGroundShadow(projection, baseDrawX, drawY, targetWidth, targetHeight, width);

  sceneContext.save();
  sceneContext.imageSmoothingEnabled = true;
  sceneContext.filter = 'blur(0.35px)';
  sceneContext.drawImage(projectionMask.canvas, drawX, drawY, targetWidth, targetHeight);
  sceneContext.filter = 'none';
  sceneContext.globalAlpha = 0.86;
  sceneContext.drawImage(projectionMask.canvas, drawX, drawY, targetWidth, targetHeight);
  sceneContext.restore();

  drawEye(projectionMask, scale, drawX, drawY);
}

function animate(timestamp: number) {
  if (previousTimestamp === null) {
    previousTimestamp = timestamp;
  }

  const deltaSeconds = (timestamp - previousTimestamp) / 1000;
  previousTimestamp = timestamp;

  if (!paused) {
    elapsedSeconds += deltaSeconds * speedMultiplier;
  }

  render();
  window.requestAnimationFrame(animate);
}

function setPaused(nextPaused: boolean) {
  paused = nextPaused;
  pauseButton.textContent = paused ? '继续' : '暂停';
}

speedInput.addEventListener('input', () => {
  speedMultiplier = Number(speedInput.value);
  speedValue.value = `${speedMultiplier.toFixed(2)}x`;
});

spotInput.addEventListener('input', () => {
  stage.style.setProperty('--spot-strength', spotInput.value);
});

eyeInput.addEventListener('change', () => {
  showEye = eyeInput.checked;
});

pauseButton.addEventListener('click', () => {
  setPaused(!paused);
});

stage.addEventListener('pointerdown', (event) => {
  if ((event.target as HTMLElement).closest('.controls')) {
    return;
  }

  setPaused(!paused);
});

window.addEventListener('resize', resize);

async function bootstrap() {
  try {
    const image = await loadImage(CROW_IMAGE_URL);
    projectionMask = createProjectionMask(readImageData(image));
    resize();
    window.requestAnimationFrame(animate);
  } catch (error) {
    prompt.textContent = '乌鸦素材加载失败';
    throw error;
  }
}

eyeInput.checked = false;
showEye = false;
stage.style.setProperty('--spot-strength', spotInput.value);
setPaused(initialParams.get('paused') === '1');
resize();
void bootstrap();
