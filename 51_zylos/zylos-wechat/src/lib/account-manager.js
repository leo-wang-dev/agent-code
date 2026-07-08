/**
 * Multi-Account Manager
 *
 * Manages the lifecycle of multiple WeChat accounts:
 * login → active → disconnected → re-auth
 *
 * Each account gets its own API client and poller instance.
 */

import { EventEmitter } from 'node:events';
import { WeChatApiClient } from './api-client.js';
import { AccountStore } from './account-store.js';
import { Poller } from './poller.js';
import { qrLogin } from './qr-login.js';

/**
 * @typedef {'idle'|'logging-in'|'active'|'disconnected'|'session-expired'} AccountState
 */

export class AccountManager extends EventEmitter {
  #store;
  #accounts = new Map(); // normalizedId → { client, poller, state, accountId }
  #reconcilePromise = null;
  #onMessages = null;
  #clientOpts;

  /**
   * @param {string} dataDir - Component data directory
   * @param {object} [clientOpts] - Extra options forwarded to WeChatApiClient
   */
  constructor(dataDir, clientOpts = {}) {
    super();
    this.#store = new AccountStore(dataDir);
    this.#clientOpts = clientOpts;
  }

  get store() { return this.#store; }

  /**
   * Initialize store and load existing accounts.
   * Does NOT start polling — call startAll() after init.
   */
  async init() {
    await this.#store.init();
  }

  /**
   * Load and start all saved accounts.
   * @param {(msgs: object[], accountId: string) => void} onMessages - Message handler
   */
  async startAll(onMessages) {
    this.#onMessages = onMessages;
    const result = await this.reconcile(onMessages);
    console.log(`[account-manager] Started ${result.active} account(s)`);
  }

  /**
   * Stop all account pollers.
   */
  async stopAll() {
    for (const [id, entry] of this.#accounts) {
      entry.poller.stop();
      entry.state = 'disconnected';
    }
  }

  /**
   * Add a new account via QR login.
   * @param {object} opts
   * @param {(url: string) => void} [opts.onQrUrl]
   * @param {(status: string) => void} [opts.onStatus]
   * @param {(msgs: object[], accountId: string) => void} opts.onMessages
   * @param {AbortSignal} [opts.signal]
   * @returns {Promise<string>} normalizedId of the new account
   */
  async addAccount(opts) {
    const client = new WeChatApiClient({ ...this.#clientOpts });

    opts.onStatus?.('Starting QR login...');

    const creds = await qrLogin(client, {
      onQrUrl: opts.onQrUrl,
      onStatus: opts.onStatus,
      signal: opts.signal,
    });

    // Update client with authenticated credentials
    client.setToken(creds.token);
    client.setBaseUrl(creds.baseUrl);

    // Save to disk
    await this.#store.saveCredentials(creds);

    this.#startAccount({
      normalizedId: creds.normalizedId,
      accountId: creds.accountId,
      token: creds.token,
      baseUrl: creds.baseUrl,
    }, opts.onMessages, client);

    return creds.normalizedId;
  }

  /**
   * Remove an account.
   * @param {string} normalizedId
   */
  async removeAccount(normalizedId) {
    const entry = this.#accounts.get(normalizedId);
    if (entry) {
      this.#stopAccount(normalizedId, entry);
    }
    await this.#store.removeAccount(normalizedId);
  }

  /**
   * Reconcile running pollers with the account store.
   * Starts newly added accounts, stops removed accounts, and restarts changed credentials.
   * @param {(msgs: object[], accountId: string) => void} onMessages
   * @returns {Promise<{started: number, stopped: number, restarted: number, active: number}>}
   */
  async reconcile(onMessages) {
    if (onMessages) {
      this.#onMessages = onMessages;
    }
    if (this.#reconcilePromise) {
      return this.#reconcilePromise;
    }

    this.#reconcilePromise = this.#reconcile(onMessages);
    try {
      return await this.#reconcilePromise;
    } finally {
      this.#reconcilePromise = null;
    }
  }

  /**
   * Get the API client for an account (for sending messages).
   * @param {string} normalizedId
   * @returns {WeChatApiClient | null}
   */
  getClient(normalizedId) {
    return this.#accounts.get(normalizedId)?.client || null;
  }

  async reconcileCurrent() {
    if (!this.#onMessages) {
      throw new Error('Account manager has not been initialized with a message handler');
    }
    return this.reconcile(this.#onMessages);
  }

  /**
   * Get the state of an account.
   * @param {string} normalizedId
   * @returns {AccountState | null}
   */
  getState(normalizedId) {
    return this.#accounts.get(normalizedId)?.state || null;
  }

  /**
   * List all accounts with their state.
   * @returns {Array<{normalizedId: string, accountId: string, state: AccountState}>}
   */
  listAccounts() {
    return Array.from(this.#accounts.entries()).map(([id, entry]) => ({
      normalizedId: id,
      accountId: entry.accountId,
      state: entry.state,
    }));
  }

