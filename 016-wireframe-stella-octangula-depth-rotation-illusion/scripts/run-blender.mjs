import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const experimentRoot = path.resolve(__dirname, '..');
const command = process.argv[2] ?? 'scene';
const config = JSON.parse(
  readFileSync(path.join(__dirname, 'stella-octangula-config.json'), 'utf8')
);

const profileNames = Object.keys(config.profiles);
if (profileNames.length !== 1 || profileNames[0] !== 'preview') {
  throw new Error('Experiment 016 is low-resolution-only and may define only preview.');
}
const preview = config.profiles.preview;
if (preview.width !== 360 || preview.height !== 640) {
  throw new Error('Experiment 016 preview must remain exactly 360x640.');
}

const blenderCandidates = [
  process.env.BLENDER_EXE,
  'D:\\software\\Blender 4.5 LTS\\blender.exe',
  'C:\\Program Files\\Blender Foundation\\Blender 4.5\\blender.exe',
  'C:\\Program Files\\Blender Foundation\\Blender 4.4\\blender.exe'
].filter(Boolean);
const blenderExe = blenderCandidates.find((candidate) => existsSync(candidate));

const commandMap = {
  scene: { profile: 'preview' },
  stills: { profile: 'preview', flag: '--stills' },
  preview: { profile: 'preview', flag: '--render' }
};

if (!Object.hasOwn(commandMap, command)) {
  console.error(`Unknown command "${command}". Use one of: scene, stills, preview.`);
  process.exit(1);
}
if (!blenderExe) {
  console.error(`Blender executable not found. Checked: ${blenderCandidates.join(', ')}`);
  console.error('Set BLENDER_EXE to the full path of blender.exe.');
  process.exit(1);
}

const selected = commandMap[command];
const blenderArgs = [
  '--background',
  '--factory-startup',
  '--python-exit-code',
  '1',
  '--python',
  path.join(__dirname, 'create_scene.py'),
  '--',
  '--profile',
  selected.profile,
  '--project-root',
  experimentRoot
];
if (selected.flag) blenderArgs.push(selected.flag);

const result = spawnSync(blenderExe, blenderArgs, {
  stdio: 'inherit',
  windowsHide: true
});
if (result.error) {
  console.error(result.error.message);
  process.exit(1);
}
if (result.status !== 0) process.exit(result.status ?? 1);

function parseRate(rate) {
  const [numerator, denominator] = rate.split('/').map(Number);
  return numerator / denominator;
}

function decodedFrameHash(videoPath, frameNumber) {
  const hash = spawnSync(
    'ffmpeg',
    [
      '-v',
      'error',
      '-i',
      videoPath,
      '-vf',
      `select=eq(n\\,${frameNumber})`,
      '-fps_mode',
      'passthrough',
      '-frames:v',
      '1',
      '-f',
      'framemd5',
      '-'
    ],
    { encoding: 'utf8', windowsHide: true }
  );
  if (hash.status !== 0) throw new Error(hash.stderr || `Frame ${frameNumber} hash failed.`);
  const dataLine = hash.stdout.split(/\r?\n/).find((line) => /^\s*0\s*,/.test(line));
  if (!dataLine) throw new Error(`Could not parse decoded frame ${frameNumber} hash.`);
  return dataLine.split(',').at(-1).trim();
}

function extractFrame(videoPath, frameNumber, outputPath) {
  const extraction = spawnSync(
    'ffmpeg',
    [
      '-y',
      '-v',
      'error',
      '-i',
      videoPath,
      '-vf',
      `select=eq(n\\,${frameNumber})`,
      '-frames:v',
      '1',
      outputPath
    ],
    { encoding: 'utf8', windowsHide: true }
  );
  if (extraction.status !== 0) throw new Error(extraction.stderr || 'Frame extraction failed.');
}

