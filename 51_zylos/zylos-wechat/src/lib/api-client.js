/**
 * WeChat iLink Bot API Client
 *
 * Low-level HTTP client for the WeChat iLink Bot API.
 * Handles headers, timeouts, and base_info injection.
 */

import { randomBytes } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { redactBody, redactUrl } from './redact.js';

const PACKAGE_VERSION = (() => {
  try {
    const raw = readFileSync(new URL('../../package.json', import.meta.url), 'utf8');
    return JSON.parse(raw).version || '0.1.0';
  } catch {
    return '0.1.0';
  }
})();
const QR_STATUS_CLIENT_VERSION = '1';

const DEFAULT_BOT_AGENT = `zylos-wechat/${PACKAGE_VERSION}`;
const BOT_AGENT_NAME_RE = /^[A-Za-z0-9_.\-]{1,32}\/[A-Za-z0-9_.+\-]{1,32}$/;

function sanitizeBotAgent(raw) {
  if (!raw || typeof raw !== 'string') return DEFAULT_BOT_AGENT;
  const trimmed = raw.trim();
  if (!trimmed) return DEFAULT_BOT_AGENT;
  const tokens = trimmed.split(/\s+/).filter((t) => BOT_AGENT_NAME_RE.test(t));
  if (tokens.length === 0) return DEFAULT_BOT_AGENT;
  const joined = tokens.join(' ');
  return Buffer.byteLength(joined, 'utf-8') <= 256 ? joined : DEFAULT_BOT_AGENT;
}

function buildClientVersion(version) {
  const parts = version.split('.').map((p) => parseInt(p, 10));
  const major = Math.min(parts[0] || 0, 255);
  const minor = Math.min(parts[1] || 0, 255);
  const patch = Math.min(parts[2] || 0, 255);
  return ((major & 0xff) << 16) | ((minor & 0xff) << 8) | (patch & 0xff);
}

const DEFAULT_BASE_URL = 'https://ilinkai.weixin.qq.com';
const DEFAULT_CDN_URL = 'https://novac2c.cdn.weixin.qq.com/c2c';

const TIMEOUT_LONGPOLL = 35_000;
const TIMEOUT_REGULAR = 15_000;
const TIMEOUT_LIGHTWEIGHT = 10_000;

function generateUin() {
  const buf = randomBytes(4);
  const num = buf.readUInt32BE(0);
  return Buffer.from(String(num)).toString('base64');
}

function createAbortContext(timeout, externalSignal) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);

  let onAbort = null;
  if (externalSignal) {
    onAbort = () => controller.abort();
    if (externalSignal.aborted) {
      onAbort();
    } else {
      externalSignal.addEventListener('abort', onAbort, { once: true });
    }
  }

  return {
    signal: controller.signal,
    cleanup() {
      clearTimeout(timer);
      if (externalSignal && onAbort) {
        externalSignal.removeEventListener('abort', onAbort);
      }
    },
  };
}

export class WeChatApiClient {
  #token;
  #baseUrl;
  #cdnBaseUrl;
  #channelVersion;
  #appId;
  #botAgent;
  #clientVersionNum;
  #logger;

  /**
   * @param {object} opts
   * @param {string} [opts.token] - Bearer token from QR login
   * @param {string} [opts.baseUrl] - API base URL (per-account override)
   * @param {string} [opts.cdnBaseUrl] - CDN base URL
   * @param {string} [opts.channelVersion] - Protocol channel version
   * @param {string} [opts.appId] - iLink-App-Id header value
   * @param {string} [opts.botAgent] - bot_agent field in base_info
   * @param {object} [opts.logger]
   */
  constructor(opts = {}) {
    this.#token = opts.token || null;
    this.#baseUrl = opts.baseUrl || DEFAULT_BASE_URL;
    this.#cdnBaseUrl = opts.cdnBaseUrl || DEFAULT_CDN_URL;
    this.#channelVersion = opts.channelVersion || '2.1.3';
    this.#appId = opts.appId ?? 'bot';
    this.#botAgent = sanitizeBotAgent(opts.botAgent);
    this.#clientVersionNum = buildClientVersion(this.#channelVersion);
    this.#logger = opts.logger || null;
  }

