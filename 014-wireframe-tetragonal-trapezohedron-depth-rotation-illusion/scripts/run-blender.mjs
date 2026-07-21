import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const experimentRoot = path.resolve(__dirname, '..');
const command = process.argv[2] ?? 'scene';
const config = JSON.parse(
  readFileSync(path.join(__dirname, 'tetragonal-trapezohedron-config.json'), 'utf8')
);

const blenderCandidates = [
  process.env.BLENDER_EXE,
  'D:\\software\\Blender 4.5 LTS\\blender.exe',
  'C:\\Program Files\\Blender Foundation\\Blender 4.5\\blender.exe',
  'C:\\Program Files\\Blender Foundation\\Blender 4.4\\blender.exe'
].filter(Boolean);
const blenderExe = blenderCandidates.find((candidate) => existsSync(candidate));

const commandMap = {
  scene: { profile: 'final' },
  stills: { profile: 'preview', flag: '--stills' },
  preview: { profile: 'preview', flag: '--render' },
  final: { profile: 'final', flag: '--render' }
};

if (!Object.hasOwn(commandMap, command)) {
  console.error(`Unknown command "${command}". Use one of: scene, stills, preview, final.`);
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

function verifyVideo(profileName) {
  const profile = config.profiles[profileName];
  const videoPath = path.join(experimentRoot, profile.output);
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
      'stream=width,height,avg_frame_rate,nb_read_frames:format=duration',
      '-of',
      'json',
      videoPath
    ],
    { encoding: 'utf8', windowsHide: true }
  );
  if (probe.status !== 0) throw new Error(probe.stderr || 'ffprobe failed.');
  const metadata = JSON.parse(probe.stdout);
  const stream = metadata.streams[0];
  const expectedFrames = profile.fps * profile.seconds;
  const actualFrames = Number(stream.nb_read_frames);
  const actualFps = parseRate(stream.avg_frame_rate);
  if (
    stream.width !== profile.width ||
    stream.height !== profile.height ||
    Math.abs(actualFps - profile.fps) > 1e-9 ||
    actualFrames !== expectedFrames ||
    Math.abs(Number(metadata.format.duration) - profile.seconds) > 0.05
  ) {
    throw new Error(`Video contract mismatch: ${JSON.stringify(metadata)}`);
  }

  const inspection = {
    profile: profileName,
    path: profile.output,
    width: stream.width,
    height: stream.height,
    fps: actualFps,
    frames: actualFrames,
    duration: Number(metadata.format.duration),
    repeatedTailFrame: false,
    conceptualLoopFrame: expectedFrames + 1
  };
  writeFileSync(
    path.join(experimentRoot, 'output', `video-inspection-${profileName}.json`),
    `${JSON.stringify(inspection, null, 2)}\n`
  );

  const columns = config.style.motionContactColumns;
  const rows = Math.ceil(config.style.motionContactFrameCount / columns);
  const sheetPath = path.join(
    experimentRoot,
    'output',
    `${profileName}-motion-contact-sheet.png`
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
      sheetPath
    ],
    { encoding: 'utf8', windowsHide: true }
  );
  if (contact.status !== 0) throw new Error(contact.stderr || 'ffmpeg contact sheet failed.');
  console.log(`Verified ${profileName}: ${actualFrames} frames, ${profile.seconds}s, ${actualFps}fps.`);
  console.log(`Motion contact sheet: ${sheetPath}`);
}

if (selected.flag === '--render') {
  try {
    verifyVideo(selected.profile);
  } catch (error) {
    console.error(error instanceof Error ? error.message : error);
    process.exit(1);
  }
}
