import { spawn } from 'node:child_process';
import { existsSync, mkdirSync, readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { inflateSync } from 'node:zlib';
import { createCrowProjectionRows, projectCrowRow, type ImageDataLike } from '../src/crow';
import { getCrowStageLayout } from '../src/layout';
import { getAmbiguousProjection, getEyeOpacity } from '../src/rotation';

const WIDTH = 1080;
const HEIGHT = 1920;
const FPS = 30;
const DURATION_SECONDS = 25;
const SPEED_MULTIPLIER = 4.25;
const FRAME_COUNT = FPS * DURATION_SECONDS;
const OUTPUT_PATH = resolve('dist', 'rotating-crow-25s-4.25x-eye.mp4');
const PROMPT_TEXT = '乌鸦是朝着哪个方向移动？';
const PROMPT_FONT = 'C\\:/Windows/Fonts/msyh.ttc';

const MASK_THRESHOLD = 112;
const MASK_PADDING = 18;
const PROFILE_WIDTH_RATIO = 0.17;
const EYE_IMAGE_POSITION = { x: 385, y: 183 };

type Rgb = readonly [number, number, number];

type ProjectionMask = {
  rows: ReturnType<typeof createCrowProjectionRows>;
  cropX: number;
  cropY: number;
  width: number;
  height: number;
  eyeY: number;
};

type PngImage = ImageDataLike & {
  data: Uint8ClampedArray;
};

function readUint32(buffer: Buffer, offset: number) {
  return buffer.readUInt32BE(offset);
}

function paethPredictor(left: number, above: number, upperLeft: number) {
  const estimate = left + above - upperLeft;
  const leftDistance = Math.abs(estimate - left);
  const aboveDistance = Math.abs(estimate - above);
  const upperLeftDistance = Math.abs(estimate - upperLeft);

  if (leftDistance <= aboveDistance && leftDistance <= upperLeftDistance) {
    return left;
  }

  return aboveDistance <= upperLeftDistance ? above : upperLeft;
}

function decodePng(path: string): PngImage {
  const png = readFileSync(path);
  const signature = png.subarray(0, 8).toString('hex');

  if (signature !== '89504e470d0a1a0a') {
    throw new Error(`Unsupported PNG signature: ${path}`);
  }

  let offset = 8;
  let width = 0;
  let height = 0;
  let bitDepth = 0;
  let colorType = 0;
  const idatChunks: Buffer[] = [];

  while (offset < png.length) {
    const length = readUint32(png, offset);
    const type = png.subarray(offset + 4, offset + 8).toString('ascii');
    const data = png.subarray(offset + 8, offset + 8 + length);

    if (type === 'IHDR') {
      width = readUint32(data, 0);
      height = readUint32(data, 4);
      bitDepth = data[8];
      colorType = data[9];
    } else if (type === 'IDAT') {
      idatChunks.push(Buffer.from(data));
    } else if (type === 'IEND') {
      break;
    }

    offset += length + 12;
  }

  if (bitDepth !== 8 || colorType !== 2) {
    throw new Error(`Only 8-bit RGB PNG input is supported. Found bitDepth=${bitDepth}, colorType=${colorType}`);
  }

  const channels = 3;
  const bytesPerPixel = channels;
  const scanlineLength = width * channels;
  const inflated = inflateSync(Buffer.concat(idatChunks));
  const output = new Uint8ClampedArray(width * height * 4);
  let sourceOffset = 0;
  let previous = new Uint8Array(scanlineLength);

  for (let y = 0; y < height; y += 1) {
    const filter = inflated[sourceOffset];
    sourceOffset += 1;
    const current = new Uint8Array(scanlineLength);

    for (let x = 0; x < scanlineLength; x += 1) {
      const raw = inflated[sourceOffset + x];
      const left = x >= bytesPerPixel ? current[x - bytesPerPixel] : 0;
      const above = previous[x] ?? 0;
      const upperLeft = x >= bytesPerPixel ? previous[x - bytesPerPixel] : 0;

      if (filter === 0) {
        current[x] = raw;
      } else if (filter === 1) {
        current[x] = (raw + left) & 255;
      } else if (filter === 2) {
        current[x] = (raw + above) & 255;
      } else if (filter === 3) {
        current[x] = (raw + Math.floor((left + above) / 2)) & 255;
      } else if (filter === 4) {
        current[x] = (raw + paethPredictor(left, above, upperLeft)) & 255;
      } else {
        throw new Error(`Unsupported PNG filter type: ${filter}`);
      }
    }

    sourceOffset += scanlineLength;

    for (let x = 0; x < width; x += 1) {
      const source = x * channels;
      const target = (y * width + x) * 4;
      output[target] = current[source];
      output[target + 1] = current[source + 1];
      output[target + 2] = current[source + 2];
      output[target + 3] = 255;
    }

    previous = current;
  }

  return { width, height, data: output };
}

function createProjectionMask(imageData: ImageDataLike): ProjectionMask {
  const rows = createCrowProjectionRows(imageData, {
    threshold: MASK_THRESHOLD,
    profileWidthRatio: PROFILE_WIDTH_RATIO
  });
  const cropX = Math.max(0, rows.bounds.minX - MASK_PADDING);
  const cropY = Math.max(0, rows.bounds.minY - MASK_PADDING);
  const cropRight = Math.min(imageData.width - 1, rows.bounds.maxX + MASK_PADDING);
  const cropBottom = Math.min(imageData.height - 1, rows.bounds.maxY + MASK_PADDING);

  return {
    rows,
    cropX,
    cropY,
    width: cropRight - cropX + 1,
    height: cropBottom - cropY + 1,
    eyeY: EYE_IMAGE_POSITION.y - cropY
  };
}

function mixChannel(base: number, overlay: number, alpha: number) {
  return Math.round(base * (1 - alpha) + overlay * alpha);
}

function blend(buffer: Buffer, index: number, color: Rgb, alpha: number) {
  if (alpha >= 0.995) {
    buffer[index] = color[0];
    buffer[index + 1] = color[1];
    buffer[index + 2] = color[2];
    return;
  }

  buffer[index] = mixChannel(buffer[index], color[0], alpha);
  buffer[index + 1] = mixChannel(buffer[index + 1], color[1], alpha);
  buffer[index + 2] = mixChannel(buffer[index + 2], color[2], alpha);
}

function clamp01(value: number) {
  return Math.min(1, Math.max(0, value));
}

function lerp(a: number, b: number, t: number) {
  return a + (b - a) * t;
}

function lerpColor(a: Rgb, b: Rgb, t: number): Rgb {
  return [
    Math.round(lerp(a[0], b[0], t)),
    Math.round(lerp(a[1], b[1], t)),
    Math.round(lerp(a[2], b[2], t))
  ];
}

function radialColor(t: number): Rgb {
  if (t <= 0.31) {
    return lerpColor([247, 247, 238], [210, 211, 202], t / 0.31);
  }

  if (t <= 0.55) {
    return lerpColor([210, 211, 202], [111, 113, 106], (t - 0.31) / 0.24);
  }

  if (t <= 0.91) {
    return lerpColor([111, 113, 106], [21, 22, 20], (t - 0.55) / 0.36);
  }

  return [21, 22, 20];
}

function makeBackground() {
  const buffer = Buffer.alloc(WIDTH * HEIGHT * 3);
  const centerX = WIDTH * 0.5;
  const centerY = HEIGHT * 0.45;
  const radius = Math.max(WIDTH, HEIGHT) * 0.5;

  for (let y = 0; y < HEIGHT; y += 1) {
    const linear = lerpColor([26, 26, 23], [11, 11, 10], y / (HEIGHT - 1));

    for (let x = 0; x < WIDTH; x += 1) {
      const distance = Math.hypot(x - centerX, y - centerY) / radius;
      const radial = radialColor(clamp01(distance));
      const index = (y * WIDTH + x) * 3;

      buffer[index] = Math.round(radial[0] * 0.94 + linear[0] * 0.06);
      buffer[index + 1] = Math.round(radial[1] * 0.94 + linear[1] * 0.06);
      buffer[index + 2] = Math.round(radial[2] * 0.94 + linear[2] * 0.06);
    }
  }

  return buffer;
}

function fillRect(buffer: Buffer, x: number, y: number, width: number, height: number, alpha: number) {
  const left = Math.max(0, Math.floor(x));
  const top = Math.max(0, Math.floor(y));
  const right = Math.min(WIDTH, Math.ceil(x + width));
  const bottom = Math.min(HEIGHT, Math.ceil(y + height));

  if (left >= right || top >= bottom || alpha <= 0) {
    return;
  }

  for (let row = top; row < bottom; row += 1) {
    let index = (row * WIDTH + left) * 3;

    for (let column = left; column < right; column += 1) {
      buffer[index] = Math.round(buffer[index] * (1 - alpha));
      buffer[index + 1] = Math.round(buffer[index + 1] * (1 - alpha));
      buffer[index + 2] = Math.round(buffer[index + 2] * (1 - alpha));
      index += 3;
    }
  }
}

function strokeEye(buffer: Buffer, centerX: number, centerY: number, radiusX: number, radiusY: number, alpha: number) {
  const lineWidth = Math.max(2, radiusX * 0.34);
  const outer = 1 + lineWidth / Math.max(radiusX, radiusY);
  const inner = Math.max(0, 1 - lineWidth / Math.max(radiusX, radiusY));
  const left = Math.max(0, Math.floor(centerX - radiusX - lineWidth - 2));
  const right = Math.min(WIDTH - 1, Math.ceil(centerX + radiusX + lineWidth + 2));
  const top = Math.max(0, Math.floor(centerY - radiusY - lineWidth - 2));
  const bottom = Math.min(HEIGHT - 1, Math.ceil(centerY + radiusY + lineWidth + 2));

  for (let y = top; y <= bottom; y += 1) {
    for (let x = left; x <= right; x += 1) {
      const normal = Math.hypot((x - centerX) / radiusX, (y - centerY) / radiusY);

      if (normal < inner || normal > outer) {
        continue;
      }

      const edgeFade = clamp01(Math.min(normal - inner, outer - normal) * 2.4);
      blend(buffer, (y * WIDTH + x) * 3, [245, 245, 238], alpha * edgeFade);
    }
  }
}

function drawFrame(background: Buffer, mask: ProjectionMask, elapsedSeconds: number) {
  const frame = Buffer.from(background);
  const projection = getAmbiguousProjection(elapsedSeconds);
  const layout = getCrowStageLayout({
    sceneWidth: WIDTH,
    sceneHeight: HEIGHT,
    maskWidth: mask.width,
    maskHeight: mask.height,
    edgeOffsetRatio: projection.edgeOffsetRatio
  });
  const spanY = Math.max(1, mask.rows.bounds.maxY - mask.rows.bounds.minY);

  for (const row of mask.rows.rows) {
    const projected = projectCrowRow(row, projection, mask.rows.axisX, {
      verticalPosition: (row.y - mask.rows.bounds.minY) / spanY
    });

    if (projected.width <= 0) {
      continue;
    }

    const sourceX = projected.left - mask.cropX;
    const sourceY = row.y - mask.cropY;
    const drawX = layout.drawX + sourceX * layout.scale;
    const drawY = layout.drawY + sourceY * layout.scale;
    const drawWidth = projected.width * layout.scale;
    const drawHeight = Math.max(1, 1.2 * layout.scale);
    const reflectionY = layout.reflectionTop * 2 - drawY - drawHeight;
    const reflectionProgress = clamp01((reflectionY - layout.reflectionTop) / layout.reflectionHeight);
    const reflectionAlpha = 0.18 * (1 - reflectionProgress) * 0.78;

    fillRect(frame, drawX, reflectionY, drawWidth, drawHeight, reflectionAlpha);
  }

  for (const row of mask.rows.rows) {
    const projected = projectCrowRow(row, projection, mask.rows.axisX, {
      verticalPosition: (row.y - mask.rows.bounds.minY) / spanY
    });

    if (projected.width <= 0) {
      continue;
    }

    fillRect(
      frame,
      layout.drawX + (projected.left - mask.cropX) * layout.scale,
      layout.drawY + (row.y - mask.cropY) * layout.scale,
      projected.width * layout.scale,
      Math.max(1, 1.2 * layout.scale),
      0.94
    );
  }

  const eyeOpacity = getEyeOpacity(projection.angle, true) * 0.62;

  if (eyeOpacity > 0.01) {
    const projectedEyeX =
      mask.rows.axisX + (EYE_IMAGE_POSITION.x - mask.rows.axisX) * projection.sideProjection - mask.cropX;
    strokeEye(
      frame,
      layout.drawX + projectedEyeX * layout.scale,
      layout.drawY + mask.eyeY * layout.scale,
      Math.max(4, layout.scale * 11.5),
      Math.max(5, layout.scale * 14.5),
      eyeOpacity
    );
  }

  return frame;
}

async function writeAll(stream: NodeJS.WritableStream, buffer: Buffer) {
  if (stream.write(buffer)) {
    return;
  }

  await new Promise<void>((resolveWrite) => stream.once('drain', resolveWrite));
}

async function main() {
  mkdirSync(dirname(OUTPUT_PATH), { recursive: true });

  const image = decodePng(resolve('assets', 'crow.png'));
  const mask = createProjectionMask(image);
  const background = makeBackground();
  const firstFrame = drawFrame(background, mask, 0);
  const ffmpeg = spawn(
    'ffmpeg',
    [
      '-y',
      '-f',
      'rawvideo',
      '-pix_fmt',
      'rgb24',
      '-s',
      `${WIDTH}x${HEIGHT}`,
      '-r',
      String(FPS),
      '-i',
      'pipe:0',
      '-an',
      '-vf',
      `drawtext=fontfile='${PROMPT_FONT}':text='${PROMPT_TEXT}':x=(w-text_w)/2:y=h-144-text_h:fontsize=42:fontcolor=0xf8f8f0@0.84:shadowcolor=0x000000@0.48:shadowx=0:shadowy=6`,
      '-c:v',
      'libx264',
      '-preset',
      'ultrafast',
      '-qp',
      '0',
      '-g',
      '1',
      '-keyint_min',
      '1',
      '-sc_threshold',
      '0',
      '-pix_fmt',
      'yuv420p',
      '-movflags',
      '+faststart',
      OUTPUT_PATH
    ],
    { stdio: ['pipe', 'inherit', 'inherit'] }
  );

  if (!ffmpeg.stdin) {
    throw new Error('Could not open ffmpeg stdin');
  }

  for (let frameIndex = 0; frameIndex < FRAME_COUNT; frameIndex += 1) {
    const frame =
      frameIndex === FRAME_COUNT - 1
        ? firstFrame
        : drawFrame(background, mask, (frameIndex / FPS) * SPEED_MULTIPLIER);

    await writeAll(ffmpeg.stdin, frame);

    if (frameIndex % FPS === 0) {
      console.log(`rendered ${Math.round(frameIndex / FPS)}s / ${DURATION_SECONDS}s`);
    }
  }

  ffmpeg.stdin.end();

  const exitCode = await new Promise<number | null>((resolveExit) => ffmpeg.once('exit', resolveExit));

  if (exitCode !== 0) {
    throw new Error(`ffmpeg exited with code ${exitCode}`);
  }

  if (!existsSync(OUTPUT_PATH)) {
    throw new Error(`Expected output was not written: ${OUTPUT_PATH}`);
  }

  console.log(`wrote ${OUTPUT_PATH}`);
}

void main();
