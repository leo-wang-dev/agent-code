import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {
  downloadInboundMedia,
  extractTextBody,
  formatInboundContent,
  pickInboundMediaItem,
} from '../src/lib/inbound-media.js';
import { encrypt, generateAesKey } from '../src/lib/media-crypto.js';

const tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'zylos-wechat-inbound-media-'));

try {
  {
    const quotedImageMessage = {
      from_user_id: 'wx-user-1',
      item_list: [
        {
          type: 1,
          text_item: { text: 'see image' },
          ref_msg: {
            message_item: {
              type: 2,
              image_item: {
                media: {
                  full_url: 'https://cdn.example.com/ref-image.png',
                },
              },
            },
          },
        },
      ],
    };

    const mediaItem = pickInboundMediaItem(quotedImageMessage.item_list);
    assert.ok(mediaItem, 'quoted image should be selected as downloadable media');
    assert.equal(mediaItem.type, 2);
    assert.equal(extractTextBody(quotedImageMessage.item_list), 'see image');
    assert.equal(
      formatInboundContent(quotedImageMessage, { imagePath: '/tmp/ref-image.png' }),
      '[WeChat DM] wx-user-1 said: see image\n[image: /tmp/ref-image.png]'
    );
  }

  {
    const voiceWithTranscript = {
      from_user_id: 'wx-user-2',
      item_list: [
        {
          type: 3,
          voice_item: {
            text: 'voice transcript',
            media: {
              encrypt_query_param: 'enc',
              aes_key: Buffer.from('0123456789abcdef0123456789abcdef', 'ascii').toString('base64'),
            },
          },
        },
      ],
    };

    assert.equal(extractTextBody(voiceWithTranscript.item_list), 'voice transcript');
    assert.equal(pickInboundMediaItem(voiceWithTranscript.item_list), null);
    assert.equal(
      formatInboundContent(voiceWithTranscript),
      '[WeChat DM] wx-user-2 said: voice transcript'
    );
  }

  {
    const aesKey = generateAesKey();
    const plaintext = Buffer.from('fake-image-bytes');
    const encrypted = encrypt(plaintext, aesKey);
    const calls = [];
    const client = {
      async cdnDownload(encryptQueryParam, fullUrl) {
        calls.push({ encryptQueryParam, fullUrl });
        return encrypted;
      },
    };

    const imageItem = {
      type: 2,
      image_item: {
        aeskey: aesKey.toString('hex'),
        media: {
          full_url: 'https://cdn.example.com/photo.png?x=1',
        },
      },
    };

    const result = await downloadInboundMedia(client, imageItem, {
      mediaDir: tmpRoot,
      logger: { warn() {} },
      label: 'test',
    });

    assert.equal(calls.length, 1);
    assert.deepEqual(calls[0], {
      encryptQueryParam: '',
      fullUrl: 'https://cdn.example.com/photo.png?x=1',
    });
    assert.ok(result.imagePath, 'image path should be returned');
    assert.equal(fs.readFileSync(result.imagePath).toString('utf8'), plaintext.toString('utf8'));
    assert.match(result.imagePath, /\.png$/);
  }

  console.log('inbound media');
  console.log('  ✓ selects quoted media items for download');
  console.log('  ✓ prefers voice transcripts over voice attachment forwarding');
  console.log('  ✓ downloads media via full_url fallback and saves decrypted payloads');
} finally {
  fs.rmSync(tmpRoot, { recursive: true, force: true });
}
