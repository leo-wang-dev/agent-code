#!/usr/bin/env node
import { join } from 'node:path';
import { ensureDirs, getConfig, paths, stopWatching, watchConfig } from './lib/config.js';
import { createLogger } from './lib/logger.js';
import { sendToC4 } from './lib/bridge.js';
import { AccountManager } from './lib/account-manager.js';
import { ContextTokenStore } from './lib/context-tokens.js';
import { TypingManager } from './lib/typing.js';
import { WeChatApiClient } from './lib/api-client.js';
import { RuntimeHealthStore } from './lib/runtime-health-store.js';
import { LoginSessionStore } from './lib/login-session-store.js';
import { AdminServer } from './lib/admin-server.js';
import {
  downloadInboundMedia,
  extractTextBody,
  formatInboundContent,
  pickInboundMediaItem,
} from './lib/inbound-media.js';

let runtimeConfig = getConfig();
let logger = createLogger(runtimeConfig.logLevel);

if (!runtimeConfig.enabled) {
  logger.info('component disabled by config');
  process.exit(0);
}

ensureDirs();

const dataDir = paths.dataDir;
const manager = new AccountManager(dataDir, {
  channelVersion: runtimeConfig.wechat.channelVersion,
  appId: runtimeConfig.wechat.appId,
  botAgent: runtimeConfig.wechat.botAgent,
  logger,
});
const contextTokens = new ContextTokenStore({
  persistPath: join(dataDir, 'context-tokens.json'),
});
const runtimeHealth = new RuntimeHealthStore(dataDir);
const loginSessions = new LoginSessionStore({
  dataDir,
  logger,
  qrClientFactory: () =>
    new WeChatApiClient({
      baseUrl: runtimeConfig.wechat.apiBase,
      cdnBaseUrl: runtimeConfig.wechat.cdnBaseUrl,
      channelVersion: runtimeConfig.wechat.channelVersion,
      appId: runtimeConfig.wechat.appId,
      botAgent: runtimeConfig.wechat.botAgent,
      logger,
    }),
});
const typingManagers = new Map(); // raw accountId -> TypingManager

const seenMessages = new Set();
const DEDUPE_MAX = 10_000;
const ACCOUNT_RECONCILE_INTERVAL_MS = 10_000;
const REPLYABILITY_REFRESH_INTERVAL_MS = 60_000;
let shuttingDown = false;
let reconcileTimer = null;
let replyabilityTimer = null;
let adminServer = null;

function markSeen(key) {
  seenMessages.add(key);
  if (seenMessages.size > DEDUPE_MAX) {
    const recent = [...seenMessages].slice(-Math.floor(DEDUPE_MAX * 0.9));
    seenMessages.clear();
    for (const value of recent) {
      seenMessages.add(value);
    }
  }
}

function isDmAllowed(userId) {
  if (runtimeConfig.dmPolicy !== 'allowlist') return true;
  return runtimeConfig.dmAllowFrom.includes(userId);
}

function extractText(msg) {
  return extractTextBody(msg.item_list);
}

function latestContextState(normalizedId, rawAccountId) {
  const latest = contextTokens.latestTimestampForAccount(normalizedId, [rawAccountId]);
  if (!latest) {
    return {
      replyability: 'needs_user_message',
      lastContextAt: null,
    };
  }
  return {
    replyability: 'replyable',
    lastContextAt: new Date(latest).toISOString(),
  };
}

async function syncAccountReplyability(normalizedId, rawAccountId) {
  const runtime = await runtimeHealth.load(normalizedId);
  if (!runtime) return;
  const contextState = latestContextState(normalizedId, rawAccountId);
  await runtimeHealth.upsert(normalizedId, {
    accountId: rawAccountId,
    replyability: contextState.replyability,
    lastContextAt: contextState.lastContextAt,
  });
}

