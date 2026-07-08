#!/usr/bin/env node
/**
 * Crypto roundtrip test for media-crypto.js
 * Verifies encrypt/decrypt and key encoding are consistent.
 */

import { readFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  generateAesKey,
  generateFileKey,
  md5,
  ciphertextSize,
  encrypt,
  decrypt,
  encodeAesKeyForMessage,
  decodeAesKey,
  prepareUpload,
} from '../src/lib/media-crypto.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
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

// --- Test 1: Basic encrypt/decrypt roundtrip ---
console.log('Test 1: encrypt/decrypt roundtrip');
{
  const key = generateAesKey();
  const plaintext = Buffer.from('Hello WeChat media crypto!');
  const ciphertext = encrypt(plaintext, key);
  const decrypted = decrypt(ciphertext, key);

  assert(Buffer.compare(plaintext, decrypted) === 0, 'decrypt(encrypt(data)) === data');
  assert(ciphertext.length === ciphertextSize(plaintext.length), 'ciphertext size matches formula');
  assert(ciphertext.length % 16 === 0, 'ciphertext is block-aligned');
}

// --- Test 2: Key encoding roundtrip ---
console.log('Test 2: AES key encoding roundtrip');
{
  const key = generateAesKey();
  const encoded = encodeAesKeyForMessage(key);
  const decoded = decodeAesKey(encoded);

  assert(Buffer.compare(key, decoded) === 0, 'decodeAesKey(encodeAesKeyForMessage(key)) === key');
  assert(typeof encoded === 'string', 'encoded key is a string');
  assert(encoded.length > 0, 'encoded key is non-empty');
}

// --- Test 3: File fixtures roundtrip ---
console.log('Test 3: fixture file roundtrip');
for (const fixture of ['tiny.png', 'tiny.txt']) {
  const filePath = join(__dirname, 'fixtures', fixture);
  let plaintext;
  try {
    plaintext = readFileSync(filePath);
  } catch {
    console.log(`  (skipping ${fixture} — not found)`);
    continue;
  }

  const key = generateAesKey();
  const originalMd5 = md5(plaintext);
  const ciphertext = encrypt(plaintext, key);
  const decrypted = decrypt(ciphertext, key);
  const decryptedMd5 = md5(decrypted);

  assert(originalMd5 === decryptedMd5, `${fixture}: MD5 matches after roundtrip`);
  assert(Buffer.compare(plaintext, decrypted) === 0, `${fixture}: byte-level match`);
}

// --- Test 4: prepareUpload output ---
console.log('Test 4: prepareUpload');
{
  const plaintext = Buffer.from('test file content for upload');
  const result = prepareUpload(plaintext, 3, 'test-user-id');

  assert(result.aesKey.length === 16, 'aesKey is 16 bytes');
  assert(result.filekey.length === 32, 'filekey is 32-char hex');
  assert(result.encryptedData.length === ciphertextSize(plaintext.length), 'encryptedData size correct');
  assert(result.uploadParams.filekey === result.filekey, 'uploadParams.filekey matches');
  assert(result.uploadParams.media_type === 3, 'media_type = FILE');
  assert(result.uploadParams.to_user_id === 'test-user-id', 'to_user_id correct');
  assert(result.uploadParams.rawsize === plaintext.length, 'rawsize = plaintext length');
  assert(result.uploadParams.filesize === result.encryptedData.length, 'filesize = ciphertext length');
  assert(result.uploadParams.rawfilemd5 === md5(plaintext), 'rawfilemd5 matches');
  assert(result.uploadParams.aeskey.length === 32, 'aeskey is 32-char hex');
  assert(result.uploadParams.no_need_thumb === true, 'no_need_thumb is true');

  // Verify encrypt/decrypt with the generated key
  const decrypted = decrypt(result.encryptedData, result.aesKey);
  assert(Buffer.compare(plaintext, decrypted) === 0, 'prepareUpload encryption is reversible');
}

// --- Test 5: generateFileKey uniqueness ---
console.log('Test 5: filekey uniqueness');
{
  const keys = new Set();
  for (let i = 0; i < 100; i++) {
    keys.add(generateFileKey());
  }
  assert(keys.size === 100, '100 filekeys are all unique');
}

// --- Test 6: decodeAesKey handles both formats ---
console.log('Test 6: decodeAesKey format handling');
{
  const key = generateAesKey();

  // Format 1: base64(raw 16 bytes) — image format
  const raw64 = key.toString('base64');
  const decoded1 = decodeAesKey(raw64);
  assert(Buffer.compare(key, decoded1) === 0, 'decodes base64(raw 16 bytes)');

  // Format 2: base64(hex string) — file/voice/video format
  const hex64 = Buffer.from(key.toString('hex')).toString('base64');
  const decoded2 = decodeAesKey(hex64);
  assert(Buffer.compare(key, decoded2) === 0, 'decodes base64(hex string)');

  // Format 3: raw hex key (image_item.aeskey)
  const rawHex = key.toString('hex');
  const decoded3 = decodeAesKey('ignored', rawHex);
  assert(Buffer.compare(key, decoded3) === 0, 'decodes raw hex key (priority)');
}

// --- Summary ---
console.log(`\n${passed} passed, ${failed} failed`);
process.exit(failed > 0 ? 1 : 0);
