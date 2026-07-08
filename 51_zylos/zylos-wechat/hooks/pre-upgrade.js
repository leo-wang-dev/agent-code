#!/usr/bin/env node
/**
 * Pre-upgrade hook for zylos-wechat.
 * Backs up config before upgrade.
 */

import { copyFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import { homedir } from 'node:os';

const DATA_DIR = join(homedir(), 'zylos/components/wechat');
const configPath = join(DATA_DIR, 'config.json');
const backupPath = join(DATA_DIR, 'config.json.backup');

if (existsSync(configPath)) {
  copyFileSync(configPath, backupPath);
  console.log(`  ✓ config.json backed up to config.json.backup`);
} else {
  console.log('  ○ no config.json to backup');
}

console.log('  Pre-upgrade complete.');
