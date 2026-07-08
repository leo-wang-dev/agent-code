import { randomBytes, randomUUID } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import { join } from 'node:path';
import { setTimeout as sleep } from 'node:timers/promises';
import QRCode from 'qrcode';
import { WeChatApiClient } from './api-client.js';
import { removeFileIfExists, writeJsonAtomic } from './file-store.js';

const ACTIVE_SESSION_TTL_MS = 10 * 60_000;
const TOMBSTONE_TTL_MS = 30 * 60_000;
const POLL_INTERVAL_MS = 1_000;
const MAX_QR_REFRESHES = 3;

function sessionId() {
  return `wxlogin_${randomUUID().replace(/-/g, '')}`;
}

function isObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function summarizeError(err) {
  const structuredCode =
    err &&
    typeof err === 'object' &&
    typeof err.code === 'string' &&
    err.code.startsWith('WECHAT_')
      ? err.code
      : null;
  const message = err instanceof Error ? err.message : String(err || 'unknown_error');
  if (structuredCode) {
    return {
      code: structuredCode,
      message: message || structuredCode,
    };
  }
  if (message.includes('timed out')) {
    return { code: 'WECHAT_LOGIN_TIMEOUT', message };
  }
  if (message.includes('aborted')) {
    return { code: 'WECHAT_LOGIN_CANCELLED', message };
  }
  return { code: 'WECHAT_LOGIN_FAILED', message };
}

function publicSessionShape(session) {
  return {
    sessionId: session.sessionId,
    state: session.state,
    createdAt: session.createdAt,
    expiresAt: session.expiresAt,
    terminalAt: session.terminalAt || null,
    qrPngBase64: session.qrPngBase64 || null,
    accountId: session.accountId || null,
    normalizedAccountId: session.normalizedAccountId || null,
    userId: session.userId || null,
    lastErrorCode: session.lastErrorCode || null,
    lastErrorMessage: session.lastErrorMessage || null,
  };
}

function hasPngSignature(buffer) {
  return (
    buffer.length >= 8 &&
    buffer[0] === 0x89 &&
    buffer[1] === 0x50 &&
    buffer[2] === 0x4e &&
    buffer[3] === 0x47 &&
    buffer[4] === 0x0d &&
    buffer[5] === 0x0a &&
    buffer[6] === 0x1a &&
    buffer[7] === 0x0a
  );
}

function extractPngBase64(value) {
  try {
    const buffer = Buffer.from(value, 'base64');
    return hasPngSignature(buffer) ? buffer.toString('base64') : null;
  } catch {
    return null;
  }
}

async function normalizeQrPngBase64(qrcodeImgContent) {
  if (typeof qrcodeImgContent !== 'string') {
    return null;
  }

  const trimmed = qrcodeImgContent.trim();
  if (!trimmed) {
    return null;
  }

  if (trimmed.startsWith('data:image/png;base64,')) {
    return trimmed.slice('data:image/png;base64,'.length);
  }

  const maybeBase64 = trimmed.replace(/\s+/g, '');
  if (/^[A-Za-z0-9+/=]+$/.test(maybeBase64) && maybeBase64.length > 256) {
    const pngBase64 = extractPngBase64(maybeBase64);
    if (pngBase64) {
      return pngBase64;
    }
  }

  // Upstream commonly returns a URL that should be encoded into a QR,
  // not a directly downloadable image payload. Generate a PNG locally so
  // dashboard callers can keep rendering a stable qrPngBase64 contract.
  const buffer = await QRCode.toBuffer(trimmed, {
    errorCorrectionLevel: 'M',
    margin: 1,
    type: 'png',
    width: 256,
  });
  return buffer.toString('base64');
}

export class LoginSessionStore {
  #sessionsDir;
  #logger;
  #qrClientFactory;
  #sessions = new Map();
  #activeSessionId = null;
  #gcTimer = null;

  constructor({ dataDir, logger, qrClientFactory }) {
    this.#sessionsDir = join(dataDir, 'login-sessions');
    this.#logger = logger;
    this.#qrClientFactory =
      qrClientFactory ||
      (() => {
        return new WeChatApiClient();
      });
  }

