import fs from 'fs';
import path from 'path';
import os from 'os';
import dotenv from 'dotenv';

dotenv.config();

const DEFAULT_DATA_DIR = path.join(os.homedir(), 'zylos/components/wechat');
const DEFAULT_C4_RECEIVE_RELATIVE = '.claude/skills/comm-bridge/scripts/c4-receive.js';

function c4ReceiveScriptCandidates() {
  return [
    path.join(os.homedir(), 'zylos', DEFAULT_C4_RECEIVE_RELATIVE),
    path.join(os.homedir(), DEFAULT_C4_RECEIVE_RELATIVE),
    path.resolve(process.cwd(), DEFAULT_C4_RECEIVE_RELATIVE),
    path.resolve(process.cwd(), '..', DEFAULT_C4_RECEIVE_RELATIVE),
    path.resolve(process.cwd(), '..', '..', DEFAULT_C4_RECEIVE_RELATIVE),
  ];
}

function detectExistingC4ReceiveScript() {
  for (const candidate of c4ReceiveScriptCandidates()) {
    if (fs.existsSync(candidate)) return candidate;
  }
  return c4ReceiveScriptCandidates()[0];
}

function resolveC4ReceiveScript(preferredPath) {
  const preferred = resolveHomePath(preferredPath);
  if (preferred && fs.existsSync(preferred)) {
    return preferred;
  }
  return detectExistingC4ReceiveScript();
}

const DEFAULT_CONFIG = {
  enabled: true,
  logLevel: 'info',
  dmPolicy: 'open',
  dmAllowFrom: [],
  admin: {
    enabled: process.env.ZYLOS_WECHAT_ADMIN_ENABLED !== 'false',
    host: process.env.ZYLOS_WECHAT_ADMIN_HOST || '127.0.0.1',
    port: Number(process.env.ZYLOS_WECHAT_ADMIN_PORT || 17605),
  },
  wechat: {
    apiBase: 'https://ilinkai.weixin.qq.com',
    cdnBaseUrl: 'https://novac2c.cdn.weixin.qq.com/c2c',
    channelVersion: '2.1.3',
    appId: 'bot',
    botAgent: '',
  },
  c4: {
    receiveScript: detectExistingC4ReceiveScript(),
  },
};

function resolveHomePath(p) {
  if (!p) return p;
  if (p.startsWith('~/')) return path.join(os.homedir(), p.slice(2));
  return p;
}

function isPlainObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function mergeDeep(base, override) {
  const result = Array.isArray(base) ? [...base] : { ...base };
  for (const [key, value] of Object.entries(override || {})) {
    if (isPlainObject(value) && isPlainObject(result[key])) {
      result[key] = mergeDeep(result[key], value);
    } else {
      result[key] = value;
    }
  }
  return result;
}

function parseIdList(value) {
  if (Array.isArray(value)) {
    return value.map((item) => String(item).trim()).filter(Boolean);
  }
  if (typeof value === 'string') {
    return value.split(',').map((item) => item.trim()).filter(Boolean);
  }
  return [];
}

function readJson(file, fallback) {
  try {
    if (!fs.existsSync(file)) return fallback;
    return JSON.parse(fs.readFileSync(file, 'utf-8'));
  } catch {
    return fallback;
  }
}

const dataDir = resolveHomePath(process.env.ZYLOS_WECHAT_DATA_DIR || DEFAULT_DATA_DIR);

export const paths = {
  dataDir: path.resolve(dataDir),
  accountsDir: path.resolve(dataDir, 'accounts'),
  loginSessionsDir: path.resolve(dataDir, 'login-sessions'),
  logsDir: path.resolve(dataDir, 'logs'),
  mediaDir: path.resolve(dataDir, 'media'),
  configFile: path.resolve(dataDir, 'config.json'),
  stateFile: path.resolve(dataDir, 'state.json'),
  dedupeFile: path.resolve(dataDir, 'dedupe.json'),
  adminTokenFile: path.resolve(dataDir, '.admin-token'),
};

export let config = null;
let configWatcher = null;
let configReloadTimer = null;

