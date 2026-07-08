# WeChat iLink Bot API Reference

Extracted from `@tencent-weixin/openclaw-weixin` v1.0.2 source code.

## Base URLs

| Purpose | URL |
|---|---|
| API | `https://ilinkai.weixin.qq.com` (default; overridden per-account from login `baseurl`) |
| CDN | `https://novac2c.cdn.weixin.qq.com/c2c` (default; overridden per-account via `cdnBaseUrl` config) |

## Common Headers

All API calls (except QR endpoints):
```
Content-Type: application/json
AuthorizationType: ilink_bot_token
Content-Length: <byte length of JSON body, UTF-8>
X-WECHAT-UIN: <base64(decimal-string(random-uint32))>
Authorization: Bearer <token>
```

Every JSON body includes:
```json
"base_info": { "channel_version": "1.0.2" }
```

Timeouts: long-poll 35s, regular API 15s, lightweight (getConfig/sendTyping) 10s.

## 1. QR Login Flow

### Step 1 — Get QR Code
```
GET <baseUrl>/ilink/bot/get_bot_qrcode?bot_type=3
```
Response:
```json
{
  "qrcode": "<opaque token for polling>",
  "qrcode_img_content": "<URL to display as QR>"
}
```

### Step 2 — Poll QR Status
```
GET <baseUrl>/ilink/bot/get_qrcode_status?qrcode=<url-encoded qrcode>
Headers: iLink-App-ClientVersion: 1
Timeout: 35s (AbortError → treat as {status:"wait"})
```
Response:
```json
{
  "status": "wait" | "scaned" | "confirmed" | "expired",
  "bot_token": "<bearer token>",
  "ilink_bot_id": "<account ID, e.g. hex@im.bot>",
  "baseurl": "<account-specific base URL>",
  "ilink_user_id": "<WeChat user ID who scanned>"
}
```
- `bot_token`, `ilink_bot_id`, `baseurl`, `ilink_user_id` only on `status = "confirmed"`
- Poll: 1s sleep between polls; up to 3 QR refreshes on `"expired"`; 8 min overall timeout

## 2. getUpdates (Long-Poll)

```
POST <baseUrl>/ilink/bot/getupdates
```
Request:
```json
{
  "get_updates_buf": "<opaque base64 cursor; empty string on first call>",
  "base_info": { "channel_version": "1.0.2" }
}
```
Response:
```json
{
  "ret": 0,
  "errcode": 0,
  "errmsg": "",
  "msgs": [],
  "get_updates_buf": "<new cursor to persist>",
  "longpolling_timeout_ms": 35000
}
```

### Error Recovery
- `ret !== 0` or `errcode !== 0`: failure count++. After 3 consecutive: 30s backoff, reset. Otherwise: 2s retry.
- `errcode === -14` (SESSION_EXPIRED): pause 60 minutes, then resume.
- `AbortError` (35s timeout): treat as empty, immediately retry.

## 3. sendMessage

```
POST <baseUrl>/ilink/bot/sendmessage
```
Request:
```json
{
  "msg": {
    "from_user_id": "",
    "to_user_id": "<recipient>",
    "client_id": "zylos-wechat:<timestamp>-<8-char hex>",
    "message_type": 2,
    "message_state": 2,
    "context_token": "<from inbound message — MANDATORY>",
    "item_list": [{ /* one MessageItem */ }]
  },
  "base_info": { "channel_version": "1.0.2" }
}
```

### MessageItem Types

**Text (type=1):**
```json
{ "type": 1, "text_item": { "text": "<text, max 4000 chars>" } }
```

**Image (type=2):**
```json
{
  "type": 2,
  "image_item": {
    "media": {
      "encrypt_query_param": "<from CDN x-encrypted-param>",
      "aes_key": "<base64(hex-string-of-aeskey)>",
      "encrypt_type": 1
    },
    "mid_size": "<ciphertext bytes>"
  }
}
```

