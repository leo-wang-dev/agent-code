import { createServer } from 'node:http';
import { randomBytes } from 'node:crypto';
import { chmod, readFile, stat } from 'node:fs/promises';
import { writeTextAtomic } from './file-store.js';

function json(reply, statusCode, payload) {
  reply.writeHead(statusCode, {
    'Content-Type': 'application/json; charset=utf-8',
    'Cache-Control': 'no-store',
  });
  reply.end(`${JSON.stringify(payload)}\n`);
}

function sanitizeErrorMessage(message) {
  if (typeof message !== 'string') return 'unknown_error';
  return message.trim().slice(0, 300) || 'unknown_error';
}

async function readJsonBody(req) {
  const chunks = [];
  for await (const chunk of req) {
    chunks.push(chunk);
  }
  if (chunks.length === 0) return {};
  return JSON.parse(Buffer.concat(chunks).toString('utf8'));
}

export class AdminServer {
  #host;
  #port;
  #tokenPath;
  #logger;
  #getConfig;
  #accountManager;
  #accountStore;
  #contextTokens;
  #loginSessions;
  #runtimeHealth;
  #reconcileAccounts;
  #typingManagers;
  #server = null;
  #token = null;
  #tokenStatus = { healthy: true, issue: null };
  #started = false;

  constructor(opts) {
    this.#host = opts.host;
    this.#port = opts.port;
    this.#tokenPath = opts.tokenPath;
    this.#logger = opts.logger;
    this.#getConfig = opts.getConfig;
    this.#accountManager = opts.accountManager;
    this.#accountStore = opts.accountStore;
    this.#contextTokens = opts.contextTokens;
    this.#loginSessions = opts.loginSessions;
    this.#runtimeHealth = opts.runtimeHealth;
    this.#reconcileAccounts = opts.reconcileAccounts;
    this.#typingManagers = opts.typingManagers || new Map();
  }

