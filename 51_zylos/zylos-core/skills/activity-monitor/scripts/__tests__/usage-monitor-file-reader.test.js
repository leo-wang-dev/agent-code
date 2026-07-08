import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { describe, it } from 'node:test';
import {
  readClaudeUsageFromMonitorFiles,
  readCodexUsageFromMonitorFile
} from '../usage-monitor-file-reader.js';

function withTmpDir(fn) {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'usage-monitor-reader-'));
  try {
    return fn(tmpDir);
  } finally {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  }
}

describe('usage-monitor-file-reader', () => {
  it('prefers Claude statusline usage data when available', () => {
    withTmpDir((tmpDir) => {
      const statuslineFile = path.join(tmpDir, 'statusline.json');
      const usageStateFile = path.join(tmpDir, 'usage.json');

      fs.writeFileSync(statuslineFile, JSON.stringify({
        usage: {
          session: { percent: 12, resets: '20:00' },
          weeklyAll: { percent: 34, resets: 'Apr 8 15:00' },
          weeklySonnet: { percent: 5, resets: 'Apr 7 10:00' }
        }
      }));
      fs.writeFileSync(usageStateFile, JSON.stringify({
        session: { percent: 99, resets: 'stale' },
        weeklyAll: { percent: 99, resets: 'stale' }
      }));

      const result = readClaudeUsageFromMonitorFiles({ statuslineFile, usageStateFile });
      assert.equal(result.sessionPercent, 12);
      assert.equal(result.weeklyAllPercent, 34);
      assert.equal(result.weeklySonnetPercent, 5);
      assert.equal(result.statusShape, 'statusline_usage');
    });
  });

  it('falls back to usage.json when Claude statusline has no usage payload', () => {
    withTmpDir((tmpDir) => {
      const statuslineFile = path.join(tmpDir, 'statusline.json');
      const usageStateFile = path.join(tmpDir, 'usage.json');

      fs.writeFileSync(statuslineFile, JSON.stringify({
        context_window: { used_percentage: 42 }
      }));
      fs.writeFileSync(usageStateFile, JSON.stringify({
        session: { percent: 22, resets: '8pm' },
        weeklyAll: { percent: 19, resets: 'Mar 27, 11am' },
        weeklySonnet: { percent: 4, resets: 'Mar 26, 5am' }
      }));

      const result = readClaudeUsageFromMonitorFiles({ statuslineFile, usageStateFile });
      assert.equal(result.sessionPercent, 22);
      assert.equal(result.weeklyAllPercent, 19);
      assert.equal(result.weeklySonnetPercent, 4);
      assert.equal(result.statusShape, 'usage_json');
    });
  });

  it('reads Codex usage from usage-codex.json', () => {
    withTmpDir((tmpDir) => {
      const usageStateFile = path.join(tmpDir, 'usage-codex.json');

      fs.writeFileSync(usageStateFile, JSON.stringify({
        session: { percent: 2, resets: '20:51' },
        weeklyAll: { percent: 1, resets: '15:51 on Apr 8' },
        weeklySonnet: { percent: null, resets: null },
        fiveHour: { percent: 2, resets: '20:51' }
      }));

      const result = readCodexUsageFromMonitorFile({ usageStateFile });
      assert.equal(result.sessionPercent, 2);
      assert.equal(result.weeklyAllPercent, 1);
      assert.equal(result.fiveHourPercent, 2);
      assert.equal(result.statusShape, 'usage_codex_json');
    });
  });
});
