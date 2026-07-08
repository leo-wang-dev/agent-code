/**
 * Long-Poll Manager
 *
 * Manages the getUpdates long-poll loop for a single WeChat account.
 * Handles offset tracking, error recovery, session expiry, and reconnection.
 */

import { setTimeout as sleep } from 'node:timers/promises';
import { EventEmitter } from 'node:events';

const SESSION_EXPIRED_ERRCODE = -14;
const SESSION_PAUSE_MS = 60 * 60_000; // 60 minutes
const MAX_CONSECUTIVE_FAILURES = 3;
const BACKOFF_AFTER_MAX_FAILURES = 30_000; // 30s
const RETRY_DELAY = 2_000; // 2s

function hasOwn(obj, key) {
  return Object.prototype.hasOwnProperty.call(obj, key);
}

/**
 * WeChat getUpdates currently returns success payloads without ret/errcode.
 * Treat as error only when ret/errcode are explicitly present and non-zero.
 */
function parseApiError(response) {
  if (!response || typeof response !== 'object') {
    return { ret: undefined, errcode: undefined, errmsg: 'invalid response payload' };
  }

  const hasRet = hasOwn(response, 'ret');
  const hasErrcode = hasOwn(response, 'errcode');
  const ret = response.ret;
  const errcode = response.errcode;

  if (!hasRet && !hasErrcode) {
    return null;
  }

  if ((hasRet && ret !== 0) || (hasErrcode && errcode !== 0)) {
    return {
      ret,
      errcode,
      errmsg: response.errmsg,
    };
  }

  return null;
}

/**
 * @typedef {object} PollerEvents
 * @property {(msgs: object[], accountId: string) => void} messages - New messages received
 * @property {(err: Error, accountId: string) => void} error - Non-fatal error
 * @property {(accountId: string) => void} session-expired - Session expired, needs re-auth
 * @property {(accountId: string) => void} connected - Poll loop started/resumed
 * @property {(accountId: string) => void} disconnected - Poll loop stopped
 */

export class Poller extends EventEmitter {
  #client;
  #accountStore;
  #accountId;
  #normalizedId;
  #running = false;
  #abortController = null;
  #consecutiveFailures = 0;
  #sessionPausedUntil = 0;

  /**
   * @param {object} opts
   * @param {import('./api-client.js').WeChatApiClient} opts.client - API client with token set
   * @param {import('./account-store.js').AccountStore} opts.accountStore
   * @param {string} opts.accountId - Raw account ID
   * @param {string} opts.normalizedId - Filesystem-safe account ID
   */
  constructor(opts) {
    super();
    this.#client = opts.client;
    this.#accountStore = opts.accountStore;
    this.#accountId = opts.accountId;
    this.#normalizedId = opts.normalizedId;
  }

  get accountId() { return this.#accountId; }
  get normalizedId() { return this.#normalizedId; }
  get running() { return this.#running; }

  /**
   * Start the long-poll loop.
   */
  async start() {
    if (this.#running) return;
    this.#running = true;
    this.#abortController = new AbortController();
    this.emit('connected', this.#accountId);

    try {
      await this.#pollLoop();
    } catch (err) {
      if (err.name !== 'AbortError') {
        this.emit('error', err, this.#accountId);
      }
    } finally {
      this.#running = false;
      this.emit('disconnected', this.#accountId);
    }
  }

  /**
   * Stop the long-poll loop.
   */
  stop() {
    this.#running = false;
    this.#abortController?.abort();
  }

  async #pollLoop() {
    let buf = await this.#accountStore.loadSyncState(this.#normalizedId);

    while (this.#running) {
      // Check session pause
      if (Date.now() < this.#sessionPausedUntil) {
        const remaining = this.#sessionPausedUntil - Date.now();
        await sleep(Math.min(remaining, 60_000), null, {
          signal: this.#abortController.signal,
        });
        continue;
      }

      try {
        const response = await this.#client.getUpdates(buf, this.#abortController.signal);

        // Success — reset failure counter
        this.#consecutiveFailures = 0;

        // API-level errors: only when ret/errcode are explicitly non-zero.
        const apiError = parseApiError(response);
        if (apiError) {
          if (apiError.errcode === SESSION_EXPIRED_ERRCODE) {
            this.#sessionPausedUntil = Date.now() + SESSION_PAUSE_MS;
            this.emit('session-expired', this.#accountId);
            continue;
          }

          this.#consecutiveFailures++;
          this.emit('error', new Error(
            `getUpdates error: ret=${apiError.ret} errcode=${apiError.errcode} errmsg=${apiError.errmsg}`
          ), this.#accountId);

          await this.#handleFailure();
          continue;
        }

        // Update cursor
        if (response.get_updates_buf) {
          buf = response.get_updates_buf;
          await this.#accountStore.saveSyncState(this.#normalizedId, buf);
        }

        // Emit messages
        if (response.msgs && response.msgs.length > 0) {
          this.emit('messages', response.msgs, this.#accountId);
        }

        // No delay on success — immediately poll again

      } catch (err) {
        if (err.name === 'AbortError') {
          if (!this.#running) break; // Intentional stop
          // Client-side timeout — treat as empty, continue immediately
          continue;
        }

        this.#consecutiveFailures++;
        this.emit('error', err, this.#accountId);
        await this.#handleFailure();
      }
    }
  }

  async #handleFailure() {
    if (!this.#running) return;

    if (this.#consecutiveFailures >= MAX_CONSECUTIVE_FAILURES) {
      this.#consecutiveFailures = 0;
      await sleep(BACKOFF_AFTER_MAX_FAILURES, null, {
        signal: this.#abortController.signal,
      }).catch(() => {});
    } else {
      await sleep(RETRY_DELAY, null, {
        signal: this.#abortController.signal,
      }).catch(() => {});
    }
  }
}