  /**
   * Get the context token map for message sending.
   * Context tokens are managed externally (in the bridge layer)
   * since they come from inbound messages.
   */

  async #reconcile(onMessages) {
    const desiredAccounts = await this.#store.loadAllAccounts();
    const desiredMap = new Map(desiredAccounts.map((acct) => [acct.normalizedId, acct]));

    let started = 0;
    let stopped = 0;
    let restarted = 0;

    for (const [normalizedId, entry] of this.#accounts) {
      const desired = desiredMap.get(normalizedId);
      if (!desired) {
        this.#stopAccount(normalizedId, entry);
        stopped += 1;
        continue;
      }

      const rawAccountId = desired.accountId || desired.normalizedId;
      const changed =
        entry.accountId !== rawAccountId ||
        entry.token !== desired.token ||
        entry.baseUrl !== desired.baseUrl;

      if (changed) {
        this.#stopAccount(normalizedId, entry);
        this.#startAccount(desired, onMessages);
        restarted += 1;
      }
    }

    for (const acct of desiredAccounts) {
      if (this.#accounts.has(acct.normalizedId)) continue;
      this.#startAccount(acct, onMessages);
      started += 1;
    }

    return {
      started,
      stopped,
      restarted,
      active: this.#accounts.size,
    };
  }

  #startAccount(acct, onMessages, existingClient = null) {
    const client = existingClient || new WeChatApiClient({
      ...this.#clientOpts,
      token: acct.token,
      baseUrl: acct.baseUrl,
    });

    if (!existingClient) {
      client.setToken(acct.token);
      client.setBaseUrl(acct.baseUrl);
    }

    const rawAccountId = acct.accountId || acct.normalizedId;
    const poller = this.#createPoller(client, rawAccountId, acct.normalizedId, onMessages);

    this.#accounts.set(acct.normalizedId, {
      client,
      poller,
      state: 'active',
      accountId: rawAccountId,
      token: acct.token,
      baseUrl: acct.baseUrl,
    });

    poller.start().catch((err) => {
      console.error(`[account:${acct.normalizedId}] Poll loop crashed:`, err.message);
    });
  }

  #stopAccount(normalizedId, entry) {
    entry.poller.stop();
    entry.state = 'disconnected';
    this.#accounts.delete(normalizedId);
  }

  #createPoller(client, accountId, normalizedId, onMessages) {
    const poller = new Poller({
      client,
      accountStore: this.#store,
      accountId,
      normalizedId,
    });

    poller.on('messages', (msgs, acctId) => {
      onMessages(msgs, acctId, normalizedId);
    });

    poller.on('error', (err, acctId) => {
      console.error(`[account:${acctId}] Poll error:`, err.message);
      this.emit('error', err, acctId, normalizedId);
    });

    poller.on('session-expired', (acctId) => {
      console.warn(`[account:${acctId}] Session expired — pausing for 60 minutes`);
      const entry = this.#accounts.get(normalizedId);
      if (entry) entry.state = 'session-expired';
      this.emit('session-expired', acctId, normalizedId);
    });

    poller.on('connected', (acctId) => {
      const entry = this.#accounts.get(normalizedId);
      if (entry) entry.state = 'active';
      this.emit('connected', acctId, normalizedId);
    });

    poller.on('disconnected', (acctId) => {
      const entry = this.#accounts.get(normalizedId);
      if (entry && entry.state !== 'session-expired') {
        entry.state = 'disconnected';
      }
      this.emit('disconnected', acctId, normalizedId);
    });

    return poller;
  }
}
