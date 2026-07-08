/**
 * Typing Indicator Manager
 *
 * Manages typing indicators for WeChat conversations.
 * Handles getConfig (to obtain typing_ticket), sendTyping lifecycle,
 * and automatic refresh every 5 seconds.
 */

const CONFIG_CACHE_TTL = 24 * 60 * 60_000; // 24 hours
const TYPING_REFRESH_INTERVAL = 5_000; // 5 seconds
const MAX_TYPING_LIFETIME_MS = 2 * 60_000; // 2 minutes
const CONFIG_RETRY_BASE = 2_000; // 2s initial retry
const CONFIG_RETRY_MAX = 60 * 60_000; // 1h max retry

export class TypingManager {
  #client;
  #configCache = new Map(); // userId -> { typingTicket, expiresAt, retryDelay }
  #activeTimers = new Map(); // userId -> { refreshTimer, stopTimer }

  /**
   * @param {import('./api-client.js').WeChatApiClient} client
   */
  constructor(client) {
    this.#client = client;
  }

  /**
   * Get typing ticket for a user (with caching).
   * @param {string} userId
   * @param {string} [contextToken]
   * @returns {Promise<string|null>} typing_ticket or null on failure
   */
  async getTypingTicket(userId, contextToken) {
    const cached = this.#configCache.get(userId);
    if (cached && Date.now() < cached.expiresAt) {
      return cached.typingTicket;
    }

    try {
      const resp = await this.#client.getConfig(userId, contextToken);
      if (resp.ret === 0 || resp.ret === undefined) {
        const ticket = resp.typing_ticket;
        if (ticket) {
          const jitter = Math.random() * 60 * 60_000;
          this.#configCache.set(userId, {
            typingTicket: ticket,
            expiresAt: Date.now() + CONFIG_CACHE_TTL - jitter,
            retryDelay: CONFIG_RETRY_BASE,
          });
          return ticket;
        }
      }
      return null;
    } catch {
      const entry = this.#configCache.get(userId);
      const retryDelay = entry?.retryDelay || CONFIG_RETRY_BASE;
      this.#configCache.set(userId, {
        typingTicket: null,
        expiresAt: Date.now() + retryDelay,
        retryDelay: Math.min(retryDelay * 2, CONFIG_RETRY_MAX),
      });
      return null;
    }
  }

  /**
   * Start typing indicator for a user.
   * Sends initial typing and refreshes every 5 seconds.
   * @param {string} userId
   * @param {string} [contextToken]
   */
  async startTyping(userId, contextToken) {
    await this.stopTyping(userId);

    const ticket = await this.getTypingTicket(userId, contextToken);
    if (!ticket) return;

    try {
      await this.#client.sendTyping(userId, ticket, 1);
    } catch {
      // Non-critical
    }

    const refreshTimer = setInterval(async () => {
      try {
        const currentTicket = await this.getTypingTicket(userId, contextToken);
        if (currentTicket) {
          await this.#client.sendTyping(userId, currentTicket, 1);
        }
      } catch {
        // Non-critical
      }
    }, TYPING_REFRESH_INTERVAL);

    const stopTimer = setTimeout(() => {
      this.stopTyping(userId).catch(() => {});
    }, MAX_TYPING_LIFETIME_MS);

    this.#activeTimers.set(userId, { refreshTimer, stopTimer });
  }

  /**
   * Check if typing is active for a user.
   * @param {string} userId
   * @returns {boolean}
   */
  isTyping(userId) {
    return this.#activeTimers.has(userId);
  }

  /**
   * Stop typing indicator for a user.
   * @param {string} userId
   */
  async stopTyping(userId) {
    const timers = this.#activeTimers.get(userId);
    if (timers) {
      clearInterval(timers.refreshTimer);
      clearTimeout(timers.stopTimer);
      this.#activeTimers.delete(userId);
    }

    const ticket = this.#configCache.get(userId)?.typingTicket;
    if (ticket) {
      try {
        await this.#client.sendTyping(userId, ticket, 2);
      } catch {
        // Non-critical
      }
    }
  }

  /**
   * Stop all active typing indicators.
   */
  stopAll() {
    for (const [userId] of this.#activeTimers) {
      this.stopTyping(userId).catch(() => {});
    }
  }
}