  get baseUrl() { return this.#baseUrl; }
  get cdnBaseUrl() { return this.#cdnBaseUrl; }
  get hasToken() { return !!this.#token; }

  setToken(token) { this.#token = token; }
  setBaseUrl(url) { this.#baseUrl = url; }
  setCdnBaseUrl(url) { this.#cdnBaseUrl = url; }

  /**
   * Build common headers for API requests.
   * @param {object} [opts]
   * @param {boolean} [opts.noAuth] - Skip Authorization header
   * @param {Record<string, string>} [opts.extra] - Additional headers
   */
  #headers(opts = {}) {
    const headers = {
      'Content-Type': 'application/json',
      'AuthorizationType': 'ilink_bot_token',
      'X-WECHAT-UIN': generateUin(),
      'iLink-App-Id': this.#appId,
      'iLink-App-ClientVersion': opts.clientVersion || String(this.#clientVersionNum),
    };

    if (this.#token && !opts.noAuth) {
      headers.Authorization = `Bearer ${this.#token}`;
    }

    if (opts.extra) {
      Object.assign(headers, opts.extra);
    }

    return headers;
  }

  /**
   * Make an API POST request.
   * @param {string} path
   * @param {object} body
   * @param {object} [opts]
   * @param {number} [opts.timeout]
   * @param {AbortSignal} [opts.signal]
   * @returns {Promise<object>}
   */
  async post(path, body, opts = {}) {
    const timeout = opts.timeout || TIMEOUT_REGULAR;
    const url = `${this.#baseUrl}${path}`;
    const payload = {
      ...body,
      base_info: {
        channel_version: this.#channelVersion,
        bot_agent: this.#botAgent,
        ...(body.base_info || {}),
      },
    };
    const jsonBody = JSON.stringify(payload);
    const headers = this.#headers();
    headers['Content-Length'] = String(Buffer.byteLength(jsonBody, 'utf8'));

    this.#logger?.debug?.(`POST ${redactUrl(url)} body=${redactBody(jsonBody)}`);
    const abort = createAbortContext(timeout, opts.signal);

    try {
      const res = await fetch(url, {
        method: 'POST',
        headers,
        body: jsonBody,
        signal: abort.signal,
      });

      if (!res.ok) {
        const text = await res.text().catch(() => '');
        this.#logger?.debug?.(`POST ${path} ${res.status} ${redactBody(text)}`);
        throw new ApiError(`HTTP ${res.status}: ${text}`, res.status);
      }

      return await res.json();
    } finally {
      abort.cleanup();
    }
  }

  /**
   * Make a GET request (used for QR login flow).
   * @param {string} path
   * @param {object} [opts]
   * @param {number} [opts.timeout]
   * @param {Record<string, string>} [opts.extraHeaders]
   * @param {AbortSignal} [opts.signal]
   */
  async get(path, opts = {}) {
    const timeout = opts.timeout || TIMEOUT_REGULAR;
    const url = `${this.#baseUrl}${path}`;
    const abort = createAbortContext(timeout, opts.signal);

    this.#logger?.debug?.(`GET ${redactUrl(url)}`);

    try {
      const res = await fetch(url, {
        method: 'GET',
        headers: this.#headers({
          noAuth: true,
          clientVersion: opts.clientVersion,
          extra: opts.extraHeaders,
        }),
        signal: abort.signal,
      });

      if (!res.ok) {
        const text = await res.text().catch(() => '');
        this.#logger?.debug?.(`GET ${path} ${res.status} ${redactBody(text)}`);
        throw new ApiError(`HTTP ${res.status}: ${text}`, res.status);
      }

      return await res.json();
    } finally {
      abort.cleanup();
    }
  }

  // --- Convenience methods ---

  /**
   * Long-poll for updates.
   * @param {string} getUpdatesBuf
   * @param {AbortSignal} [signal]
   */
  async getUpdates(getUpdatesBuf, signal) {
    return this.post('/ilink/bot/getupdates', {
      get_updates_buf: getUpdatesBuf || '',
    }, { timeout: TIMEOUT_LONGPOLL + 5_000, signal });
  }

  /**
   * Send a message.
   * @param {object} msg
   */
  async sendMessage(msg) {
    return this.post('/ilink/bot/sendmessage', { msg });
  }

  /**
   * Get config (typing ticket).
   * @param {string} userId
   * @param {string} [contextToken]
   */
  async getConfig(userId, contextToken) {
    const body = { ilink_user_id: userId };
    if (contextToken) body.context_token = contextToken;
    return this.post('/ilink/bot/getconfig', body, { timeout: TIMEOUT_LIGHTWEIGHT });
  }

  /**
   * Send typing indicator.
   * @param {string} userId
   * @param {string} typingTicket
   * @param {number} [status=1]
   */
  async sendTyping(userId, typingTicket, status = 1) {
    return this.post('/ilink/bot/sendtyping', {
      ilink_user_id: userId,
      typing_ticket: typingTicket,
      status,
    }, { timeout: TIMEOUT_LIGHTWEIGHT });
  }

  /**
   * Get upload URL for media.
   * @param {object} params
   */
  async getUploadUrl(params) {
    return this.post('/ilink/bot/getuploadurl', params);
  }

  // --- Lifecycle notifications ---

  async notifyStart() {
    return this.post('/ilink/bot/msg/notifystart', {}, { timeout: TIMEOUT_LIGHTWEIGHT });
  }

  async notifyStop(opts = {}) {
    const timeout = opts.timeout || TIMEOUT_LIGHTWEIGHT;
    return this.post('/ilink/bot/msg/notifystop', {}, { timeout });
  }

  // --- QR Login ---

  /**
   * Get QR code for login.
   */
  async getQrCode() {
    return this.get('/ilink/bot/get_bot_qrcode?bot_type=3');
  }

  /**
   * Poll QR code status.
   * @param {string} qrcodeToken
   * @param {AbortSignal} [signal]
   */
  async getQrCodeStatus(qrcodeToken, signal) {
    const encoded = encodeURIComponent(qrcodeToken);
    return this.get(`/ilink/bot/get_qrcode_status?qrcode=${encoded}`, {
      timeout: TIMEOUT_LONGPOLL + 5_000,
      clientVersion: QR_STATUS_CLIENT_VERSION,
      signal,
    });
  }

  // --- CDN ---

  /**
   * Upload encrypted file to CDN.
   * @param {string} uploadParam
   * @param {string} filekey
   * @param {Buffer} encryptedData
   * @returns {Promise<string>}
   */
  async cdnUpload(uploadParam, filekey, encryptedData) {
    const url = `${this.#cdnBaseUrl}/upload?encrypted_query_param=${encodeURIComponent(uploadParam)}&filekey=${encodeURIComponent(filekey)}`;
    const abort = createAbortContext(TIMEOUT_REGULAR);

    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/octet-stream' },
        body: encryptedData,
        signal: abort.signal,
      });

      if (!res.ok) {
        throw new ApiError(`CDN upload failed: HTTP ${res.status}`, res.status);
      }

      const downloadParam = res.headers.get('x-encrypted-param');
      if (!downloadParam) {
        throw new ApiError('CDN upload: missing x-encrypted-param header', 0);
      }

      return downloadParam;
    } finally {
      abort.cleanup();
    }
  }

  /**
   * Download encrypted file from CDN.
   * @param {string} encryptQueryParam
   * @param {string} [fullUrl]
   * @returns {Promise<Buffer>}
   */
  async cdnDownload(encryptQueryParam, fullUrl) {
    const url = fullUrl || `${this.#cdnBaseUrl}/download?encrypted_query_param=${encodeURIComponent(encryptQueryParam)}`;
    const abort = createAbortContext(TIMEOUT_REGULAR);

    try {
      const res = await fetch(url, { signal: abort.signal });
      if (!res.ok) {
        throw new ApiError(`CDN download failed: HTTP ${res.status}`, res.status);
      }
      return Buffer.from(await res.arrayBuffer());
    } finally {
      abort.cleanup();
    }
  }
}

export class ApiError extends Error {
  constructor(message, statusCode, details = null) {
    super(message);
    this.name = 'ApiError';
    this.statusCode = statusCode;
    this.details = details;
  }
}
