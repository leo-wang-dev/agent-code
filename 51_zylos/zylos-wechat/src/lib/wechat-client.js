/**
 * @deprecated Use api-client.js instead. This module is a compatibility shim
 * that delegates to WeChatApiClient with the real API contract.
 * Will be removed in v0.2.0.
 */

import { WeChatApiClient } from './api-client.js';
import { randomBytes } from 'node:crypto';

export class WeChatClient {
  #api;

  constructor({ apiBase, accessToken, uin, deviceId, timeoutMs = 35000 }) {
    this.#api = new WeChatApiClient({
      token: accessToken,
      baseUrl: apiBase,
    });
  }

  get api() { return this.#api; }

  async getUpdates({ offset, timeoutMs = 35000 }) {
    // offset is ignored — real API uses opaque get_updates_buf cursor
    // Callers should migrate to api-client.js + poller.js
    return this.#api.getUpdates('');
  }

  async sendMessage({ to, content, contextToken, type = 'text' }) {
    const clientId = `zylos-wechat:${Date.now()}-${randomBytes(4).toString('hex')}`;
    return this.#api.sendMessage({
      from_user_id: '',
      to_user_id: to,
      client_id: clientId,
      message_type: 2,
      message_state: 2,
      context_token: contextToken,
      item_list: [{ type: 1, text_item: { text: content } }],
    });
  }

  async sendTyping({ to, contextToken }) {
    // sendTyping requires a typing_ticket from getConfig, not contextToken
    // This shim cannot fully replicate — callers should use api-client.js directly
    console.warn('[wechat-client] sendTyping via deprecated shim — migrate to api-client.js');
    return {};
  }

  async getConfig() {
    // getConfig requires a userId parameter in the real API
    console.warn('[wechat-client] getConfig via deprecated shim — migrate to api-client.js');
    return {};
  }

  async createQrLoginSession() {
    return this.#api.getQrCode();
  }
}