async function handleMessages(msgs, accountId, normalizedId) {
  for (const msg of msgs) {
    if (msg.message_type === 2) continue;
    if (msg.message_state !== undefined && msg.message_state !== 2) continue;

    const msgId = String(msg.message_id || msg.seq || '');
    if (!msgId) continue;

    const dedupeKey = `${accountId}:${msgId}`;
    if (seenMessages.has(dedupeKey)) continue;

    const fromUserId = msg.from_user_id || '';
    const receivedAt = new Date().toISOString();

    if (msg.context_token && fromUserId) {
      contextTokens.set(normalizedId, fromUserId, msg.context_token);
    }

    await runtimeHealth.upsert(normalizedId, {
      accountId,
      loginHealth: 'healthy',
      lastPollAt: receivedAt,
      lastPollErrorCode: null,
      lastPollErrorMessage: null,
      lastInboundAt: receivedAt,
      ...latestContextState(normalizedId, accountId),
    });

    if (!isDmAllowed(fromUserId)) {
      logger.debug('drop from non-allowlisted user:', fromUserId);
      markSeen(dedupeKey);
      continue;
    }

    const client = manager.getClient(normalizedId);
    const mediaItem = pickInboundMediaItem(msg.item_list);
    const mediaResult = mediaItem && client
      ? await downloadInboundMedia(client, mediaItem, {
          mediaDir: paths.mediaDir,
          logger,
          label: 'inbound',
        })
      : {};

    const text = extractText(msg);
    const endpoint = fromUserId ? `${normalizedId}|to:${fromUserId}` : normalizedId;
    const content = mediaItem || text
      ? formatInboundContent(msg, mediaResult)
      : `[WeChat DM] ${fromUserId} said: ${text}`;

    const typingMgr = typingManagers.get(accountId);
    if (typingMgr && fromUserId) {
      typingMgr.startTyping(fromUserId, msg.context_token).catch(() => {});
    }

    try {
      await sendToC4({
        scriptPath: runtimeConfig.c4ReceiveScript,
        channel: 'wechat',
        endpoint,
        content,
        logger,
      });
    } catch (err) {
      logger.error('C4 dispatch failed:', err.message);
      if (typingMgr && fromUserId) {
        typingMgr.stopTyping(fromUserId).catch(() => {});
      }
    }

    markSeen(dedupeKey);
  }
}

