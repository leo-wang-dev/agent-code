import { join } from 'node:path';
import { readJsonFile, removeFileIfExists, writeJsonAtomic } from './file-store.js';

function toIso(value) {
  if (!value) return null;
  if (typeof value === 'string') return value;
  if (value instanceof Date) return value.toISOString();
  return null;
}

function normalizeErrorMessage(message) {
  if (typeof message !== 'string') return null;
  const trimmed = message.trim();
  return trimmed ? trimmed.slice(0, 300) : null;
}

export class RuntimeHealthStore {
  #accountsDir;

  constructor(dataDir) {
    this.#accountsDir = join(dataDir, 'accounts');
  }

  #path(normalizedId) {
    return join(this.#accountsDir, `${normalizedId}.runtime.json`);
  }

  async load(normalizedId) {
    return readJsonFile(this.#path(normalizedId), null);
  }

  async remove(normalizedId) {
    await removeFileIfExists(this.#path(normalizedId));
  }

  async upsert(normalizedId, patch = {}) {
    const existing = (await this.load(normalizedId)) || {};
    const now = new Date().toISOString();
    const next = {
      normalizedAccountId: normalizedId,
      accountId: typeof patch.accountId === 'string' ? patch.accountId : existing.accountId || null,
      userId: typeof patch.userId === 'string' ? patch.userId : existing.userId || null,
      savedAt: toIso(patch.savedAt) || existing.savedAt || null,
      loginHealth:
        typeof patch.loginHealth === 'string' ? patch.loginHealth : existing.loginHealth || 'unknown',
      lastPollAt: toIso(patch.lastPollAt) || existing.lastPollAt || null,
      lastPollErrorCode:
        typeof patch.lastPollErrorCode === 'string' || patch.lastPollErrorCode === null
          ? patch.lastPollErrorCode
          : existing.lastPollErrorCode || null,
      lastPollErrorMessage:
        normalizeErrorMessage(patch.lastPollErrorMessage) ??
        existing.lastPollErrorMessage ??
        null,
      lastInboundAt: toIso(patch.lastInboundAt) || existing.lastInboundAt || null,
      lastContextAt: toIso(patch.lastContextAt) || existing.lastContextAt || null,
      replyability:
        typeof patch.replyability === 'string' ? patch.replyability : existing.replyability || 'unknown',
      updatedAt: now,
    };

    await writeJsonAtomic(this.#path(normalizedId), next, { mode: 0o600 });
    return next;
  }
}