function verifyPreview() {
  const videoPath = path.join(experimentRoot, preview.output);
  if (!existsSync(videoPath)) throw new Error(`Rendered video is missing: ${videoPath}`);
  const probe = spawnSync(
    'ffprobe',
    [
      '-v',
      'error',
      '-select_streams',
      'v:0',
      '-count_frames',
      '-show_entries',
      'stream=codec_name,width,height,avg_frame_rate,nb_read_frames:format=duration',
      '-of',
      'json',
      videoPath
    ],
    { encoding: 'utf8', windowsHide: true }
  );
  if (probe.status !== 0) throw new Error(probe.stderr || 'ffprobe failed.');
  const metadata = JSON.parse(probe.stdout);
  const stream = metadata.streams[0];
  const expectedFrames = preview.fps * preview.seconds;
  const actualFrames = Number(stream.nb_read_frames);
  const actualFps = parseRate(stream.avg_frame_rate);
  if (
    stream.codec_name !== 'h264' ||
    stream.width !== 360 ||
    stream.height !== 640 ||
    Math.abs(actualFps - preview.fps) > 1e-9 ||
    actualFrames !== expectedFrames ||
    Math.abs(Number(metadata.format.duration) - preview.seconds) > 0.05
  ) {
    throw new Error(`Video contract mismatch: ${JSON.stringify(metadata)}`);
  }
  const turns = preview.seconds / config.style.rotationCycleSeconds;
  if (turns !== 2) throw new Error(`Expected exactly two turns, received ${turns}.`);
  const firstFrameHash = decodedFrameHash(videoPath, 0);
  const lastFrameHash = decodedFrameHash(videoPath, expectedFrames - 1);
  if (firstFrameHash === lastFrameHash) {
    throw new Error('The encoded tail must not duplicate the first frame.');
  }

  const outputDirectory = path.join(experimentRoot, 'output');
  extractFrame(videoPath, 0, path.join(outputDirectory, 'preview-first-frame.png'));
  extractFrame(
    videoPath,
    expectedFrames - 1,
    path.join(outputDirectory, 'preview-last-frame.png')
  );
  const columns = config.style.motionContactColumns;
  const rows = Math.ceil(config.style.motionContactFrameCount / columns);
  const contactPath = path.join(
    outputDirectory,
    'stella-octangula-motion-contact-sheet.png'
  );
  const contact = spawnSync(
    'ffmpeg',
    [
      '-y',
      '-v',
      'error',
      '-t',
      String(config.style.rotationCycleSeconds),
      '-i',
      videoPath,
      '-vf',
      `fps=${config.style.motionContactFrameCount}/${config.style.rotationCycleSeconds},tile=${columns}x${rows}:padding=2:margin=2:color=black`,
      '-frames:v',
      '1',
      contactPath
    ],
    { encoding: 'utf8', windowsHide: true }
  );
  if (contact.status !== 0) throw new Error(contact.stderr || 'Contact sheet failed.');

  const inspection = {
    profile: 'preview',
    path: preview.output,
    codec: stream.codec_name,
    width: stream.width,
    height: stream.height,
    fps: actualFps,
    frames: actualFrames,
    duration: Number(metadata.format.duration),
    turns,
    repeatedTailFrame: false,
    firstDecodedFrameHash: firstFrameHash,
    lastDecodedFrameHash: lastFrameHash,
    conceptualLoopFrame: expectedFrames + 1,
    highResolutionProfileExists: false,
    highResolutionRenderAttempted: false
  };
  writeFileSync(
    path.join(outputDirectory, 'video-inspection-preview.json'),
    `${JSON.stringify(inspection, null, 2)}\n`
  );
  console.log(
    `Verified preview: H.264, ${actualFrames} frames, ${preview.seconds}s, ${actualFps}fps at 360x640; repeated tail: false.`
  );
  console.log(`Motion contact sheet: ${contactPath}`);
}

if (selected.flag === '--render') {
  try {
    verifyPreview();
  } catch (error) {
    console.error(error instanceof Error ? error.message : error);
    process.exit(1);
  }
}
