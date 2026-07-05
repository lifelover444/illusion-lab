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
  scene: { profile: 'final', render: false },
  preview: { profile: 'preview', render: true },
  final: { profile: 'final', render: true }
};

if (!Object.hasOwn(commandMap, command)) {
  console.error(`Unknown command "${command}". Use one of: scene, preview, final.`);
  process.exit(1);
}

if (!existsSync(blenderExe)) {
  console.error(`Blender executable not found: ${blenderExe}`);
  console.error('Set BLENDER_EXE to the full path of blender.exe if it is installed elsewhere.');
  process.exit(1);
}

const readOption = (name) => {
  const index = process.argv.indexOf(name);
  if (index === -1) {
    return undefined;
  }

  const value = process.argv[index + 1];
  if (!value || value.startsWith('--')) {
    console.error(`Missing value for ${name}.`);
    process.exit(1);
  }

  return value;
};

const sceneScript = path.join(__dirname, 'create_scene.py');
const selected = commandMap[command];
const profile = readOption('--profile') ?? selected.profile;
const projectRoot = readOption('--project-root') ?? experimentRoot;
const blenderArgs = [
  '--background',
  '--factory-startup',
  '--python',
  sceneScript,
  '--',
  '--profile',
  profile,
  '--project-root',
  projectRoot
];

if (selected.render) {
  blenderArgs.push('--render');
}

const result = spawnSync(blenderExe, blenderArgs, {
  stdio: 'inherit',
  windowsHide: false
});

if (result.error) {
  console.error(result.error.message);
  process.exit(1);
}

process.exit(result.status ?? 1);
