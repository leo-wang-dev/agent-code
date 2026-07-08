#!/usr/bin/env node
import { AccountStore } from './lib/account-store.js';
import { WeChatApiClient } from './lib/api-client.js';
import { qrLogin } from './lib/qr-login.js';
import { getConfig, paths, saveConfig } from './lib/config.js';

const store = new AccountStore(paths.dataDir);

function usage() {
  console.log('Usage: node src/admin.js <command> [args]');
  console.log('Commands:');
  console.log('  show');
  console.log('  list-accounts');
  console.log('  login');
  console.log('  remove-account <normalized_id>');
  console.log('  set-dm-policy <open|allowlist>');
  console.log('  list-dm-allow');
  console.log('  add-dm-allow <wechat_user_id>');
  console.log('  remove-dm-allow <wechat_user_id>');
}

function fail(message) {
  console.error(message);
  process.exit(1);
}

function printConfig(cfg) {
  console.log(JSON.stringify({
    enabled: cfg.enabled,
    logLevel: cfg.logLevel,
    dmPolicy: cfg.dmPolicy,
    dmAllowFrom: cfg.dmAllowFrom,
    wechat: cfg.wechat,
    c4: cfg.c4,
  }, null, 2));
}

async function show() {
  printConfig(getConfig());
}

async function listAccounts() {
  await store.init();
  const accounts = await store.loadAllAccounts();
  if (accounts.length === 0) {
    console.log('No WeChat accounts configured');
    return;
  }

  for (const account of accounts) {
    console.log(`${account.normalizedId} raw=${account.accountId || account.normalizedId} savedAt=${account.savedAt || 'unknown'} userId=${account.userId || ''}`);
  }
}

async function login() {
  await store.init();

  const cfg = getConfig();
  const client = new WeChatApiClient({
    baseUrl: cfg.wechat.apiBase,
    cdnBaseUrl: cfg.wechat.cdnBaseUrl,
    channelVersion: cfg.wechat.channelVersion,
    appId: cfg.wechat.appId,
    botAgent: cfg.wechat.botAgent,
  });

  const creds = await qrLogin(client, {
    onQrUrl: (url) => {
      console.log('QR URL:');
      console.log(url);
    },
    onStatus: (status) => {
      console.log(status);
    },
  });

  await store.saveCredentials(creds);
  console.log(`Saved account: ${creds.normalizedId}`);
  console.log('If service is already running, it should pick up the new account within 10 seconds.');
}

async function removeAccount(normalizedId) {
  if (!normalizedId) fail('Usage: node src/admin.js remove-account <normalized_id>');
  await store.init();
  await store.removeAccount(normalizedId);
  console.log(`Removed account: ${normalizedId}`);
  console.log('If service is running, it should stop this account poller within 10 seconds.');
}

async function setDmPolicy(policy) {
  if (!policy || !['open', 'allowlist'].includes(policy)) {
    fail('Usage: node src/admin.js set-dm-policy <open|allowlist>');
  }
  const cfg = getConfig();
  const next = {
    ...cfg,
    dmPolicy: policy,
  };
  if (!saveConfig(next)) {
    fail('Failed to save config');
  }
  console.log(`dmPolicy set to ${policy}`);
}

async function listDmAllow() {
  const cfg = getConfig();
  console.log(`dmPolicy: ${cfg.dmPolicy}`);
  console.log(`dmAllowFrom (${cfg.dmAllowFrom.length}): ${cfg.dmAllowFrom.length ? cfg.dmAllowFrom.join(', ') : 'none'}`);
}

async function addDmAllow(userId) {
  if (!userId) fail('Usage: node src/admin.js add-dm-allow <wechat_user_id>');
  const cfg = getConfig();
  const nextAllow = [...new Set([...cfg.dmAllowFrom, userId])];
  const next = {
    ...cfg,
    dmPolicy: cfg.dmPolicy,
    dmAllowFrom: nextAllow,
  };
  if (!saveConfig(next)) {
    fail('Failed to save config');
  }
  console.log(`Added ${userId} to dmAllowFrom`);
}

async function removeDmAllow(userId) {
  if (!userId) fail('Usage: node src/admin.js remove-dm-allow <wechat_user_id>');
  const cfg = getConfig();
  const nextAllow = cfg.dmAllowFrom.filter((id) => id !== userId);
  const next = {
    ...cfg,
    dmAllowFrom: nextAllow,
  };
  if (!saveConfig(next)) {
    fail('Failed to save config');
  }
  console.log(`Removed ${userId} from dmAllowFrom`);
}

const commands = {
  show,
  'list-accounts': listAccounts,
  login,
  'remove-account': removeAccount,
  'set-dm-policy': setDmPolicy,
  'list-dm-allow': listDmAllow,
  'add-dm-allow': addDmAllow,
  'remove-dm-allow': removeDmAllow,
};

const [command, ...args] = process.argv.slice(2);

if (!command || !commands[command]) {
  usage();
  process.exit(command ? 1 : 0);
}

commands[command](...args).catch((err) => {
  console.error(err.message);
  process.exit(1);
});