function buildEnvOverrides() {
  const overrides = {};

  if (process.env.ZYLOS_WECHAT_ENABLED !== undefined) {
    overrides.enabled = process.env.ZYLOS_WECHAT_ENABLED !== 'false';
  }

  if (process.env.ZYLOS_WECHAT_LOG_LEVEL) {
    overrides.logLevel = process.env.ZYLOS_WECHAT_LOG_LEVEL;
  }

  if (
    process.env.ZYLOS_WECHAT_ADMIN_ENABLED !== undefined ||
    process.env.ZYLOS_WECHAT_ADMIN_HOST ||
    process.env.ZYLOS_WECHAT_ADMIN_PORT
  ) {
    overrides.admin = {};
    if (process.env.ZYLOS_WECHAT_ADMIN_ENABLED !== undefined) {
      overrides.admin.enabled = process.env.ZYLOS_WECHAT_ADMIN_ENABLED !== 'false';
    }
    if (process.env.ZYLOS_WECHAT_ADMIN_HOST) {
      overrides.admin.host = process.env.ZYLOS_WECHAT_ADMIN_HOST;
    }
    if (process.env.ZYLOS_WECHAT_ADMIN_PORT) {
      const parsedPort = Number(process.env.ZYLOS_WECHAT_ADMIN_PORT);
      if (Number.isFinite(parsedPort) && parsedPort > 0) {
        overrides.admin.port = parsedPort;
      }
    }
  }

  if (process.env.ZYLOS_WECHAT_DM_ALLOWLIST !== undefined) {
    overrides.dmAllowFrom = parseIdList(process.env.ZYLOS_WECHAT_DM_ALLOWLIST);
    overrides.dmPolicy = overrides.dmAllowFrom.length > 0 ? 'allowlist' : 'open';
  }

  if (
    process.env.WECHAT_API_BASE || process.env.WECHAT_CDN_BASE_URL ||
    process.env.WECHAT_CHANNEL_VERSION || process.env.WECHAT_APP_ID ||
    process.env.WECHAT_BOT_AGENT
  ) {
    overrides.wechat = {};
    if (process.env.WECHAT_API_BASE) {
      overrides.wechat.apiBase = process.env.WECHAT_API_BASE;
    }
    if (process.env.WECHAT_CDN_BASE_URL) {
      overrides.wechat.cdnBaseUrl = process.env.WECHAT_CDN_BASE_URL;
    }
    if (process.env.WECHAT_CHANNEL_VERSION) {
      overrides.wechat.channelVersion = process.env.WECHAT_CHANNEL_VERSION;
    }
    if (process.env.WECHAT_APP_ID) {
      overrides.wechat.appId = process.env.WECHAT_APP_ID;
    }
    if (process.env.WECHAT_BOT_AGENT) {
      overrides.wechat.botAgent = process.env.WECHAT_BOT_AGENT;
    }
  }

  if (process.env.C4_RECEIVE_SCRIPT) {
    overrides.c4 = { receiveScript: process.env.C4_RECEIVE_SCRIPT };
  }

  return overrides;
}

function normalizeConfig(candidate = {}) {
  const merged = mergeDeep(DEFAULT_CONFIG, candidate);
  const dmAllowFrom = parseIdList(
    merged.dmAllowFrom !== undefined ? merged.dmAllowFrom : merged.dmAllowlist
  );
  const dmPolicy = merged.dmPolicy === 'allowlist' ? 'allowlist' : 'open';
  const c4ReceiveScript = resolveC4ReceiveScript(
    merged.c4?.receiveScript || merged.c4ReceiveScript || DEFAULT_CONFIG.c4.receiveScript
  );

  return {
    enabled: merged.enabled !== false,
    logLevel: typeof merged.logLevel === 'string' && merged.logLevel ? merged.logLevel : 'info',
    dataDir: paths.dataDir,
    dmPolicy,
    dmAllowFrom,
    dmAllowlist: dmAllowFrom,
    admin: {
      enabled: merged.admin?.enabled !== false,
      host:
        typeof merged.admin?.host === 'string' && merged.admin.host
          ? merged.admin.host
          : DEFAULT_CONFIG.admin.host,
      port:
        typeof merged.admin?.port === 'number' &&
        Number.isInteger(merged.admin.port) &&
        merged.admin.port > 0
          ? merged.admin.port
          : DEFAULT_CONFIG.admin.port,
    },
    wechat: {
      apiBase: merged.wechat?.apiBase || DEFAULT_CONFIG.wechat.apiBase,
      cdnBaseUrl: merged.wechat?.cdnBaseUrl || DEFAULT_CONFIG.wechat.cdnBaseUrl,
      channelVersion: merged.wechat?.channelVersion || DEFAULT_CONFIG.wechat.channelVersion,
      appId: merged.wechat?.appId ?? DEFAULT_CONFIG.wechat.appId,
      botAgent: merged.wechat?.botAgent ?? DEFAULT_CONFIG.wechat.botAgent,
    },
    c4: {
      receiveScript: c4ReceiveScript,
    },
    c4ReceiveScript,
  };
}

