/**
 * Context Token Manager
 *
 * In-memory store for WeChat context tokens with optional disk persistence.
 * Each inbound message carries a context_token that MUST be echoed
 * in every outbound reply to that user. Tokens are stored per
 * accountId:userId pair and updated on every inbound message.
 *
 * When persistPath is set, tokens are written to disk on every set()
 * so that scripts/send.js (a separate process) can read them.
 */

import { chmodSync, mkdirSync, readFileSync, renameSync, unlinkSync, writeFileSync } from 'node:fs';
import { dirname } from 'node:path';

const DEFAULT_MAX_ENTRIES = 10_000;
const DEFAULT_TTL_MS = 24 * 60 * 60_000;
const DEFAULT_PERSIST_DEBOUNCE_MS = 500;

export class ContextTokenStore {
  #tokens = new Map();
  #maxEntries;
  #ttlMs;
  #persistPath;
  #persistTimer = null;

  /**
   * @param {object} [opts]
   * @param {number} [opts.maxEntries=10000]
   * @param {number} [opts.ttlMs=86400000] - TTL in ms (24h default)
   * @param {string} [opts.persistPath] - File path to persist tokens for cross-process reads
   */
  constructor(opts = {}) {
    this.#maxEntries = opts.maxEntries || DEFAULT_MAX_ENTRIES;
    this.#ttlMs = opts.ttlMs || DEFAULT_TTL_MS;
    this.#persistPath = opts.persistPath || null;

    if (this.#persistPath) {
      this.#loadFromDisk();
    }
  }

  /**
   * Build the key for a token entry.
   * @param {string} accountId
   * @param {string} userId
   * @returns {string}
   */
  #key(accountId, userId) {
    return `${accountId}:${userId}`;
  }

  #pruneExpired() {
    const now = Date.now();
    let removed = 0;

    for (const [key, entry] of this.#tokens) {
      if (now - entry.updatedAt > this.#ttlMs) {
        this.#tokens.delete(key);
        removed += 1;
      }
    }

    return removed;
  }

  /**
   * Update context token from an inbound message.
   * @param {string} accountId
   * @param {string} userId
   * @param {string} contextToken
   */
  set(accountId, userId, contextToken) {
    if (!contextToken) return;

    this.#tokens.set(this.#key(accountId, userId), {
      token: contextToken,
      updatedAt: Date.now(),
    });

    if (this.#tokens.size > this.#maxEntries) {
      this.#evictOldest();
    }

    this.#schedulePersist();
  }

  /**
   * Get context token for sending a message to a user.
   * @param {string} accountId
   * @param {string} userId
   * @returns {string | null}
   */
  get(accountId, userId) {
    const key = this.#key(accountId, userId);
    const entry = this.#tokens.get(key);

    if (!entry) return null;

    if (Date.now() - entry.updatedAt > this.#ttlMs) {
      this.#tokens.delete(key);
      this.#schedulePersist();
      return null;
    }

    return entry.token;
  }

  /**
   * Check if a context token exists for a user.
   * @param {string} accountId
   * @param {string} userId
   * @returns {boolean}
   */
  has(accountId, userId) {
    return this.get(accountId, userId) !== null;
  }

  /**
   * Remove expired entries.
   * @returns {number} number of removed entries
   */
  cleanup() {
    const removed = this.#pruneExpired();
    if (removed > 0) {
      this.#schedulePersist();
    }
    return removed;
  }

  /**
   * Remove all tokens belonging to an account, including optional fallback IDs.
   * @param {string} accountId
   * @param {string[]} [fallbackAccountIds]
   * @returns {number} number of removed entries
   */
  deleteAccount(accountId, fallbackAccountIds = []) {
    const ids = new Set([accountId, ...fallbackAccountIds].filter(Boolean));
    let removed = 0;

    for (const key of this.#tokens.keys()) {
      if ([...ids].some((id) => key.startsWith(`${id}:`))) {
        this.#tokens.delete(key);
        removed += 1;
      }
    }

    if (removed > 0) {
      this.#schedulePersist();
    }

    return removed;
  }

  /**
   * Return the newest non-expired context token timestamp for an account.
   * @param {string} accountId
   * @param {string[]} [fallbackAccountIds]
   * @returns {number | null}
   */
  latestTimestampForAccount(accountId, fallbackAccountIds = []) {
    const ids = new Set([accountId, ...fallbackAccountIds].filter(Boolean));
    if (ids.size === 0) {
      return null;
    }

    const now = Date.now();
    let latest = null;

    for (const [key, entry] of this.#tokens) {
      const prefix = key.split(':', 1)[0];
      if (!ids.has(prefix)) continue;
      if (now - entry.updatedAt > this.#ttlMs) continue;
      if (latest === null || entry.updatedAt > latest) {
        latest = entry.updatedAt;
      }
    }

    return latest;
  }

  /**
   * Get store size.
   */
  get size() {
    return this.#tokens.size;
  }

  /**
   * Force flush to disk immediately (call on shutdown).
   */
  flush() {
    if (this.#persistTimer) {
      clearTimeout(this.#persistTimer);
      this.#persistTimer = null;
    }
    this.#writeToDisk();
  }

  /**
   * Load tokens from a persist file (for cross-process reads like send.js).
   * @param {string} filePath
   * @returns {ContextTokenStore}
   */
  static fromDisk(filePath) {
    return new ContextTokenStore({ persistPath: filePath });
  }

  // --- Disk persistence ---

  #loadFromDisk() {
    if (!this.#persistPath) return;

    try {
      const raw = readFileSync(this.#persistPath, 'utf8');
      const data = JSON.parse(raw);

      if (!data || typeof data !== 'object' || Array.isArray(data)) {
        return;
      }

      for (const [key, entry] of Object.entries(data)) {
        if (!entry || typeof entry !== 'object') continue;
        if (typeof entry.token !== 'string') continue;
        if (typeof entry.updatedAt !== 'number') continue;
        if (Date.now() - entry.updatedAt > this.#ttlMs) continue;
        this.#tokens.set(key, entry);
      }
    } catch {
      // missing or corrupt file: start fresh
    }
  }

  #schedulePersist() {
    if (!this.#persistPath || this.#persistTimer) return;

    this.#persistTimer = setTimeout(() => {
      this.#persistTimer = null;
      this.#writeToDisk();
    }, DEFAULT_PERSIST_DEBOUNCE_MS);

    this.#persistTimer.unref?.();
  }

  #writeToDisk() {
    if (!this.#persistPath) return;

    const tmpPath = `${this.#persistPath}.${process.pid}.${Date.now()}.tmp`;

    try {
      this.#pruneExpired();
      mkdirSync(dirname(this.#persistPath), { recursive: true });

      const payload = {};
      for (const [key, entry] of this.#tokens) {
        payload[key] = entry;
      }

      writeFileSync(tmpPath, `${JSON.stringify(payload, null, 2)}\n`);
      chmodSync(tmpPath, 0o600);
      renameSync(tmpPath, this.#persistPath);
    } catch (err) {
      try {
        unlinkSync(tmpPath);
      } catch {
        // ignore tmp cleanup failures
      }
      console.error('[context-tokens] persist failed:', err.message);
    }
  }

  #evictOldest() {
    let oldestKey = null;
    let oldestTime = Infinity;

    for (const [key, entry] of this.#tokens) {
      if (entry.updatedAt < oldestTime) {
        oldestTime = entry.updatedAt;
        oldestKey = key;
      }
    }

    if (oldestKey) {
      this.#tokens.delete(oldestKey);
    }
  }
}
