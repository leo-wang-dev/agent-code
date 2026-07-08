#!/usr/bin/env node
import { redactToken, redactBody, redactUrl } from '../src/lib/redact.js';

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

console.log('Test 1: redactToken');
assert(redactToken(null) === '(none)', 'null → (none)');
assert(redactToken('') === '(none)', 'empty → (none)');
assert(redactToken('abc') === '****(len=3)', 'short token masked');
assert(redactToken('abcdefghijklmnop') === 'abcdef…(len=16)', 'long token shows prefix');
assert(redactToken('abcdefghij', 4) === 'abcd…(len=10)', 'custom prefix length');

console.log('Test 2: redactBody');
assert(redactBody(null) === '(empty)', 'null → (empty)');
assert(redactBody('') === '(empty)', 'empty → (empty)');
assert(redactBody('plain text') === 'plain text', 'plain text unchanged');
assert(
  redactBody('{"token":"secret123"}').includes('"token":"<redacted>"'),
  'token field redacted',
);
assert(
  redactBody('{"context_token":"abc","name":"test"}').includes('"context_token":"<redacted>"'),
  'context_token redacted',
);
assert(
  redactBody('{"Authorization":"Bearer xyz"}').includes('"Authorization":"<redacted>"'),
  'Authorization redacted',
);
assert(
  redactBody('{"bot_token":"t123","data":"ok"}').includes('"bot_token":"<redacted>"'),
  'bot_token redacted',
);
assert(
  !redactBody('{"my_field":"value"}').includes('<redacted>'),
  'non-sensitive fields untouched',
);
const longBody = 'a'.repeat(300);
const truncated = redactBody(longBody);
assert(truncated.length < 300 && truncated.includes('truncated'), 'long body truncated');

console.log('Test 3: redactUrl');
assert(redactUrl('https://example.com/api/path') === 'https://example.com/api/path', 'URL without query unchanged');
assert(redactUrl('https://example.com/api?token=secret') === 'https://example.com/api?<redacted>', 'query params redacted');
assert(redactUrl('not a url') === 'not a url', 'invalid URL returned as-is');
assert(redactUrl('') === '', 'empty string');
assert(redactUrl(null) === '', 'null → empty');
const longUrl = 'x'.repeat(100);
assert(redactUrl(longUrl).includes('…'), 'long non-URL truncated');

console.log(`\n${passed} passed, ${failed} failed`);
if (failed > 0) process.exit(1);
