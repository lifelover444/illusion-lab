import './styles.css';
import {
  createCrowProjectionRows,
  projectCrowRow,
  type CrowProjectionRows
} from './crow';
import { getAmbiguousProjection, getContinuityCues, getEyeOpacity } from './rotation';

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

function smoothstep(edge0: number, edge1: number, value: number) {
  const amount = Math.min(1, Math.max(0, (value - edge0) / (edge1 - edge0)));
  return amount * amount * (3 - 2 * amount);
}

function getSilhouetteWidth(rows: CrowProjectionRows) {
  return rows.bounds.maxX - rows.bounds.minX + 1;
}

function getLowerCueWeight(rowY: number, rows: CrowProjectionRows) {
  const span = Math.max(1, rows.bounds.maxY - rows.bounds.minY);
  const normalizedY = (rowY - rows.bounds.minY) / span;
  return smoothstep(0.58, 0.94, normalizedY);
}

function drawProjectionMask(mask: ProjectionMask) {
  const projection = getAmbiguousProjection(elapsedSeconds);
  const cues = getContinuityCues(projection.angle);
  const edgeDrift = cues.edgeDriftRatio * getSilhouetteWidth(mask.rows);
  const { context } = mask;

  context.clearRect(0, 0, mask.canvas.width, mask.canvas.height);
  context.fillStyle = '#000000';

  for (const row of mask.rows.rows) {
    const projected = projectCrowRow(row, projection, mask.rows.axisX);
    const lowerWeight = getLowerCueWeight(row.y, mask.rows);
    const occlusionTrim = Math.abs(cues.lowerOcclusionRatio) * lowerWeight * projected.width;
    let left = projected.left + edgeDrift - mask.cropX;
    let right = projected.right + edgeDrift - mask.cropX;
    const y = row.y - mask.cropY;

    if (projected.width <= 0) {
      continue;
    }

    if (cues.lowerOcclusionRatio > 0) {
      left += occlusionTrim;
    } else {
      right -= occlusionTrim;
    }

    context.fillRect(left, y, Math.max(0.8, right - left), 1.2);
  }

  return projection;
}

function drawEye(mask: ProjectionMask, scale: number, drawX: number, drawY: number) {
  const projection = getAmbiguousProjection(elapsedSeconds);
  const cues = getContinuityCues(projection.angle);
  const edgeDrift = cues.edgeDriftRatio * getSilhouetteWidth(mask.rows);
  const opacity = getEyeOpacity(projection.angle, showEye);

  if (opacity <= 0.01) {
    return;
  }

  const projectedEyeX =
    mask.rows.axisX +
    (EYE_IMAGE_POSITION.x - mask.rows.axisX) * projection.sideProjection +
    edgeDrift -
    mask.cropX;
  const x = drawX + projectedEyeX * scale;
  const y = drawY + mask.eyeY * scale;
  const radiusX = Math.max(3.5, scale * 11.5);
  const radiusY = Math.max(4.5, scale * 14.5);

  sceneContext.save();
  sceneContext.globalAlpha = opacity;
  sceneContext.strokeStyle = '#f5f5ee';
  sceneContext.lineWidth = Math.max(2, scale * 4);
  sceneContext.beginPath();
  sceneContext.ellipse(x, y, radiusX, radiusY, 0, 0, Math.PI * 2);
  sceneContext.stroke();
  sceneContext.restore();
}

function drawGroundShadow(
  mask: ProjectionMask,
  drawX: number,
  drawY: number,
  targetWidth: number,
  targetHeight: number
) {
  const projection = getAmbiguousProjection(elapsedSeconds);
  const cues = getContinuityCues(projection.angle);
  const sideFacing = Math.abs(projection.sideProjection);
  const centerX = drawX + targetWidth / 2 + cues.shadowDriftRatio * targetWidth;
  const centerY = drawY + targetHeight * 0.94;
  const radiusX = targetWidth * (0.3 + sideFacing * 0.08) * cues.shadowScaleX;
  const radiusY = Math.max(8, targetHeight * 0.035);
  const opacity = 0.085 + sideFacing * 0.025;
  const gradient = sceneContext.createRadialGradient(
    centerX,
    centerY,
    radiusY * 0.15,
    centerX,
    centerY,
    radiusX
  );

  gradient.addColorStop(0, `rgba(0, 0, 0, ${opacity})`);
  gradient.addColorStop(0.55, `rgba(0, 0, 0, ${opacity * 0.38})`);
  gradient.addColorStop(1, 'rgba(0, 0, 0, 0)');

  sceneContext.save();
  sceneContext.translate(centerX, centerY);
  sceneContext.scale(1, radiusY / radiusX);
  sceneContext.translate(-centerX, -centerY);
  sceneContext.fillStyle = gradient;
  sceneContext.beginPath();
  sceneContext.arc(centerX, centerY, radiusX, 0, Math.PI * 2);
  sceneContext.fill();
  sceneContext.restore();
}

function render() {
  const width = sceneCanvas.clientWidth;
  const height = sceneCanvas.clientHeight;

  sceneContext.clearRect(0, 0, width, height);

  if (!projectionMask) {
    return;
  }

  drawProjectionMask(projectionMask);

  const targetHeight = Math.min(height * 0.6, width * 1.17);
  const scale = targetHeight / projectionMask.canvas.height;
  const targetWidth = projectionMask.canvas.width * scale;
  const drawX = (width - targetWidth) / 2;
  const drawY = Math.max(42, height * 0.13);

  drawGroundShadow(projectionMask, drawX, drawY, targetWidth, targetHeight);

  sceneContext.save();
  sceneContext.imageSmoothingEnabled = true;
  sceneContext.filter = 'blur(0.32px)';
  sceneContext.drawImage(projectionMask.canvas, drawX, drawY, targetWidth, targetHeight);
  sceneContext.filter = 'none';
  sceneContext.globalAlpha = 0.88;
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

eyeInput.checked = initialParams.get('eye') === '1';
showEye = eyeInput.checked;
stage.style.setProperty('--spot-strength', spotInput.value);
setPaused(initialParams.get('paused') === '1');
resize();
void bootstrap();