function serializableConfig(nextConfig = getConfig()) {
  return {
    enabled: nextConfig.enabled,
    logLevel: nextConfig.logLevel,
    dmPolicy: nextConfig.dmPolicy,
    dmAllowFrom: nextConfig.dmAllowFrom,
    admin: {
      enabled: nextConfig.admin?.enabled !== false,
      host: nextConfig.admin?.host || DEFAULT_CONFIG.admin.host,
      port: nextConfig.admin?.port || DEFAULT_CONFIG.admin.port,
    },
    wechat: {
      apiBase: nextConfig.wechat.apiBase,
      cdnBaseUrl: nextConfig.wechat.cdnBaseUrl,
      channelVersion: nextConfig.wechat.channelVersion,
      appId: nextConfig.wechat.appId,
      botAgent: nextConfig.wechat.botAgent,
    },
    c4: {
      receiveScript: nextConfig.c4?.receiveScript || nextConfig.c4ReceiveScript,
    },
  };
}

export function loadConfig() {
  const fileConfig = readJson(paths.configFile, {});
  config = normalizeConfig(mergeDeep(fileConfig, buildEnvOverrides()));
  return config;
}

export function getConfig() {
  if (!config) return loadConfig();
  return config;
}

export function saveConfig(nextConfig) {
  ensureDirs();
  const normalized = normalizeConfig(nextConfig);
  const payload = serializableConfig(normalized);
  const tmpPath = `${paths.configFile}.tmp`;

  try {
    fs.writeFileSync(tmpPath, JSON.stringify(payload, null, 2));
    fs.renameSync(tmpPath, paths.configFile);
    config = normalizeConfig(payload);
    return true;
  } catch {
    try {
      if (fs.existsSync(tmpPath)) fs.unlinkSync(tmpPath);
    } catch {
      // ignore cleanup failure
    }
    return false;
  }
}

export function watchConfig(onChange) {
  stopWatching();

  const configDir = path.dirname(paths.configFile);
  const configBase = path.basename(paths.configFile);

  const scheduleReload = () => {
    if (configReloadTimer) clearTimeout(configReloadTimer);
    configReloadTimer = setTimeout(() => {
      configReloadTimer = null;
      const nextConfig = loadConfig();
      onChange?.(nextConfig);
    }, 100);
  };

  if (!fs.existsSync(configDir)) return;

  configWatcher = fs.watch(configDir, (eventType, filename) => {
    if (filename && String(filename) === configBase) {
      scheduleReload();
    }
  });

  configWatcher.on('error', () => {
    stopWatching();
  });
}

export function stopWatching() {
  if (configReloadTimer) {
    clearTimeout(configReloadTimer);
    configReloadTimer = null;
  }

  if (configWatcher) {
    configWatcher.close();
    configWatcher = null;
  }
}

export function ensureDirs() {
  fs.mkdirSync(paths.dataDir, { recursive: true });
  fs.mkdirSync(paths.accountsDir, { recursive: true });
  fs.mkdirSync(paths.loginSessionsDir, { recursive: true });
  fs.mkdirSync(paths.logsDir, { recursive: true });
  fs.mkdirSync(paths.mediaDir, { recursive: true });
}

export function loadJson(file, fallback) {
  return readJson(file, fallback);
}

export function saveJson(file, data) {
  fs.writeFileSync(file, JSON.stringify(data, null, 2));
}

config = loadConfig();
