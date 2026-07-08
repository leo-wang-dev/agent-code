/**
 * WeChat QR Login Flow
 *
 * Handles the QR code authentication flow for WeChat accounts.
 * Displays QR in terminal, polls for scan confirmation, returns credentials.
 */

import { setTimeout as sleep } from 'node:timers/promises';

const QR_POLL_INTERVAL = 1_000;       // 1s between polls
const QR_MAX_REFRESHES = 3;           // retry with new QR on expiry
const QR_OVERALL_TIMEOUT = 8 * 60_000; // 8 minutes total

/**
 * Normalize account ID for filesystem-safe usage.
 * e.g. "abc123@im.bot" → "abc123-im-bot"
 * @param {string} id
 * @returns {string}
 */
export function normalizeAccountId(id) {
  return id.replace(/[@.]/g, '-');
}

/**
 * Run the QR login flow.
 *
 * @param {import('./api-client.js').WeChatApiClient} client - API client (no token needed)
 * @param {object} [opts]
 * @param {(url: string) => void} [opts.onQrUrl] - Called with QR image URL to display
 * @param {(status: string) => void} [opts.onStatus] - Called with status updates
 * @param {AbortSignal} [opts.signal] - Abort signal
 * @returns {Promise<AccountCredentials>} Account credentials on success
 * @throws {LoginError} On timeout, abort, or max retries
 */
export async function qrLogin(client, opts = {}) {
  const { onQrUrl, onStatus, signal } = opts;
  const startTime = Date.now();

  let refreshCount = 0;

  while (refreshCount <= QR_MAX_REFRESHES) {
    if (signal?.aborted) throw new LoginError('Login aborted');
    if (Date.now() - startTime > QR_OVERALL_TIMEOUT) {
      throw new LoginError('Login timed out (8 minutes)');
    }

    // Step 1: Get QR code
    onStatus?.('Requesting QR code...');
    const qrResponse = await client.getQrCode();

    if (!qrResponse.qrcode || !qrResponse.qrcode_img_content) {
      throw new LoginError('Failed to get QR code from server');
    }

    const qrcodeToken = qrResponse.qrcode;
    const qrImageUrl = qrResponse.qrcode_img_content;

    onQrUrl?.(qrImageUrl);
    onStatus?.('Scan the QR code with WeChat to log in');

    // Step 2: Poll for status
    let lastStatus = '';
    while (true) {
      if (signal?.aborted) throw new LoginError('Login aborted');
      if (Date.now() - startTime > QR_OVERALL_TIMEOUT) {
        throw new LoginError('Login timed out (8 minutes)');
      }

      let statusResponse;
      try {
        statusResponse = await client.getQrCodeStatus(qrcodeToken, signal);
      } catch (err) {
        if (err.name === 'AbortError') {
          // Client-side timeout — treat as "wait"
          statusResponse = { status: 'wait' };
        } else {
          throw err;
        }
      }

      const { status } = statusResponse;

      if (status !== lastStatus) {
        lastStatus = status;
        if (status === 'scaned') {
          onStatus?.('QR scanned — confirm on your phone');
        }
      }

      if (status === 'confirmed') {
        const credentials = {
          token: statusResponse.bot_token,
          baseUrl: statusResponse.baseurl,
          accountId: statusResponse.ilink_bot_id,
          normalizedId: normalizeAccountId(statusResponse.ilink_bot_id),
          userId: statusResponse.ilink_user_id,
          savedAt: new Date().toISOString(),
        };

        onStatus?.(`Login successful: ${credentials.accountId}`);
        return credentials;
      }

      if (status === 'expired') {
        refreshCount++;
        onStatus?.(`QR expired, refreshing (${refreshCount}/${QR_MAX_REFRESHES})...`);
        break; // break inner loop to get new QR
      }

      // "wait" or "scaned" — continue polling
      await sleep(QR_POLL_INTERVAL);
    }
  }

  throw new LoginError(`QR code expired ${QR_MAX_REFRESHES} times`);
}

/**
 * @typedef {object} AccountCredentials
 * @property {string} token - Bearer token
 * @property {string} baseUrl - Account-specific API base URL
 * @property {string} accountId - Raw account ID (e.g. "hex@im.bot")
 * @property {string} normalizedId - Filesystem-safe ID (e.g. "hex-im-bot")
 * @property {string} userId - WeChat user ID of the account owner
 * @property {string} savedAt - ISO timestamp
 */

export class LoginError extends Error {
  constructor(message) {
    super(message);
    this.name = 'LoginError';
  }
}
