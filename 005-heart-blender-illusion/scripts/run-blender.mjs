import { existsSync } from 'node:fs';
import { mkdir } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawn } from 'node:child_process';

const __dirname = dirname(fileURLToPath(import.meta.url));
const projectRoot = resolve(__dirname, '..');
const mode = process.argv[2] ?? 'scene';
const validModes = new Set(['scene', 'preview', 'final']);

if (!validModes.has(mode)) {
  console.error(`Unsupported mode "${mode}". Use one of: ${Array.from(validModes).join(', ')}`);
  process.exit(1);
}

const configPath = resolve(__dirname, 'heart-illusion-config.json');
const scriptPath = resolve(__dirname, 'create_scene.py');
const outputBlend = resolve(projectRoot, 'output', 'heart-mobius-illusion.blend');
const blenderBin = process.env.BLENDER_BIN || 'blender';

if (!existsSync(scriptPath)) {
  console.error(`Missing Blender scene script: ${scriptPath}`);
  process.exit(1);
}

await mkdir(dirname(outputBlend), { recursive: true });

const args = [
  '--background',
  '--python',
  scriptPath,
  '--',
  '--mode',
  mode,
  '--config',
  configPath,
  '--blend',
  outputBlend
];

const child = spawn(blenderBin, args, {
  cwd: projectRoot,
  stdio: 'inherit'
});

child.on('error', (error) => {
  console.error(`Unable to start Blender with "${blenderBin}". Set BLENDER_BIN to the Blender executable path. ${error.message}`);
  process.exit(1);
});

child.on('exit', (code) => {
  process.exit(code ?? 1);
});