**File (type=4):**
```json
{
  "type": 4,
  "file_item": {
    "media": { "encrypt_query_param": "...", "aes_key": "...", "encrypt_type": 1 },
    "file_name": "<original filename>",
    "len": "<plaintext bytes as string>"
  }
}
```

**Video (type=5):**
```json
{
  "type": 5,
  "video_item": {
    "media": { "encrypt_query_param": "...", "aes_key": "...", "encrypt_type": 1 },
    "video_size": "<ciphertext bytes>"
  }
}
```

## 4. getConfig

```
POST <baseUrl>/ilink/bot/getconfig
```
Request:
```json
{
  "ilink_user_id": "<user ID>",
  "context_token": "<optional>",
  "base_info": { "channel_version": "1.0.2" }
}
```
Response:
```json
{
  "ret": 0,
  "errmsg": "",
  "typing_ticket": "<use in sendTyping>"
}
```
Cache: 24h TTL, exponential-backoff retry starting at 2s capped at 1h.

## 5. sendTyping

```
POST <baseUrl>/ilink/bot/sendtyping
```
Request:
```json
{
  "ilink_user_id": "<user ID>",
  "typing_ticket": "<from getConfig>",
  "status": 1,
  "base_info": { "channel_version": "1.0.2" }
}
```
`status`: 1=typing, 2=cancel. Refresh every 5s during generation.

## 6. Media Upload

### Step 1 — Prepare
```
aeskey = randomBytes(16)
filesize = ceil((rawsize + 1) / 16) * 16  // PKCS7 padded
filekey = randomBytes(16).hex()
rawfilemd5 = md5(plaintext)
```

### Step 2 — getUploadUrl
```
POST <baseUrl>/ilink/bot/getuploadurl
```
```json
{
  "filekey": "<32-char hex>",
  "media_type": 1,
  "to_user_id": "<recipient>",
  "rawsize": "<plaintext bytes>",
  "rawfilemd5": "<hex md5>",
  "filesize": "<ciphertext bytes>",
  "no_need_thumb": true,
  "aeskey": "<32-char hex of 16-byte key>",
  "base_info": { "channel_version": "1.0.2" }
}
```
`media_type`: 1=IMAGE, 2=VIDEO, 3=FILE, 4=VOICE

Response: `{ "upload_param": "..." }`

### Step 3 — CDN Upload
```
POST <cdnBaseUrl>/upload?encrypted_query_param=<urlenc(upload_param)>&filekey=<urlenc(filekey)>
Content-Type: application/octet-stream
Body: AES-128-ECB(plaintext, aeskey)  // PKCS7 padding
```
Success: HTTP 200, header `x-encrypted-param: <downloadParam>`

### Step 4 — CDN Download
```
GET <cdnBaseUrl>/download?encrypted_query_param=<urlenc(encrypt_query_param)>
```
Body: AES-128-ECB encrypted. Decrypt with aes_key.

## 7. Inbound Message Structure

```typescript
{
  seq?: number
  message_id?: number
  from_user_id?: string
  to_user_id?: string
  client_id?: string
  create_time_ms?: number
  update_time_ms?: number
  delete_time_ms?: number
  session_id?: string
  group_id?: string
  message_type?: 0|1|2       // NONE|USER|BOT
  message_state?: 0|1|2      // NEW|GENERATING|FINISH
  item_list?: MessageItem[]
  context_token?: string      // MUST echo in every reply
}
```

### Voice Item Extra
`encode_type` (1=pcm..8=ogg-speex), `sample_rate`, `playtime` (ms), `text` (voice-to-text).

### Quoted Message
`item.ref_msg.message_item` + `item.ref_msg.title`. Format: `[引用: <title> | <body>]\n<text>`.

## 8. Per-Account State

| Key | Content |
|---|---|
| Account credentials | token, baseUrl, savedAt, userId |
| Sync state | `{ "get_updates_buf": "..." }` |
| Context tokens | In-memory Map<"accountId:userId", token> |
| Typing tickets | In-memory cache, 24h TTL per userId |