  async start() {
    await this.#loadOrCreateToken();

    this.#server = createServer((req, res) => {
      void this.#handle(req, res).catch((err) => {
        json(res, 500, {
          ok: false,
          error: {
            code: 'WECHAT_ADMIN_INTERNAL_ERROR',
            message: sanitizeErrorMessage(err instanceof Error ? err.message : String(err)),
          },
        });
      });
    });

    await new Promise((resolve, reject) => {
      const handleError = (err) => {
        this.#logger?.error('admin server failed to bind:', err.message);
        this.#started = false;
        reject(err);
      };

      this.#server.once('error', handleError);
      this.#server.listen(this.#port, this.#host, () => {
        this.#server?.off('error', handleError);
        this.#started = true;
        resolve();
      });
    });
  }

  async close() {
    if (!this.#server) return;
    await new Promise((resolve) => this.#server.close(() => resolve()));
    this.#started = false;
    this.#server = null;
  }

  async #handle(req, res) {
    const url = new URL(req.url || '/', `http://${this.#host}:${this.#port}`);

    if (url.pathname === '/healthz' && req.method === 'GET') {
      const activeSession = await this.#loginSessions.getActiveSession();
      return json(res, 200, {
        ok: true,
        data: {
          status: this.#started ? 'ok' : 'degraded',
          admin: {
            host: this.#host,
            port: this.#port,
            tokenHealthy: this.#tokenStatus.healthy,
            tokenIssue: this.#tokenStatus.issue,
          },
          loginSession: activeSession ? activeSession.state : 'idle',
        },
      });
    }

    if (!this.#isAuthorized(req)) {
      return json(res, 401, {
        ok: false,
        error: {
          code: 'WECHAT_ADMIN_UNAUTHORIZED',
          message: 'Unauthorized',
        },
      });
    }

    if (url.pathname === '/v1/login/start' && req.method === 'POST') {
      const accounts = await this.#accountStore.loadAllAccounts();
      if (accounts.length > 0) {
        return json(res, 409, {
          ok: false,
          error: {
            code: 'WECHAT_ACCOUNT_CONFLICT',
            message: 'WeChat account already exists on this VM',
          },
        });
      }

      const session = await this.#loginSessions.startSession();
      return json(res, 200, { ok: true, session });
    }

    if (url.pathname === '/v1/login/session' && req.method === 'GET') {
      const session = await this.#loginSessions.getActiveSession();
      return json(res, 200, {
        ok: true,
        session: session || {
          state: 'idle',
          sessionId: null,
          createdAt: null,
          expiresAt: null,
          terminalAt: null,
          qrPngBase64: null,
          accountId: null,
          normalizedAccountId: null,
          userId: null,
          lastErrorCode: null,
          lastErrorMessage: null,
        },
      });
    }

    if (url.pathname === '/v1/login/cancel' && req.method === 'POST') {
      const body = await readJsonBody(req);
      const sessionId = typeof body.sessionId === 'string' ? body.sessionId : '';
      const session = sessionId ? await this.#loginSessions.cancelSession(sessionId) : null;
      if (!session) {
        return json(res, 404, {
          ok: false,
          error: {
            code: 'WECHAT_LOGIN_NOT_FOUND',
            message: 'Login session not found',
          },
        });
      }
      return json(res, 200, { ok: true, session });
    }

    if (url.pathname === '/v1/login/finalize' && req.method === 'POST') {
      const body = await readJsonBody(req);
      const sessionId = typeof body.sessionId === 'string' ? body.sessionId : '';
      const result = await this.#loginSessions.finalizeSession(sessionId, async (staged) => {
        const existing = await this.#accountStore.loadAllAccounts();
        if (existing.length > 0) {
          if (existing.length === 1 && existing[0].normalizedId === staged.normalizedId) {
            return {
              accountId: existing[0].accountId || staged.accountId,
              normalizedAccountId: existing[0].normalizedId,
              userId: existing[0].userId || staged.userId || null,
              savedAt: existing[0].savedAt || staged.savedAt,
            };
          }
          throw this.#businessError(
            'WECHAT_ACCOUNT_CONFLICT',
            'WeChat account already exists on this VM'
          );
        }

        await this.#accountStore.saveCredentials(staged);
        try {
          await this.#runtimeHealth.upsert(staged.normalizedId, {
            accountId: staged.accountId,
            userId: staged.userId,
            savedAt: staged.savedAt,
            loginHealth: 'healthy',
            replyability: 'needs_user_message',
          });
          await this.#reconcileAccounts();
          return {
            accountId: staged.accountId,
            normalizedAccountId: staged.normalizedId,
            userId: staged.userId || null,
            savedAt: staged.savedAt,
          };
        } catch (err) {
          await this.#accountStore.removeAccount(staged.normalizedId).catch(() => {});
          await this.#runtimeHealth.remove(staged.normalizedId).catch(() => {});
          throw err;
        }
      });

      if (!result.ok) {
        const statusCode = result.code === 'WECHAT_ACCOUNT_CONFLICT' ? 409 : 400;
        return json(res, statusCode, {
          ok: false,
          error: {
            code: result.code,
            message: result.message,
          },
        });
      }
      return json(res, 200, {
        ok: true,
        account: result.account,
      });
    }

    if (url.pathname === '/v1/accounts' && req.method === 'GET') {
      const accounts = await this.#accountStore.loadAllAccounts();
      const payload = await Promise.all(
        accounts.map(async (account) => {
          const runtime = await this.#runtimeHealth.load(account.normalizedId);
          return {
            accountId: account.accountId || account.normalizedId,
            normalizedAccountId: account.normalizedId,
            userId: account.userId || null,
            savedAt: account.savedAt || null,
            loginHealth: runtime?.loginHealth || 'unknown',
            replyability: runtime?.replyability || 'unknown',
          };
        })
      );
      return json(res, 200, { ok: true, accounts: payload });
    }

    if (url.pathname.startsWith('/v1/accounts/') && req.method === 'GET') {
      const normalizedId = decodeURIComponent(url.pathname.split('/')[3] || '');
      if (!normalizedId || !url.pathname.endsWith('/health')) {
        return json(res, 404, {
          ok: false,
          error: {
            code: 'WECHAT_NOT_FOUND',
            message: 'Route not found',
          },
        });
      }
      const account = await this.#accountStore.loadCredentials(normalizedId);
      if (!account) {
        return json(res, 404, {
          ok: false,
          error: {
            code: 'WECHAT_ACCOUNT_NOT_FOUND',
            message: 'WeChat account not found',
          },
        });
      }
      const runtime = await this.#runtimeHealth.load(normalizedId);
      return json(res, 200, {
        ok: true,
        account: {
          accountId: account.accountId || normalizedId,
          normalizedAccountId: normalizedId,
          userId: account.userId || null,
          savedAt: account.savedAt || null,
          loginHealth: runtime?.loginHealth || 'unknown',
          lastInboundAt: runtime?.lastInboundAt || null,
          lastContextAt: runtime?.lastContextAt || null,
          replyability: runtime?.replyability || 'unknown',
          dmPolicy: this.#getConfig().dmPolicy,
        },
      });
    }

    if (url.pathname.startsWith('/v1/accounts/') && req.method === 'DELETE') {
      const normalizedId = decodeURIComponent(url.pathname.split('/')[3] || '');
      const account = await this.#accountStore.loadCredentials(normalizedId);
      if (!account) {
        return json(res, 404, {
          ok: false,
          error: {
            code: 'WECHAT_ACCOUNT_NOT_FOUND',
            message: 'WeChat account not found',
          },
        });
      }
      await this.#accountManager.removeAccount(normalizedId);
      this.#contextTokens.deleteAccount(normalizedId, [account.accountId || '']);
      await this.#runtimeHealth.remove(normalizedId).catch(() => {});
      await this.#reconcileAccounts();
      return json(res, 200, { ok: true, removed: { normalizedAccountId: normalizedId } });
    }

    if (url.pathname === '/v1/typing/stop' && req.method === 'POST') {
      const body = await readJsonBody(req);
      const userId = typeof body.userId === 'string' ? body.userId : '';
      if (!userId) {
        return json(res, 400, {
          ok: false,
          error: { code: 'WECHAT_INVALID_PARAMS', message: 'userId is required' },
        });
      }
      let stoppedCount = 0;
      for (const typingMgr of this.#typingManagers.values()) {
        const hadActive = typingMgr.isTyping?.(userId);
        await typingMgr.stopTyping(userId);
        if (hadActive) stoppedCount++;
      }
      return json(res, 200, { ok: true, stopped: stoppedCount > 0, stoppedCount });
    }

    return json(res, 404, {
      ok: false,
      error: {
        code: 'WECHAT_NOT_FOUND',
        message: 'Route not found',
      },
    });
  }

  async #loadOrCreateToken() {
    try {
      const token = (await readFile(this.#tokenPath, 'utf8')).trim();
      const stats = await stat(this.#tokenPath);
      if (!token) {
        await this.#writeNewToken();
        return;
      }
      if ((stats.mode & 0o777) !== 0o600) {
        await chmod(this.#tokenPath, 0o600).catch(() => {});
      }
      this.#token = token;
      this.#tokenStatus = { healthy: true, issue: null };
      return;
    } catch (err) {
      if (err && typeof err === 'object' && 'code' in err && err.code === 'ENOENT') {
        await this.#writeNewToken();
        return;
      }
      try {
        await this.#writeNewToken();
      } catch {
        this.#tokenStatus = { healthy: false, issue: 'token_file_unreadable' };
      }
    }
  }

  async #writeNewToken() {
    const token = randomBytes(24).toString('base64url');
    await writeTextAtomic(this.#tokenPath, `${token}\n`, { mode: 0o600 });
    this.#token = token;
    this.#tokenStatus = { healthy: true, issue: null };
  }

  #businessError(code, message) {
    const error = new Error(message || code);
    error.code = code;
    return error;
  }

  #isAuthorized(req) {
    if (!this.#token || !this.#tokenStatus.healthy) {
      return false;
    }
    const header = req.headers.authorization || '';
    return header === `Bearer ${this.#token}`;
  }
}
