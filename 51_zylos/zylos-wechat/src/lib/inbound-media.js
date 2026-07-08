import { mkdir, writeFile } from 'node:fs/promises';
import { basename, extname, join } from 'node:path';
import { randomBytes } from 'node:crypto';
import { decrypt, decodeAesKey } from './media-crypto.js';

export const MESSAGE_ITEM_TYPE = {
  TEXT: 1,
  IMAGE: 2,
  VOICE: 3,
  FILE: 4,
  VIDEO: 5,
};

const FILE_MIME_BY_EXT = {
  '.csv': 'text/csv',
  '.gif': 'image/gif',
  '.jpeg': 'image/jpeg',
  '.jpg': 'image/jpeg',
  '.json': 'application/json',
  '.mov': 'video/quicktime',
  '.mp3': 'audio/mpeg',
  '.mp4': 'video/mp4',
  '.ogg': 'audio/ogg',
  '.pdf': 'application/pdf',
  '.png': 'image/png',
  '.silk': 'audio/silk',
  '.svg': 'image/svg+xml',
  '.txt': 'text/plain',
  '.wav': 'audio/wav',
  '.webm': 'video/webm',
  '.webp': 'image/webp',
};

function sanitizeFileComponent(value, fallback) {
  const safe = String(value || '')
    .trim()
    .replace(/[/\\?%*:|"<>]/g, '_')
    .replace(/\s+/g, ' ');
  return safe || fallback;
}

function inferExtensionFromUrl(url) {
  if (!url) return '';
  try {
    const parsed = new URL(url);
    return extname(parsed.pathname || '').toLowerCase();
  } catch {
    return '';
  }
}

function inferFileMimeType(fileName) {
  const ext = extname(fileName || '').toLowerCase();
  return FILE_MIME_BY_EXT[ext] || 'application/octet-stream';
}

function buildStoredFilename({ prefix, preferredName, fallbackExt }) {
  const preferredBase = preferredName ? basename(preferredName) : '';
  const safeBase = sanitizeFileComponent(preferredBase, prefix);
  const currentExt = extname(safeBase);
  const ext = currentExt || fallbackExt || '';
  const stem = currentExt ? safeBase.slice(0, -currentExt.length) : safeBase;
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const rand = randomBytes(4).toString('hex');
  return `${timestamp}-${prefix}-${sanitizeFileComponent(stem, prefix)}-${rand}${ext}`;
}

async function saveInboundBuffer(mediaDir, filename, buffer) {
  const inboundDir = join(mediaDir, 'inbound');
  await mkdir(inboundDir, { recursive: true });
  const filePath = join(inboundDir, filename);
  await writeFile(filePath, buffer);
  return filePath;
}

function hasDownloadableMedia(media) {
  return Boolean(media?.encrypt_query_param || media?.full_url);
}

export function isMediaItem(item) {
  return (
    item?.type === MESSAGE_ITEM_TYPE.IMAGE ||
    item?.type === MESSAGE_ITEM_TYPE.VIDEO ||
    item?.type === MESSAGE_ITEM_TYPE.FILE ||
    item?.type === MESSAGE_ITEM_TYPE.VOICE
  );
}

function isDownloadableMediaItem(item) {
  if (!item) return false;
  if (item.type === MESSAGE_ITEM_TYPE.IMAGE) return hasDownloadableMedia(item.image_item?.media);
  if (item.type === MESSAGE_ITEM_TYPE.VIDEO) {
    return hasDownloadableMedia(item.video_item?.media) && Boolean(item.video_item?.media?.aes_key);
  }
  if (item.type === MESSAGE_ITEM_TYPE.FILE) {
    return hasDownloadableMedia(item.file_item?.media) && Boolean(item.file_item?.media?.aes_key);
  }
  if (item.type === MESSAGE_ITEM_TYPE.VOICE) {
    return hasDownloadableMedia(item.voice_item?.media) && Boolean(item.voice_item?.media?.aes_key) && !item.voice_item?.text;
  }
  return false;
}

export function extractTextBody(itemList) {
  if (!itemList?.length) return '';

  for (const item of itemList) {
    if (item.type === MESSAGE_ITEM_TYPE.TEXT && item.text_item?.text != null) {
      const text = String(item.text_item.text);
      const ref = item.ref_msg;
      if (!ref) return text;
      if (ref.message_item && isMediaItem(ref.message_item)) return text;

      const parts = [];
      if (ref.title) parts.push(ref.title);
      if (ref.message_item) {
        const refBody = extractTextBody([ref.message_item]);
        if (refBody) parts.push(refBody);
      }
      if (!parts.length) return text;
      return `[引用: ${parts.join(' | ')}]\n${text}`;
    }

    if (item.type === MESSAGE_ITEM_TYPE.VOICE && item.voice_item?.text) {
      return item.voice_item.text;
    }
  }

  return '';
}

export function pickInboundMediaItem(itemList) {
  if (!itemList?.length) return null;

  const mainMediaItem =
    itemList.find((item) => item.type === MESSAGE_ITEM_TYPE.IMAGE && isDownloadableMediaItem(item)) ||
    itemList.find((item) => item.type === MESSAGE_ITEM_TYPE.VIDEO && isDownloadableMediaItem(item)) ||
    itemList.find((item) => item.type === MESSAGE_ITEM_TYPE.FILE && isDownloadableMediaItem(item)) ||
    itemList.find((item) => item.type === MESSAGE_ITEM_TYPE.VOICE && isDownloadableMediaItem(item));

  if (mainMediaItem) return mainMediaItem;

  const refMediaItem = itemList.find(
    (item) =>
      item.type === MESSAGE_ITEM_TYPE.TEXT &&
      item.ref_msg?.message_item &&
      isDownloadableMediaItem(item.ref_msg.message_item)
  )?.ref_msg?.message_item;

  return refMediaItem || null;
}

export async function downloadInboundMedia(client, item, { mediaDir, logger, label = 'inbound' }) {
  if (!client || !item || !mediaDir) return {};

  try {
    if (item.type === MESSAGE_ITEM_TYPE.IMAGE) {
      const image = item.image_item;
      if (!hasDownloadableMedia(image?.media)) return {};
      const raw = await client.cdnDownload(image.media.encrypt_query_param || '', image.media.full_url);
      const aesKey = image.aeskey || image.media?.aes_key
        ? decodeAesKey(image.media?.aes_key || '', image.aeskey)
        : null;
      const plaintext = aesKey ? decrypt(raw, aesKey) : raw;
      const fallbackExt = inferExtensionFromUrl(image.url) || inferExtensionFromUrl(image.media?.full_url) || '.bin';
      const filePath = await saveInboundBuffer(
        mediaDir,
        buildStoredFilename({ prefix: 'wechat-image', preferredName: `image${fallbackExt}`, fallbackExt }),
        plaintext
      );
      return { imagePath: filePath };
    }

    if (item.type === MESSAGE_ITEM_TYPE.FILE) {
      const file = item.file_item;
      if (!hasDownloadableMedia(file?.media) || !file.media?.aes_key) return {};
      const raw = await client.cdnDownload(file.media.encrypt_query_param || '', file.media.full_url);
      const plaintext = decrypt(raw, decodeAesKey(file.media.aes_key));
      const preferredName = file.file_name || `file${inferExtensionFromUrl(file.media.full_url) || ''}`;
      const filePath = await saveInboundBuffer(
        mediaDir,
        buildStoredFilename({
          prefix: 'wechat-file',
          preferredName,
          fallbackExt: inferExtensionFromUrl(file.media.full_url),
        }),
        plaintext
      );
      return {
        filePath,
        fileName: basename(preferredName),
        fileMimeType: inferFileMimeType(preferredName),
      };
    }

    if (item.type === MESSAGE_ITEM_TYPE.VIDEO) {
      const video = item.video_item;
      if (!hasDownloadableMedia(video?.media) || !video.media?.aes_key) return {};
      const raw = await client.cdnDownload(video.media.encrypt_query_param || '', video.media.full_url);
      const plaintext = decrypt(raw, decodeAesKey(video.media.aes_key));
      const fallbackExt = inferExtensionFromUrl(video.media.full_url) || '.mp4';
      const filePath = await saveInboundBuffer(
        mediaDir,
        buildStoredFilename({ prefix: 'wechat-video', preferredName: `video${fallbackExt}`, fallbackExt }),
        plaintext
      );
      return { videoPath: filePath };
    }

    if (item.type === MESSAGE_ITEM_TYPE.VOICE) {
      const voice = item.voice_item;
      if (voice?.text || !hasDownloadableMedia(voice?.media) || !voice.media?.aes_key) return {};
      const raw = await client.cdnDownload(voice.media.encrypt_query_param || '', voice.media.full_url);
      const plaintext = decrypt(raw, decodeAesKey(voice.media.aes_key));
      const fallbackExt = inferExtensionFromUrl(voice.media.full_url) || '.silk';
      const filePath = await saveInboundBuffer(
        mediaDir,
        buildStoredFilename({ prefix: 'wechat-voice', preferredName: `voice${fallbackExt}`, fallbackExt }),
        plaintext
      );
      return { voicePath: filePath };
    }
  } catch (error) {
    logger?.warn?.(`${label} media download failed`, error.message || String(error));
  }

  return {};
}

export function formatInboundContent(message, mediaResult = {}) {
  const sender = message?.from_user_id || 'unknown';
  const text = extractTextBody(message?.item_list);
  const parts = [`[WeChat DM] ${sender} said: ${text}`];

  if (mediaResult.imagePath) {
    parts.push(`\n[image: ${mediaResult.imagePath}]`);
  }
  if (mediaResult.videoPath) {
    parts.push(`\n[video: ${mediaResult.videoPath}]`);
  }
  if (mediaResult.filePath) {
    const fileLabel = mediaResult.fileName || basename(mediaResult.filePath);
    const fileMimeType = mediaResult.fileMimeType || inferFileMimeType(fileLabel);
    parts.push(`\n[file: ${fileLabel} (${fileMimeType}) — ${mediaResult.filePath}]`);
  }
  if (mediaResult.voicePath) {
    parts.push(`\n[voice: ${mediaResult.voicePath}]`);
  }

  return parts.join('');
}
