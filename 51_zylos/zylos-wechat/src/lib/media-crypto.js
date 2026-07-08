/**
 * Media Crypto
 *
 * AES-128-ECB encryption/decryption for WeChat CDN media uploads/downloads.
 * Handles key generation, PKCS7 padding, and the WeChat-specific key encoding.
 */

import { randomBytes, createCipheriv, createDecipheriv, createHash } from 'node:crypto';

const AES_BLOCK_SIZE = 16;

/**
 * Generate a random AES-128 key.
 * @returns {Buffer} 16-byte key
 */
export function generateAesKey() {
  return randomBytes(AES_BLOCK_SIZE);
}

/**
 * Generate a random file key.
 * @returns {string} 32-char hex string
 */
export function generateFileKey() {
  return randomBytes(AES_BLOCK_SIZE).toString('hex');
}

/**
 * Calculate MD5 hash of data.
 * @param {Buffer} data
 * @returns {string} 32-char hex md5
 */
export function md5(data) {
  return createHash('md5').update(data).digest('hex');
}

/**
 * Calculate the ciphertext size for a given plaintext size (PKCS7 padding).
 * @param {number} plaintextSize
 * @returns {number}
 */
export function ciphertextSize(plaintextSize) {
  return Math.ceil((plaintextSize + 1) / AES_BLOCK_SIZE) * AES_BLOCK_SIZE;
}

/**
 * Encrypt data with AES-128-ECB (PKCS7 padding).
 * @param {Buffer} plaintext
 * @param {Buffer} aesKey - 16-byte key
 * @returns {Buffer} Ciphertext
 */
export function encrypt(plaintext, aesKey) {
  const cipher = createCipheriv('aes-128-ecb', aesKey, null);
  return Buffer.concat([cipher.update(plaintext), cipher.final()]);
}

/**
 * Decrypt data with AES-128-ECB (PKCS7 padding).
 * @param {Buffer} ciphertext
 * @param {Buffer} aesKey - 16-byte key
 * @returns {Buffer} Plaintext
 */
export function decrypt(ciphertext, aesKey) {
  const decipher = createDecipheriv('aes-128-ecb', aesKey, null);
  return Buffer.concat([decipher.update(ciphertext), decipher.final()]);
}

/**
 * Encode AES key for the sendMessage `media.aes_key` field.
 * WeChat format: base64(hex-string-of-key-bytes)
 * @param {Buffer} aesKey - 16-byte key
 * @returns {string}
 */
export function encodeAesKeyForMessage(aesKey) {
  return Buffer.from(aesKey.toString('hex')).toString('base64');
}

/**
 * Decode AES key from inbound message `media.aes_key` field.
 * Two formats in the wild:
 * - base64(raw 16 bytes) — images
 * - base64(hex string of 16 bytes) — file/voice/video
 *
 * @param {string} encoded - base64-encoded aes_key
 * @param {string} [rawHexKey] - If available (image_item.aeskey), use this instead
 * @returns {Buffer} 16-byte key
 */
export function decodeAesKey(encoded, rawHexKey) {
  if (rawHexKey) {
    // Direct hex string (from image_item.aeskey)
    return Buffer.from(rawHexKey, 'hex');
  }

  const decoded = Buffer.from(encoded, 'base64');

  if (decoded.length === AES_BLOCK_SIZE) {
    // Raw 16 bytes — image format
    return decoded;
  }

  if (decoded.length === AES_BLOCK_SIZE * 2) {
    // Hex string (32 ASCII chars) — file/voice/video format
    return Buffer.from(decoded.toString('ascii'), 'hex');
  }

  // Fallback: try as-is
  return decoded;
}

/**
 * Prepare upload parameters for a file.
 * @param {Buffer} plaintext - File data
 * @param {number} mediaType - 1=IMAGE, 2=VIDEO, 3=FILE, 4=VOICE
 * @param {string} toUserId - Recipient
 * @returns {object} { aesKey, filekey, uploadParams, encryptedData }
 */
export function prepareUpload(plaintext, mediaType, toUserId) {
  const aesKey = generateAesKey();
  const filekey = generateFileKey();
  const rawfilemd5 = md5(plaintext);
  const encryptedData = encrypt(plaintext, aesKey);

  return {
    aesKey,
    filekey,
    encryptedData,
    uploadParams: {
      filekey,
      media_type: mediaType,
      to_user_id: toUserId,
      rawsize: plaintext.length,
      rawfilemd5,
      filesize: encryptedData.length,
      no_need_thumb: true,
      aeskey: aesKey.toString('hex'),
    },
  };
}