async function main() {
  logger.info('zylos-wechat starting...');
  logger.info('data dir:', dataDir);

  watchConfig((nextConfig) => {
    runtimeConfig = nextConfig;
    logger = createLogger(runtimeConfig.logLevel);
    logger.info('config reloaded');

    if (!runtimeConfig.enabled) {
      logger.info('component disabled in config, shutting down');
      shutdown('CONFIG_DISABLED');
    }
  });

  await manager.init();
  await loginSessions.init();

  manager.on('error', (err, acctId, normalizedId) => {
    logger.error(`[${acctId}] error:`, err.message);
    if (normalizedId) {
      void runtimeHealth.upsert(normalizedId, {
        accountId: acctId,
        loginHealth: 'degraded',
        lastPollAt: new Date().toISOString(),
        lastPollErrorCode: 'WECHAT_POLL_ERROR',
        lastPollErrorMessage: err.message,
        ...latestContextState(normalizedId, acctId),
      });
    }
  });

  manager.on('session-expired', (acctId, normalizedId) => {
    logger.warn(`[${acctId}] session expired - paused for 60 minutes`);
    if (normalizedId) {
      void runtimeHealth.upsert(normalizedId, {
        accountId: acctId,
        loginHealth: 'reauth_required',
        lastPollAt: new Date().toISOString(),
        lastPollErrorCode: 'WECHAT_SESSION_EXPIRED',
        lastPollErrorMessage: 'Session expired and requires QR re-auth',
        replyability: 'unknown',
      });
    }
  });

  manager.on('connected', (acctId, normalizedId) => {
    logger.info(`[${acctId}] polling started`);
    const client = manager.getClient(normalizedId);
    if (client) {
      typingManagers.set(acctId, new TypingManager(client));
      client.notifyStart().catch((err) => {
        logger.debug(`[${acctId}] notifyStart failed:`, err.message);
      });
    }
    void manager.store.loadCredentials(normalizedId).then((creds) => {
      void runtimeHealth.upsert(normalizedId, {
        accountId: acctId,
        userId: creds?.userId || null,
        savedAt: creds?.savedAt || null,
        loginHealth: 'healthy',
        lastPollAt: new Date().toISOString(),
        lastPollErrorCode: null,
        lastPollErrorMessage: null,
        ...latestContextState(normalizedId, acctId),
      });
    });
  });

  manager.on('disconnected', (acctId, normalizedId) => {
    logger.info(`[${acctId}] polling stopped`);
    const typingMgr = typingManagers.get(acctId);
    if (typingMgr) {
      typingMgr.stopAll();
      typingManagers.delete(acctId);
    }
    if (normalizedId) {
      void runtimeHealth.upsert(normalizedId, {
        accountId: acctId,
        loginHealth: 'degraded',
        lastPollAt: new Date().toISOString(),
        ...latestContextState(normalizedId, acctId),
      });
    }
  });

  await manager.startAll(handleMessages);

  reconcileTimer = setInterval(() => {
    if (shuttingDown) return;

    manager.reconcile(handleMessages).catch((err) => {
      logger.error('account reconcile failed:', err.message);
    });
  }, ACCOUNT_RECONCILE_INTERVAL_MS);
  reconcileTimer.unref?.();

  replyabilityTimer = setInterval(() => {
    if (shuttingDown) return;
    contextTokens.cleanup();
    for (const account of manager.listAccounts()) {
      void syncAccountReplyability(account.normalizedId, account.accountId);
    }
  }, REPLYABILITY_REFRESH_INTERVAL_MS);
  replyabilityTimer.unref?.();

  if (runtimeConfig.admin?.enabled !== false) {
    adminServer = new AdminServer({
      host: runtimeConfig.admin.host,
      port: runtimeConfig.admin.port,
      tokenPath: paths.adminTokenFile,
      logger,
      getConfig: () => runtimeConfig,
      accountManager: manager,
      accountStore: manager.store,
      contextTokens,
      loginSessions,
      runtimeHealth,
      reconcileAccounts: () => manager.reconcileCurrent(),
      typingManagers,
    });
    await adminServer.start();
  }

  const accounts = manager.listAccounts();
  if (accounts.length === 0) {
    logger.info('no accounts configured - waiting for QR login via admin CLI');
  } else {
    logger.info(`${accounts.length} account(s) active`);
  }
}

function shutdown(sig) {
  if (shuttingDown) return;
  shuttingDown = true;

  logger.info(`received ${sig}, shutting down...`);
  stopWatching();
  if (reconcileTimer) {
    clearInterval(reconcileTimer);
    reconcileTimer = null;
  }
  if (replyabilityTimer) {
    clearInterval(replyabilityTimer);
    replyabilityTimer = null;
  }
  contextTokens.flush();
  loginSessions.stop();
  void adminServer?.close().catch(() => {});

  for (const typingMgr of typingManagers.values()) {
    typingMgr.stopAll();
  }

  const notifyPromises = manager.listAccounts().map((acct) => {
    const client = manager.getClient(acct.normalizedId);
    return client?.notifyStop({ timeout: 3_000 }).catch((err) => {
      logger.debug(`[${acct.accountId}] notifyStop failed:`, err.message);
    });
  });

  Promise.allSettled(notifyPromises).then(() => {
    return manager.stopAll();
  }).then(() => {
    logger.info('all pollers stopped');
    process.exit(0);
  }).catch(() => {
    process.exit(1);
  });

  setTimeout(() => process.exit(0), 5_000);
}

process.on('SIGINT', () => shutdown('SIGINT'));
process.on('SIGTERM', () => shutdown('SIGTERM'));

main().catch((err) => {
  logger.error('fatal:', err.message);
  process.exit(1);
});
