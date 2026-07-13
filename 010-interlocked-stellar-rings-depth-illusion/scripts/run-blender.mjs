import { existsSync } from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const experimentRoot = path.resolve(__dirname, '..');
const command = process.argv[2] ?? 'scene';
const blenderExe = process.env.BLENDER_EXE ?? 'D:\\software\\Blender 4.5 LTS\\blender.exe';

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

if (!existsSync(blenderExe)) {
  console.error(`Blender executable not found: ${blenderExe}`);
  console.error('Set BLENDER_EXE to the full path of blender.exe if it is installed elsewhere.');
  process.exit(1);
}

const selected = commandMap[command];
const blenderArgs = [
  '--background',
  '--factory-startup',
  '--python',
  path.join(__dirname, 'create_scene.py'),
  '--',
  '--profile',
  selected.profile,
  '--project-root',
  experimentRoot
];

if (selected.flag) {
  blenderArgs.push(selected.flag);
}

const result = spawnSync(blenderExe, blenderArgs, {
  stdio: 'inherit',
  windowsHide: true
});

if (result.error) {
  console.error(result.error.message);
  process.exit(1);
}

process.exit(result.status ?? 1);
