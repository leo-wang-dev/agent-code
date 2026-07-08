#!/usr/bin/env node
/**
 * Outbound send script for zylos-wechat.
 *
 * Called by C4 comm-bridge via c4-send.js:
 *   node scripts/send.js <endpoint_id> "<message>"
 *   echo "message" | node scripts/send.js <endpoint_id>
 *
 * Or directly:
 *   node scripts/send.js --to <wechat_id> --text <message> --context-token <token> [--account <normalized_id>]
 *
 * Media send (C4 format):
 *   echo "[MEDIA:image]/path/to/image.png" | node scripts/send.js <endpoint_id>
 *   echo "[MEDIA:file]/path/to/doc.pdf" | node scripts/send.js <endpoint_id>
 *
 * The endpoint_id format from C4: "<normalized_account_id>|to:<wechat_user_id>"
 * Context token is loaded from the account's token cache if available.
 */

import { randomBytes } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import { join } from 'node:path';
import { WeChatApiClient } from '../src/lib/api-client.js';
import { AccountStore } from '../src/lib/account-store.js';
import { ContextTokenStore } from '../src/lib/context-tokens.js';
import { getConfig } from '../src/lib/config.js';
import { uploadMedia, MEDIA_TYPE } from '../src/lib/media-upload.js';

const DATA_DIR = process.env.ZYLOS_WECHAT_DATA_DIR
  || join(process.env.HOME || '', 'zylos/components/wechat');

function arg(name) {
  const i = process.argv.indexOf(name);
  if (i < 0) return '';
  return process.argv[i + 1] || '';
}

async function readStdin() {
  const chunks = [];
  for await (const chunk of process.stdin) {
    chunks.push(chunk);
  }
  return Buffer.concat(chunks).toString('utf8').trim();
}

async function stopTypingViaAdmin(userId) {
  try {
    const cfg = getConfig();
    const host = cfg.admin?.host || '127.0.0.1';
    const port = cfg.admin?.port || 17605;
    const tokenPath = join(DATA_DIR, '.admin-token');
    const token = (await readFile(tokenPath, 'utf8')).trim();
    const res = await fetch(`http://${host}:${port}/v1/typing/stop`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({ userId }),
      signal: AbortSignal.timeout(3_000),
    });
    if (!res.ok) {
      const text = await res.text().catch(() => '');
      console.error(`typing/stop: HTTP ${res.status} ${text}`);
    }
  } catch {
    // Non-critical: admin server may not be running (e.g. standalone send)
  }
}

