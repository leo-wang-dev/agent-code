#!/usr/bin/env node
/**
 * Post-install hook for zylos-wechat.
 * Creates required data directories and default config.
 */

import { mkdirSync, writeFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import { homedir } from 'node:os';

const C4_RECEIVE_RELATIVE = '.claude/skills/comm-bridge/scripts/c4-receive.js';

function resolveHomePath(p) {
  if (!p) return p;
  if (p.startsWith('~/')) return join(homedir(), p.slice(2));
  return p;
}

function detectC4ReceiveScript() {
  const candidates = [
    join(homedir(), 'zylos', C4_RECEIVE_RELATIVE),
    join(homedir(), C4_RECEIVE_RELATIVE),
    join(process.cwd(), C4_RECEIVE_RELATIVE),
    join(process.cwd(), '..', C4_RECEIVE_RELATIVE),
    join(process.cwd(), '..', '..', C4_RECEIVE_RELATIVE),
  ];

  for (const candidate of candidates) {
    if (existsSync(candidate)) return candidate;
  }

  return candidates[0];
}

const DATA_DIR = resolveHomePath(
  process.env.ZYLOS_WECHAT_DATA_DIR || join(homedir(), 'zylos/components/wechat')
);

const dirs = [
  DATA_DIR,
  join(DATA_DIR, 'accounts'),
  join(DATA_DIR, 'logs'),
  join(DATA_DIR, 'media'),
];

for (const dir of dirs) {
  mkdirSync(dir, { recursive: true });
  console.log(`  ✓ ${dir}`);
}

const configPath = join(DATA_DIR, 'config.json');
if (!existsSync(configPath)) {
  const defaultConfig = {
    enabled: true,
    logLevel: 'info',
    dmPolicy: 'open',
    dmAllowFrom: [],
    wechat: {
      apiBase: 'https://ilinkai.weixin.qq.com',
      cdnBaseUrl: 'https://novac2c.cdn.weixin.qq.com/c2c',
    },
    c4: {
      receiveScript: detectC4ReceiveScript(),
    },
  };
  writeFileSync(configPath, JSON.stringify(defaultConfig, null, 2));
  console.log(`  ✓ ${configPath} (default config created)`);
} else {
  console.log(`  ○ ${configPath} (already exists, preserved)`);
}

const envVars = ['ZYLOS_WECHAT_ENABLED'];
const missing = envVars.filter((v) => !process.env[v]);
if (missing.length > 0) {
  console.log(`\n  Note: Optional env vars not set: ${missing.join(', ')}`);
  console.log('  Component will use defaults.');
}

console.log('\n  Post-install complete.');
console.log('  To add a WeChat account, start the service and trigger QR login.');
