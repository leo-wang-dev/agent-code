#!/usr/bin/env node
/**
 * Tests for api-client.js helper functions: buildClientVersion, sanitizeBotAgent.
 * These are not exported, so we test them indirectly via WeChatApiClient behavior.
 */

import { WeChatApiClient } from '../src/lib/api-client.js';

let passed = 0;
let failed = 0;

function assert(condition, msg) {
  if (condition) {
    passed++;
    console.log(`  ✓ ${msg}`);
  } else {
    failed++;
    console.error(`  ✗ ${msg}`);
  }
}

// We can't test internal functions directly, but we can verify behavior
// through the public API by inspecting what the client sends.

console.log('Test 1: WeChatApiClient defaults');
{
  const client = new WeChatApiClient();
  assert(client.baseUrl === 'https://ilinkai.weixin.qq.com', 'default baseUrl');
  assert(client.cdnBaseUrl === 'https://novac2c.cdn.weixin.qq.com/c2c', 'default cdnBaseUrl');
  assert(client.hasToken === false, 'no token by default');
}

console.log('Test 2: WeChatApiClient with custom opts');
{
  const client = new WeChatApiClient({
    token: 'test-token',
    baseUrl: 'https://custom.api',
    cdnBaseUrl: 'https://custom.cdn',
    channelVersion: '2.4.2',
    appId: 'custom-app',
    botAgent: 'my-bot/1.0.0',
  });
  assert(client.baseUrl === 'https://custom.api', 'custom baseUrl');
  assert(client.cdnBaseUrl === 'https://custom.cdn', 'custom cdnBaseUrl');
  assert(client.hasToken === true, 'token set');
}

console.log('Test 3: WeChatApiClient channelVersion fallback');
{
  const client = new WeChatApiClient({ channelVersion: '' });
  // With empty string, || operator falls back to default '2.1.3'
  // We can't inspect the private field, but the client should construct without error
  assert(client instanceof WeChatApiClient, 'empty channelVersion does not throw');
}

console.log('Test 4: WeChatApiClient botAgent sanitization');
{
  // Invalid botAgent should fall back to default
  const client1 = new WeChatApiClient({ botAgent: '<script>alert(1)</script>' });
  assert(client1 instanceof WeChatApiClient, 'invalid botAgent does not throw');

  const client2 = new WeChatApiClient({ botAgent: '' });
  assert(client2 instanceof WeChatApiClient, 'empty botAgent does not throw');

  const client3 = new WeChatApiClient({ botAgent: null });
  assert(client3 instanceof WeChatApiClient, 'null botAgent does not throw');
}

console.log('Test 5: buildClientVersion encoding (via constructor)');
{
  // Version components > 255 should be clamped, not overflow
  const client = new WeChatApiClient({ channelVersion: '256.300.400' });
  assert(client instanceof WeChatApiClient, 'overflow version does not throw');
}

console.log(`\n${passed} passed, ${failed} failed`);
if (failed > 0) process.exit(1);