async function main() {
  let to;
  let text;
  let contextToken;
  let accountId;

  const endpointArg = process.argv[2];
  const hasFlags = process.argv.includes('--to') || process.argv.includes('--text');

  if (endpointArg && !hasFlags && !endpointArg.startsWith('-')) {
    const parts = endpointArg.split('|');
    if (parts.length >= 2) {
      accountId = parts[0];
      const toPart = parts.find((p) => p.startsWith('to:'));
      to = toPart ? toPart.slice(3) : parts[1];
    } else {
      to = endpointArg;
    }

    const messageArg = process.argv.slice(3).join(' ').trim();
    text = messageArg || await readStdin();
    if (!text) {
      console.error('No message provided (expected argv[3] or stdin)');
      process.exit(1);
    }
  } else {
    to = arg('--to');
    text = arg('--text');
    contextToken = arg('--context-token');
    accountId = arg('--account');
  }

  if (!to || !text) {
    console.error('Usage:');
    console.error('  node scripts/send.js <endpoint_id> "<message>"');
    console.error('  echo "message" | node scripts/send.js <endpoint_id>');
    console.error('  node scripts/send.js --to <wechat_id> --text <message> --context-token <token> [--account <normalized_id>]');
    process.exit(1);
  }

  const store = new AccountStore(DATA_DIR);
  await store.init();
  const accounts = await store.loadAllAccounts();

  let creds;
  if (accountId) {
    creds = await store.loadCredentials(accountId);
    if (!creds) {
      console.error(`ERR_WECHAT_AUTH: Account not found: ${accountId}`);
      process.exit(1);
    }
  } else if (accounts.length === 1) {
    creds = accounts[0];
    accountId = creds.normalizedId;
  } else if (accounts.length > 1) {
    console.error('ERR_WECHAT_ACCOUNT_REQUIRED: Multiple accounts configured');
    console.error('Use an endpoint like "<account>|to:<wechat_user_id>" or pass --account <normalized_id>.');
    process.exit(1);
  }

  if (!creds || !creds.token) {
    console.error('ERR_WECHAT_AUTH: No account credentials found');
    process.exit(1);
  }

  if (!contextToken) {
    const tokenCachePath = join(DATA_DIR, 'context-tokens.json');
    const tokenStore = ContextTokenStore.fromDisk(tokenCachePath);
    contextToken = tokenStore.get(accountId, to);
    if (!contextToken && creds.accountId && creds.accountId !== accountId) {
      contextToken = tokenStore.get(creds.accountId, to);
    }

    if (!contextToken) {
      console.error('ERR_CONTEXT_TOKEN_MISSING: No context_token found for this user');
      console.error('The user must send a message first so the service can cache their context_token.');
      console.error('Or provide --context-token explicitly.');
      process.exit(1);
    }
  }

  const cfg = getConfig();
  const client = new WeChatApiClient({
    token: creds.token,
    baseUrl: creds.baseUrl,
    channelVersion: cfg.wechat.channelVersion,
    appId: cfg.wechat.appId,
    botAgent: cfg.wechat.botAgent,
  });

  const mediaMatch = text.match(/^\[MEDIA:(\w+)\](.+)$/);

  if (mediaMatch) {
    const mediaTypeStr = mediaMatch[1].toLowerCase();
    const mediaPath = mediaMatch[2].trim();
    const typeMap = {
      image: MEDIA_TYPE.IMAGE,
      video: MEDIA_TYPE.VIDEO,
      file: MEDIA_TYPE.FILE,
      voice: MEDIA_TYPE.VOICE,
    };
    const mediaType = typeMap[mediaTypeStr];
    if (!mediaType) {
      console.error(`Unknown media type: "${mediaTypeStr}". Use: image, video, file, voice`);
      process.exit(1);
    }

    const mediaItem = await uploadMedia(client, {
      filePath: mediaPath,
      toUserId: to,
      mediaType,
    });

    const clientId = `zylos-wechat:${Date.now()}-${randomBytes(4).toString('hex')}`;
    const resp = await client.sendMessage({
      from_user_id: '',
      to_user_id: to,
      client_id: clientId,
      message_type: 2,
      message_state: 2,
      context_token: contextToken,
      item_list: [mediaItem],
    });

    if (resp.ret !== undefined && resp.ret !== 0) {
      console.error(`WeChat API error: ret=${resp.ret} errcode=${resp.errcode} errmsg=${resp.errmsg}`);
      process.exit(1);
    }
  } else {
    const clientId = `zylos-wechat:${Date.now()}-${randomBytes(4).toString('hex')}`;
    const MAX_CHARS = 4000;
    const chunks = [];
    for (let i = 0; i < text.length; i += MAX_CHARS) {
      chunks.push(text.slice(i, i + MAX_CHARS));
    }

    for (let i = 0; i < chunks.length; i++) {
      const resp = await client.sendMessage({
        from_user_id: '',
        to_user_id: to,
        client_id: `${clientId}-${i}`,
        message_type: 2,
        message_state: 2,
        context_token: contextToken,
        item_list: [{ type: 1, text_item: { text: chunks[i] } }],
      });

      if (resp.ret !== undefined && resp.ret !== 0) {
        console.error(`WeChat API error: ret=${resp.ret} errcode=${resp.errcode} errmsg=${resp.errmsg}`);
        process.exit(1);
      }
    }
  }

  await stopTypingViaAdmin(to);

  console.log('OK');
}

main().catch((err) => {
  console.error(err.message);
  process.exit(1);
});