  async init() {
    await writeJsonAtomic(join(this.#sessionsDir, '.keep'), { createdAt: new Date().toISOString() })
      .catch(async () => {
        // Avoid failing init just because the marker cannot be written.
      });
    await removeFileIfExists(join(this.#sessionsDir, '.keep'));
    await this.cleanup({
      markActiveAsFailed: true,
      failureCode: 'WECHAT_COMPONENT_RESTARTED',
      failureMessage: 'Login session ended because the component restarted',
    });
    this.#gcTimer = setInterval(() => {
      this.cleanup().catch((err) => {
        this.#logger?.warn('login session cleanup failed:', err.message);
      });
    }, 5 * 60_000);
    this.#gcTimer.unref?.();
  }

  stop() {
    if (this.#gcTimer) {
      clearInterval(this.#gcTimer);
      this.#gcTimer = null;
    }
    for (const session of this.#sessions.values()) {
      session.abortController?.abort();
    }
    this.#sessions.clear();
    this.#activeSessionId = null;
  }

  sessionPath(sessionId) {
    return join(this.#sessionsDir, `${sessionId}.json`);
  }

  secretPath(sessionId) {
    return join(this.#sessionsDir, `${sessionId}.secret.json`);
  }

  async cleanup(opts = {}) {
    const now = Date.now();
    const { readdir } = await import('node:fs/promises');

    let names = [];
    try {
      names = await readdir(this.#sessionsDir);
    } catch {
      return;
    }

    for (const name of names) {
      if (!name.endsWith('.json') || name.endsWith('.secret.json')) continue;
      const path = join(this.#sessionsDir, name);
      const session = await this.#loadPublicFile(path);
      if (!session) continue;

      const expiresAt = Date.parse(session.expiresAt || '');
      const terminalAt = Date.parse(session.terminalAt || '');
      const ageMs = Number.isFinite(terminalAt) ? now - terminalAt : null;
      const isTerminal = Boolean(session.terminalAt);

      if (!isTerminal && Number.isFinite(expiresAt) && expiresAt <= now) {
        await this.#transitionTerminal(session, 'expired', {
          lastErrorCode: session.lastErrorCode || 'WECHAT_LOGIN_EXPIRED',
          lastErrorMessage: session.lastErrorMessage || 'QR login session expired',
        });
        continue;
      }

      if (!isTerminal && opts.markActiveAsFailed) {
        await this.#transitionTerminal(session, 'failed', {
          lastErrorCode: opts.failureCode || 'WECHAT_COMPONENT_RESTARTED',
          lastErrorMessage:
            opts.failureMessage || 'Login session ended because the component restarted',
        });
        continue;
      }

      if (isTerminal && ageMs !== null && ageMs > TOMBSTONE_TTL_MS) {
        await removeFileIfExists(path);
        await removeFileIfExists(this.secretPath(session.sessionId));
      }
    }
  }

  async getActiveSession() {
    await this.cleanup();
    if (this.#activeSessionId) {
      const session = await this.getSession(this.#activeSessionId);
      if (session && !session.terminalAt) {
        return session;
      }
      this.#activeSessionId = null;
    }

    const session = await this.#findLatestNonTerminalSession();
    if (!session) {
      return null;
    }
    this.#activeSessionId = session.sessionId;
    return session;
  }

  async getSession(sessionId) {
    const inMemory = this.#sessions.get(sessionId);
    if (inMemory) {
      return publicSessionShape(inMemory.publicState);
    }
    const session = await this.#loadPublicFile(this.sessionPath(sessionId));
    return session ? publicSessionShape(session) : null;
  }

  async startSession() {
    await this.cleanup();
    const existing = await this.getActiveSession();
    if (existing) {
      return existing;
    }

    const session = {
      sessionId: sessionId(),
      state: 'qr_ready',
      createdAt: new Date().toISOString(),
      expiresAt: new Date(Date.now() + ACTIVE_SESSION_TTL_MS).toISOString(),
      qrPngBase64: null,
      terminalAt: null,
      lastErrorCode: null,
      lastErrorMessage: null,
      accountId: null,
      normalizedAccountId: null,
      userId: null,
    };

    const runtime = {
      publicState: session,
      abortController: new AbortController(),
    };
    this.#sessions.set(session.sessionId, runtime);
    this.#activeSessionId = session.sessionId;

    await this.#writePublic(runtime.publicState);

    try {
      const client = this.#qrClientFactory();
      const firstQr = await client.getQrCode();
      if (!firstQr?.qrcode || !firstQr?.qrcode_img_content) {
        throw new Error('Failed to fetch QR code from upstream');
      }

      runtime.qrcode = firstQr.qrcode;
      runtime.client = client;
      runtime.publicState.qrPngBase64 = await normalizeQrPngBase64(firstQr.qrcode_img_content);
      runtime.publicState.state = 'qr_ready';
      runtime.publicState.expiresAt = new Date(Date.now() + ACTIVE_SESSION_TTL_MS).toISOString();
      await this.#writePublic(runtime.publicState);

      void this.#pollSession(runtime);
      return publicSessionShape(runtime.publicState);
    } catch (err) {
      await this.#transitionTerminal(runtime.publicState, 'failed', summarizeError(err));
      this.#sessions.delete(runtime.publicState.sessionId);
      this.#activeSessionId = null;
      throw err;
    }
  }

  async cancelSession(sessionId) {
    await this.cleanup();
    const runtime = this.#sessions.get(sessionId);
    if (runtime) {
      runtime.abortController?.abort();
      await this.#transitionTerminal(runtime.publicState, 'cancelled', {
        lastErrorCode: 'WECHAT_LOGIN_CANCELLED',
        lastErrorMessage: 'Login cancelled by user',
      });
      this.#sessions.delete(sessionId);
      if (this.#activeSessionId === sessionId) {
        this.#activeSessionId = null;
      }
      return publicSessionShape(runtime.publicState);
    }

    const session = await this.#loadPublicFile(this.sessionPath(sessionId));
    if (!session) return null;
    if (!session.terminalAt) {
      await this.#transitionTerminal(session, 'cancelled', {
        lastErrorCode: 'WECHAT_LOGIN_CANCELLED',
        lastErrorMessage: 'Login cancelled by user',
      });
    }
    return publicSessionShape(session);
  }

