---
name: wechat
version: 0.3.1
description: >-
  WeChat (微信) communication channel for Zylos. Use when: (1) replying to WeChat
  messages (DM), (2) sending proactive messages or media (images, files) to WeChat
  users, (3) managing DM access control (dmPolicy, dmAllowFrom), (4) managing WeChat
  account login via QR code, (5) troubleshooting WeChat connection or polling issues.
  Config at ~/zylos/components/wechat/config.json. Service: pm2 zylos-wechat.
type: communication

lifecycle:
  npm: true
  service:
    type: pm2
    name: zylos-wechat
    entry: src/index.js
  data_dir: ~/zylos/components/wechat
  hooks:
    post-install: hooks/post-install.js
    pre-upgrade: hooks/pre-upgrade.js
    post-upgrade: hooks/post-upgrade.js
  preserve:
    - config.json
    - accounts/
    - context-tokens.json

upgrade:
  repo: zylos-ai/zylos-wechat
  branch: main

config:
  required: []
  optional:
    - name: ZYLOS_WECHAT_DATA_DIR
      description: Override component data directory
      default: "~/zylos/components/wechat"
    - name: ZYLOS_WECHAT_ENABLED
      description: Optional env override for config.enabled
      default: "true"
    - name: ZYLOS_WECHAT_LOG_LEVEL
      description: Optional env override for config.logLevel
      default: "info"
    - name: ZYLOS_WECHAT_DM_ALLOWLIST
      description: Legacy env override for config.dmAllowFrom (implies dmPolicy=allowlist when non-empty)
      default: ""

dependencies:
  - comm-bridge
---

# zylos-wechat

WeChat personal account integration via the iLink Bot API.

## Account Login

```bash
npm run admin -- login
```

The command prints a QR URL. Open it with WeChat and confirm login. If the service is running, it should pick up the new account within about 10 seconds.

## Admin CLI

```bash
npm run admin -- show
npm run admin -- list-accounts
npm run admin -- remove-account <normalized_id>
npm run admin -- set-dm-policy <open|allowlist>
npm run admin -- list-dm-allow
npm run admin -- add-dm-allow <wechat_user_id>
npm run admin -- remove-dm-allow <wechat_user_id>
```

## Config

Primary config: `~/zylos/components/wechat/config.json`

```json
{
  "enabled": true,
  "logLevel": "info",
  "dmPolicy": "open",
  "dmAllowFrom": [],
  "wechat": {
    "apiBase": "https://ilinkai.weixin.qq.com",
    "cdnBaseUrl": "https://novac2c.cdn.weixin.qq.com/c2c"
  },
  "c4": {
    "receiveScript": "~/zylos/.claude/skills/comm-bridge/scripts/c4-receive.js"
  }
}
```

Environment variables are optional overrides on top of `config.json`, not the primary source of truth.

## Send Message

```bash
# Text
echo "hello" | node scripts/send.js "<normalized_account_id>|to:<wechat_user_id>"

# Media
echo "[MEDIA:image]/path/to/photo.png" | node scripts/send.js "<normalized_account_id>|to:<wechat_user_id>"
```

## Architecture

- Long-poll (`getUpdates`) for inbound messages
- Context token cached per user (required for all replies)
- AES-128-ECB encrypted media via Tencent CDN
- Multi-account support with isolated state per account
