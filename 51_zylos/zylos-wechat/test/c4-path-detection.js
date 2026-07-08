import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { execFileSync } from 'node:child_process';

const repoRoot = path.resolve(import.meta.dirname, '..');
const tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'zylos-wechat-c4-'));
const homeDir = path.join(tmpRoot, 'home');
const dataDir = path.join(tmpRoot, 'zylos', 'components', 'wechat');
const expectedScript = path.join(homeDir, 'zylos', '.claude', 'skills', 'comm-bridge', 'scripts', 'c4-receive.js');

fs.mkdirSync(homeDir, { recursive: true });

try {
  execFileSync('node', ['hooks/post-install.js'], {
    cwd: repoRoot,
    env: {
      ...process.env,
      HOME: homeDir,
      ZYLOS_WECHAT_DATA_DIR: dataDir,
    },
    stdio: 'pipe',
    encoding: 'utf8',
  });

  const configPath = path.join(dataDir, 'config.json');
  const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
  assert.equal(
    config.c4.receiveScript,
    expectedScript,
    'post-install should default to ~/zylos/.claude/skills/comm-bridge/scripts/c4-receive.js'
  );

  const runtimeScript = execFileSync(
    'node',
    [
      '--input-type=module',
      '-e',
      "import { getConfig } from './src/lib/config.js'; console.log(getConfig().c4.receiveScript);",
    ],
    {
      cwd: repoRoot,
      env: {
        ...process.env,
        HOME: homeDir,
        ZYLOS_WECHAT_DATA_DIR: dataDir,
      },
      stdio: 'pipe',
      encoding: 'utf8',
    }
  ).trim();

  assert.equal(
    runtimeScript,
    expectedScript,
    'runtime config should prefer ~/zylos/.claude/skills/comm-bridge/scripts/c4-receive.js'
  );

  console.log('c4 path detection');
  console.log('  ✓ post-install default path uses ~/zylos/.claude/skills/comm-bridge');
  console.log('  ✓ runtime config prefers ~/zylos/.claude/skills/comm-bridge');
} finally {
  fs.rmSync(tmpRoot, { recursive: true, force: true });
}
