# zylos-wechat

WeChat component for Zylos. This repo is scaffolded for the migration from `@tencent-weixin/openclaw-weixin` to a standalone Zylos component with C4 comm-bridge integration.

## Current status

- ✅ Component skeleton
- ✅ Interface contract v0.1 (see `docs/interface-contract-v0.1.md`)
- ✅ `scripts/send.js` CLI entry for outbound messages
- 🚧 WeChat API transport implementation in progress (polling/login/media)

## Scope (v0)

1. Long polling receive (`getUpdates`)
2. Outbound text send (`sendMessage`, with `contextToken`)
3. QR login flow
4. Multi-account state isolation
5. Typing indicator (`sendtyping`)
6. Config fetch (`getconfig`)
7. Media upload (AES-128-ECB + CDN)

## Quick start

```bash
cp .env.example .env
npm install
npm run start
```

## Send message from CLI

```bash
npm run send -- --to "<wechat_user_id>" --text "hello" --context-token "<token>"
```

## Docs

- Interface contract: `docs/interface-contract-v0.1.md`
