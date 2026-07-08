/**
 * Media Upload Pipeline
 *
 * High-level API for uploading media (images, files, videos) to WeChat.
 * Handles the full flow: prepare → getUploadUrl → CDN encrypt+upload → build message item.
 */

import { readFile } from 'node:fs/promises';
import { basename } from 'node:path';
import { randomBytes } from 'node:crypto';
import { prepareUpload, encodeAesKeyForMessage } from './media-crypto.js';

/** Media type constants matching WeChat API */
export const MEDIA_TYPE = {
  IMAGE: 1,
  VIDEO: 2,
  FILE: 3,
  VOICE: 4,
};

/** Max upload size: 100 MB */
const MAX_UPLOAD_SIZE = 100 * 1024 * 1024;

/** CDN upload retry config */
const CDN_MAX_RETRIES = 3;

/**
 * Upload a file and return a sendMessage-ready item_list entry.
 *
 * @param {import('./api-client.js').WeChatApiClient} client
 * @param {object} opts
 * @param {string} opts.filePath - Path to local file
 * @param {string} opts.toUserId - Recipient WeChat user ID
 * @param {number} [opts.mediaType] - Auto-detected from extension if not provided
 * @param {string} [opts.fileName] - Override file name
 * @returns {Promise<object>} MessageItem for item_list
 */
export async function uploadMedia(client, opts) {
  const { filePath, toUserId } = opts;
  const plaintext = await readFile(filePath);

  if (plaintext.length > MAX_UPLOAD_SIZE) {
    throw new MediaUploadError(`File too large: ${plaintext.length} bytes (max ${MAX_UPLOAD_SIZE})`, 'ERR_WECHAT_FILE_TOO_LARGE');
  }

  const fileName = opts.fileName || basename(filePath);
  const mediaType = opts.mediaType || detectMediaType(fileName);

  // Step 1: Prepare encryption
  const { aesKey, filekey, encryptedData, uploadParams } = prepareUpload(plaintext, mediaType, toUserId);

  // Step 2: Get upload URL
  let uploadResponse;
  try {
    uploadResponse = await client.getUploadUrl(uploadParams);
  } catch (err) {
    throw new MediaUploadError(`getUploadUrl failed: ${err.message}`, 'ERR_WECHAT_UPLOAD_URL');
  }

  if (!uploadResponse.upload_param) {
    throw new MediaUploadError(
      `getUploadUrl returned no upload_param: ret=${uploadResponse.ret} errmsg=${uploadResponse.errmsg}`,
      'ERR_WECHAT_UPLOAD_URL'
    );
  }

  // Step 3: CDN upload with retry
  let downloadParam;
  for (let attempt = 1; attempt <= CDN_MAX_RETRIES; attempt++) {
    try {
      downloadParam = await client.cdnUpload(uploadResponse.upload_param, filekey, encryptedData);
      break;
    } catch (err) {
      // 4xx: abort immediately
      if (err.statusCode && err.statusCode >= 400 && err.statusCode < 500) {
        throw new MediaUploadError(`CDN upload failed (${err.statusCode}): ${err.message}`, 'ERR_WECHAT_CDN_UPLOAD');
      }
      // Last attempt: throw
      if (attempt === CDN_MAX_RETRIES) {
        throw new MediaUploadError(`CDN upload failed after ${CDN_MAX_RETRIES} attempts: ${err.message}`, 'ERR_WECHAT_CDN_UPLOAD');
      }
      // Retry on 5xx / network error
    }
  }

  if (!downloadParam) {
    throw new MediaUploadError('CDN upload returned no x-encrypted-param', 'ERR_WECHAT_CDN_NO_PARAM');
  }

  // Step 4: Build message item
  const encodedAesKey = encodeAesKeyForMessage(aesKey);
  return buildMediaItem(mediaType, {
    downloadParam,
    encodedAesKey,
    ciphertextSize: encryptedData.length,
    plaintextSize: plaintext.length,
    fileName,
  });
}

/**
 * Download and decrypt a media file from CDN.
 *
 * @param {import('./api-client.js').WeChatApiClient} client
 * @param {string} encryptQueryParam - From inbound message media.encrypt_query_param
 * @param {Buffer} aesKey - 16-byte AES key (decoded from message)
 * @returns {Promise<Buffer>} Decrypted file data
 */
export async function downloadMedia(client, encryptQueryParam, aesKey) {
  const { decrypt } = await import('./media-crypto.js');

  const encrypted = await client.cdnDownload(encryptQueryParam);
  return decrypt(encrypted, aesKey);
}

/**
 * Build a MessageItem for a media type.
 */
function buildMediaItem(mediaType, params) {
  const { downloadParam, encodedAesKey, ciphertextSize, plaintextSize, fileName } = params;
  const media = {
    encrypt_query_param: downloadParam,
    aes_key: encodedAesKey,
    encrypt_type: 1,
  };

  switch (mediaType) {
    case MEDIA_TYPE.IMAGE:
      return {
        type: 2,
        image_item: {
          media,
          mid_size: ciphertextSize,
        },
      };

    case MEDIA_TYPE.FILE:
      return {
        type: 4,
        file_item: {
          media,
          file_name: fileName,
          len: String(plaintextSize),
        },
      };

    case MEDIA_TYPE.VIDEO:
      return {
        type: 5,
        video_item: {
          media,
          video_size: ciphertextSize,
        },
      };

    case MEDIA_TYPE.VOICE:
      return {
        type: 3,
        voice_item: {
          media,
        },
      };

    default:
      // Fallback to file
      return {
        type: 4,
        file_item: {
          media,
          file_name: fileName,
          len: String(plaintextSize),
        },
      };
  }
}

/**
 * Detect media type from file extension.
 * @param {string} fileName
 * @returns {number}
 */
function detectMediaType(fileName) {
  const ext = fileName.split('.').pop()?.toLowerCase();
  switch (ext) {
    case 'jpg': case 'jpeg': case 'png': case 'gif': case 'webp': case 'bmp':
      return MEDIA_TYPE.IMAGE;
    case 'mp4': case 'avi': case 'mov': case 'mkv': case 'webm':
      return MEDIA_TYPE.VIDEO;
    case 'mp3': case 'wav': case 'ogg': case 'silk': case 'amr':
      return MEDIA_TYPE.VOICE;
    default:
      return MEDIA_TYPE.FILE;
  }
}

export class MediaUploadError extends Error {
  constructor(message, code) {
    super(message);
    this.name = 'MediaUploadError';
    this.code = code;
  }
}