  async finalizeSession(sessionId, finalizeFn) {
    await this.cleanup();
    const session = await this.#loadPublicFile(this.sessionPath(sessionId));
    if (!session) {
      return { ok: false, code: 'WECHAT_LOGIN_NOT_FOUND', message: 'Login session not found' };
    }

    if (session.state === 'finalized') {
      return {
        ok: true,
        account: {
          accountId: session.accountId,
          normalizedAccountId: session.normalizedAccountId,
          userId: session.userId,
          savedAt: session.terminalAt,
        },
      };
    }

    if (session.state !== 'confirmed') {
      return {
        ok: false,
        code: 'WECHAT_LOGIN_NOT_READY',
        message: `Cannot finalize session in state ${session.state}`,
      };
    }

    const staged = await this.loadStagedCredentials(sessionId);
    if (!staged) {
      await this.#transitionTerminal(session, 'failed', {
        lastErrorCode: 'WECHAT_STAGED_CREDENTIALS_MISSING',
        lastErrorMessage: 'Staged credentials are missing for this login session',
      });
      return {
        ok: false,
        code: 'WECHAT_STAGED_CREDENTIALS_MISSING',
        message: 'Staged credentials missing',
      };
    }

    try {
      const account = await finalizeFn(staged);
      session.state = 'finalized';
      session.terminalAt = new Date().toISOString();
      session.qrPngBase64 = null;
      session.accountId = account.accountId;
      session.normalizedAccountId = account.normalizedAccountId;
      session.userId = account.userId;
      session.lastErrorCode = null;
      session.lastErrorMessage = null;
      await this.#writePublic(session);
      await removeFileIfExists(this.secretPath(sessionId));
      if (this.#activeSessionId === sessionId) {
        this.#activeSessionId = null;
      }
      this.#sessions.delete(sessionId);
      return { ok: true, account };
    } catch (err) {
      const error = summarizeError(err);
      return {
        ok: false,
        code: error.code,
        message: error.message,
      };
    }
  }

  async loadStagedCredentials(sessionId) {
    const data = await this.#loadPublicFile(this.secretPath(sessionId));
    if (!isObject(data)) return null;
    return data;
  }

  async #pollSession(runtime) {
    const signal = runtime.abortController.signal;
    let refreshCount = 0;
    let lastStatus = '';

    try {
      while (!signal.aborted) {
        const session = runtime.publicState;
        if (Date.parse(session.expiresAt) <= Date.now()) {
          await this.#transitionTerminal(session, 'expired', {
            lastErrorCode: 'WECHAT_LOGIN_EXPIRED',
            lastErrorMessage: 'QR login session expired',
          });
          this.#sessions.delete(session.sessionId);
          if (this.#activeSessionId === session.sessionId) {
            this.#activeSessionId = null;
          }
          return;
        }

        let statusResponse;
        try {
          statusResponse = await runtime.client.getQrCodeStatus(runtime.qrcode, signal);
        } catch (err) {
          if (err instanceof Error && err.name === 'AbortError') {
            return;
          }
          statusResponse = { status: 'wait' };
        }

        const { status } = statusResponse || {};
        if (status && status !== lastStatus) {
          lastStatus = status;
          if (status === 'scaned') {
            session.state = 'scanned';
            await this.#writePublic(session);
          }
        }

        if (status === 'confirmed') {
          const staged = {
            token: statusResponse.bot_token,
            baseUrl: statusResponse.baseurl,
            accountId: statusResponse.ilink_bot_id,
            normalizedId: String(statusResponse.ilink_bot_id || '').replace(/[@.]/g, '-'),
            userId: statusResponse.ilink_user_id,
            savedAt: new Date().toISOString(),
          };

          if (!staged.accountId || !staged.token || !staged.baseUrl) {
            throw new Error('Upstream confirmed login without complete credentials');
          }

          await writeJsonAtomic(this.secretPath(session.sessionId), staged, { mode: 0o600 });
          session.state = 'confirmed';
          session.qrPngBase64 = null;
          session.accountId = staged.accountId;
          session.normalizedAccountId = staged.normalizedId;
          session.userId = staged.userId || null;
          session.lastErrorCode = null;
          session.lastErrorMessage = null;
          await this.#writePublic(session);
          return;
        }

        if (status === 'scaned_but_redirect' && statusResponse.redirect_host) {
          runtime.client.setBaseUrl(`https://${statusResponse.redirect_host}`);
        } else if (status === 'expired') {
          refreshCount += 1;
          if (refreshCount > MAX_QR_REFRESHES) {
            await this.#transitionTerminal(session, 'expired', {
              lastErrorCode: 'WECHAT_LOGIN_EXPIRED',
              lastErrorMessage: 'QR code expired too many times',
            });
            this.#sessions.delete(session.sessionId);
            if (this.#activeSessionId === session.sessionId) {
              this.#activeSessionId = null;
            }
            return;
          }
          const nextQr = await runtime.client.getQrCode();
          runtime.qrcode = nextQr.qrcode;
          session.state = 'qr_ready';
          session.qrPngBase64 = await normalizeQrPngBase64(nextQr.qrcode_img_content);
          session.expiresAt = new Date(Date.now() + ACTIVE_SESSION_TTL_MS).toISOString();
          session.lastErrorCode = null;
          session.lastErrorMessage = null;
          await this.#writePublic(session);
          lastStatus = '';
        }

        await sleep(POLL_INTERVAL_MS, null, { signal }).catch(() => {});
      }
    } catch (err) {
      const error = summarizeError(err);
      await this.#transitionTerminal(runtime.publicState, 'failed', {
        lastErrorCode: error.code,
        lastErrorMessage: error.message,
      });
    } finally {
      this.#sessions.delete(runtime.publicState.sessionId);
      if (
        this.#activeSessionId === runtime.publicState.sessionId &&
        runtime.publicState.terminalAt
      ) {
        this.#activeSessionId = null;
      }
    }
  }

  async #transitionTerminal(session, state, error = {}) {
    session.state = state;
    session.terminalAt = new Date().toISOString();
    session.qrPngBase64 = null;
    if (typeof error.lastErrorCode === 'string') {
      session.lastErrorCode = error.lastErrorCode;
    }
    if (typeof error.lastErrorMessage === 'string') {
      session.lastErrorMessage = error.lastErrorMessage;
    }
    await this.#writePublic(session);
    await removeFileIfExists(this.secretPath(session.sessionId));
  }

  async #writePublic(session) {
    await writeJsonAtomic(this.sessionPath(session.sessionId), publicSessionShape(session), {
      mode: 0o600,
    });
  }

  async #loadPublicFile(path) {
    try {
      const raw = await readFile(path, 'utf8');
      const parsed = JSON.parse(raw);
      return isObject(parsed) ? parsed : null;
    } catch {
      return null;
    }
  }

  async #findLatestNonTerminalSession() {
    const { readdir } = await import('node:fs/promises');

    let names = [];
    try {
      names = await readdir(this.#sessionsDir);
    } catch {
      return null;
    }

    let best = null;
    let bestCreatedAt = Number.NEGATIVE_INFINITY;

    for (const name of names) {
      if (!name.endsWith('.json') || name.endsWith('.secret.json')) continue;
      const session = await this.#loadPublicFile(join(this.#sessionsDir, name));
      if (!session || session.terminalAt || typeof session.sessionId !== 'string') continue;

      const createdAt = Date.parse(session.createdAt || '');
      const sortKey = Number.isFinite(createdAt) ? createdAt : 0;
      if (!best || sortKey >= bestCreatedAt) {
        best = publicSessionShape(session);
        bestCreatedAt = sortKey;
      }
    }

    return best;
  }
}
