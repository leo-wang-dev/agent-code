/**
 * Account Store
 *
 * Manages WeChat account credentials and sync state on disk.
 * Each account has:
 * - credentials file: token, baseUrl, userId, savedAt
 * - sync state file: get_updates_buf (long-poll cursor)
 */

import { chmod, mkdir, readFile, rename, unlink, writeFile } from 'node:fs/promises';
import { join } from 'node:path';

const CONTEXT_TOKENS_FILE = 'context-tokens.json';

export class AccountStore {
  #dataDir;
  #accountsDir;

  /**
   * @param {string} dataDir - Component data directory (~/zylos/components/wechat)
   */
  constructor(dataDir) {
    this.#dataDir = dataDir;
    this.#accountsDir = join(dataDir, 'accounts');
  }

  async init() {
    await mkdir(this.#accountsDir, { recursive: true });
  }

  // --- Account Index ---

  #indexPath() {
    return join(this.#dataDir, 'accounts.json');
  }

  async #writeJsonAtomic(path, value, opts = {}) {
    const tmpPath = `${path}.${process.pid}.${Date.now()}.tmp`;
    const json = `${JSON.stringify(value, null, 2)}\n`;

    try {
      await writeFile(tmpPath, json);
      if (typeof opts.mode === 'number') {
        await chmod(tmpPath, opts.mode);
      }
      await rename(tmpPath, path);
    } catch (error) {
      try {
        await unlink(tmpPath);
      } catch {
        // ignore tmp cleanup failures
      }
      throw error;
    }
  }

  /**
   * List all registered account IDs (normalized).
   * @returns {Promise<string[]>}
   */
  async listAccounts() {
    try {
      const data = await readFile(this.#indexPath(), 'utf8');
      const parsed = JSON.parse(data);
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  }

  /**
   * Add account to index if not already present.
   * @param {string} normalizedId
   */
  async #addToIndex(normalizedId) {
    const accounts = await this.listAccounts();
    if (!accounts.includes(normalizedId)) {
      accounts.push(normalizedId);
      await this.#writeJsonAtomic(this.#indexPath(), accounts);
    }
  }

  /**
   * Remove account from index.
   * @param {string} normalizedId
   */
  async #removeFromIndex(normalizedId) {
    const accounts = await this.listAccounts();
    const filtered = accounts.filter((id) => id !== normalizedId);
    await this.#writeJsonAtomic(this.#indexPath(), filtered);
  }

  // --- Account Credentials ---

  #credPath(normalizedId) {
    return join(this.#accountsDir, `${normalizedId}.json`);
  }

  /**
   * Save account credentials (token, baseUrl, etc.).
   * File is chmod 0600 for security.
   * @param {import('./qr-login.js').AccountCredentials} creds
   */
  async saveCredentials(creds) {
    const path = this.#credPath(creds.normalizedId);
    const data = {
      accountId: creds.accountId,
      token: creds.token,
      baseUrl: creds.baseUrl,
      userId: creds.userId,
      savedAt: creds.savedAt,
    };
    await this.#writeJsonAtomic(path, data, { mode: 0o600 });
    await this.#addToIndex(creds.normalizedId);
  }

  /**
   * Load account credentials.
   * @param {string} normalizedId
   * @returns {Promise<{accountId?: string, token: string, baseUrl: string, userId: string, savedAt: string} | null>}
   */
  async loadCredentials(normalizedId) {
    try {
      const data = await readFile(this.#credPath(normalizedId), 'utf8');
      return JSON.parse(data);
    } catch {
      return null;
    }
  }

  async #removeContextTokens(normalizedId, rawAccountId) {
    const path = join(this.#dataDir, CONTEXT_TOKENS_FILE);
    let data;

    try {
      data = JSON.parse(await readFile(path, 'utf8'));
    } catch {
      return;
    }

    if (!data || typeof data !== 'object' || Array.isArray(data)) {
      return;
    }

    const prefixes = new Set([`${normalizedId}:`]);
    if (rawAccountId && rawAccountId !== normalizedId) {
      prefixes.add(`${rawAccountId}:`);
    }

    const filtered = {};
    let changed = false;

    for (const [key, value] of Object.entries(data)) {
      const remove = [...prefixes].some((prefix) => key.startsWith(prefix));
      if (remove) {
        changed = true;
        continue;
      }
      filtered[key] = value;
    }

    if (changed) {
      await this.#writeJsonAtomic(path, filtered, { mode: 0o600 });
    }
  }

  /**
   * Remove account and its state files.
   * @param {string} normalizedId
   */
  async removeAccount(normalizedId) {
    const creds = await this.loadCredentials(normalizedId);
    const paths = [
      this.#credPath(normalizedId),
      this.#syncPath(normalizedId),
    ];

    for (const path of paths) {
      try {
        await unlink(path);
      } catch {
        // ignore missing files
      }
    }

    await this.#removeFromIndex(normalizedId);
    await this.#removeContextTokens(normalizedId, creds?.accountId || null);
  }

  // --- Sync State ---

  #syncPath(normalizedId) {
    return join(this.#accountsDir, `${normalizedId}.sync.json`);
  }

  /**
   * Load the long-poll cursor for an account.
   * @param {string} normalizedId
   * @returns {Promise<string>} get_updates_buf (empty string if not found)
   */
  async loadSyncState(normalizedId) {
    try {
      const data = await readFile(this.#syncPath(normalizedId), 'utf8');
      const parsed = JSON.parse(data);
      return parsed.get_updates_buf || '';
    } catch {
      return '';
    }
  }

  /**
   * Save the long-poll cursor.
   * @param {string} normalizedId
   * @param {string} getUpdatesBuf
   */
  async saveSyncState(normalizedId, getUpdatesBuf) {
    await this.#writeJsonAtomic(this.#syncPath(normalizedId), {
      get_updates_buf: getUpdatesBuf,
    });
  }

  /**
   * Load all accounts with their credentials.
   * @returns {Promise<Array<{normalizedId: string, accountId?: string, token: string, baseUrl: string, userId: string, savedAt: string}>>}
   */
  async loadAllAccounts() {
    const ids = await this.listAccounts();
    const accounts = [];
    for (const id of ids) {
      const creds = await this.loadCredentials(id);
      if (creds) {
        accounts.push({ normalizedId: id, ...creds });
      }
    }
    return accounts;
  }
}
