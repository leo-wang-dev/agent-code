import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { LoginSessionStore } from '../src/lib/login-session-store.js';

const tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'zylos-wechat-login-session-'));
const dataDir = path.join(tmpRoot, 'data');
const sessionsDir = path.join(dataDir, 'login-sessions');
const now = Date.now();

fs.mkdirSync(sessionsDir, { recursive: true });

const confirmedSession = {
  sessionId: 'wxlogin_confirmed_fixture',
  state: 'confirmed',
  createdAt: new Date(now - 60_000).toISOString(),
  expiresAt: new Date(now + 10 * 60_000).toISOString(),
  terminalAt: null,
  qrPngBase64: null,
  accountId: 'abc123@im.bot',
  normalizedAccountId: 'abc123-im-bot',
  userId: 'wx_user_123',
  lastErrorCode: null,
  lastErrorMessage: null,
};

fs.writeFileSync(
  path.join(sessionsDir, `${confirmedSession.sessionId}.json`),
  `${JSON.stringify(confirmedSession, null, 2)}\n`,
  'utf8'
);

const store = new LoginSessionStore({
  dataDir,
  logger: {
    warn() {},
  },
});

try {
  const active = await store.getActiveSession();
  assert.ok(active, 'confirmed session on disk should still be discoverable as active');
  assert.equal(active.sessionId, confirmedSession.sessionId);
  assert.equal(active.state, 'confirmed');
  assert.equal(active.accountId, confirmedSession.accountId);
  assert.equal(active.terminalAt, null);

  const rediscovered = await store.getActiveSession();
  assert.ok(rediscovered, 'discovered confirmed session should remain active on repeat lookup');
  assert.equal(rediscovered.sessionId, confirmedSession.sessionId);

  console.log('login session store');
  console.log('  ✓ discovers confirmed sessions from disk before finalize');
  console.log('  ✓ keeps confirmed sessions visible to admin polling');
} finally {
  store.stop();
  fs.rmSync(tmpRoot, { recursive: true, force: true });
}
