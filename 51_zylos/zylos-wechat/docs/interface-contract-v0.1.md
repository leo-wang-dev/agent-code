# zylos-wechat Interface Contract v0.1

Status: Updated with verified API contract (2026-03-22)

## API Protocol

All API calls use `POST` to `https://ilinkai.weixin.qq.com` (or per-account `baseUrl` from login).

Required headers on every request:
```
Content-Type: application/json
AuthorizationType: ilink_bot_token
X-WECHAT-UIN: <base64(decimal-string(random-uint32))>
Authorization: Bearer <token>
```

Every JSON body includes:
```json
"base_info": { "channel_version": "1.0.2" }
```

## 1) Inbound event schema (WeChat -> C4)

```json
{
  "channel": "wechat",
  "endpoint": "<normalized_account_id>",
  "content": "[WeChat DM] <sender> said: <text>",
  "meta": {
    "account_id": "<normalized_account_id>",
    "msg_id": "<message_id>",
    "from": "<hex>@im.wechat",
    "context_token": "<token from inbound message>",
    "timestamp": "<iso time>",
    "raw_type": "text|image|file|video|voice"
  }
}
```

## 2) Outbound contract (`scripts/send.js` / runtime)

Required fields:

- `to`: WeChat peer id, e.g. `<hex>@im.wechat`
- `content`: text payload
- `contextToken`: must come from latest inbound message of the target conversation (**mandatory**)

Actual API request (POST `/ilink/bot/sendmessage`):

```json
{
  "msg": {
    "from_user_id": "",
    "to_user_id": "<wechat_user_id>",
    "client_id": "zylos-wechat:<timestamp>-<hex>",
    "message_type": 2,
    "message_state": 2,
    "context_token": "<token>",
    "item_list": [{ "type": 1, "text_item": { "text": "<content>" } }]
  },
  "base_info": { "channel_version": "1.0.2" }
}
```

## 3) Account state store schema

Per-account files in `~/zylos/components/wechat/accounts/`:

**Credentials** (`<normalized_id>.json`, chmod 0600):
```json
{
  "token": "<bearer_token>",
  "baseUrl": "<account-specific API base URL>",
  "userId": "<WeChat user ID of account owner>",
  "savedAt": "<ISO timestamp>"
}
```

**Sync state** (`<normalized_id>.sync.json`):
```json
{
  "get_updates_buf": "<opaque base64 cursor from last getUpdates response>"
}
```

**Account index** (`accounts.json`):
```json
["<normalized_id_1>", "<normalized_id_2>"]
```

Note: The long-poll cursor is an opaque `get_updates_buf` string (not a numeric offset).
Empty string `""` on first call retrieves all pending messages.

## 4) Dedupe / idempotency

Key: `<normalized_account_id>:<message_id>`

Store: In-memory Set with TTL (max 10,000 entries, 1 hour expiry).

Guarantee: At-least-once ingestion from polling; dedupe prevents duplicate dispatch into C4.

## 5) Error handling semantics (v0)

- `ERR_CONTEXT_TOKEN_MISSING` — No context_token available for target user
- `ERR_CONTEXT_TOKEN_EXPIRED` — Cached context_token TTL exceeded (24h)
- `ERR_WECHAT_AUTH` — Bearer token invalid or missing
- `ERR_WECHAT_SESSION_EXPIRED` — errcode -14 from getUpdates (60-min pause)
- `ERR_WECHAT_RATE_LIMIT`
- `ERR_WECHAT_UPSTREAM` — ret !== 0 or errcode !== 0

Error recovery for getUpdates:
- Consecutive failures < 3: retry after 2s
- Consecutive failures >= 3: backoff 30s, reset counter
- Session expired (errcode -14): pause all API calls for 60 minutes

## 6) Non-goals in v0.1

- Group chat semantics
- Voice transcription (silk-wasm)
- Webhook mode (polling only)
