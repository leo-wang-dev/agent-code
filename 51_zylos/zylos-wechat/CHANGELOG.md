# Changelog

All notable changes to zylos-wechat will be documented in this file.

## [0.3.1] - 2026-05-18

### Fixed
- Post-upgrade hook now backs up `config.json` to
  `config.json.backup.<ISO-timestamp>` before mutation and uses atomic
  write (temp + rename) for the new config (#23)
- Migration failures correctly `process.exit(1)` so they no longer
  silently skip (#23)

### Removed
- Reverted in-config `_legacy_*` field injection
  (`_legacy_dmAllowlist`, `_legacy_c4ReceiveScript`) in favor of
  whole-file backups; the original config schema is preserved (#23)

## [0.3.0] - 2026-05-08

### Added
- Config-driven `channel_version` with env override, replacing hardcoded value (#19)
- `iLink-App-Id` and numeric-encoded `ClientVersion` request headers (#19)
- `bot_agent` field in `base_info` for upstream identification (#19)
- `notifyStart` / `notifyStop` lifecycle hooks for session management (#19)
- Log redaction module (`redact.js`) for sensitive data masking (#19)
- 31 new unit tests for redaction and API client helpers (#19)
- Component development guide (`CLAUDE.md`) (#21)

### Fixed
- Typing indicator not stopping after reply is sent (#16, #19)

## [0.2.1] - 2026-04-01

### Fixed
- Inbound WeChat media messages now download and forward image, file, video, and voice attachments into the existing C4 text bridge format
- Inbound media download now supports `full_url` fallback when encrypted query parameters are insufficient on their own
- Quoted-message media is now detected and forwarded instead of being dropped during inbound dispatch
- Voice messages now prefer `voice_item.text` as the message body and only fall back to `[voice: ...]` attachment forwarding when no transcript is available
- Confirmed login session test fixtures now use relative timestamps so the test suite does not fail after the hard-coded expiry window passes

## [0.2.0] - 2026-04-01

### Added
- Localhost-only admin HTTP control plane for login start/status/cancel/finalize and account health/disconnect
- Login session persistence with staged credentials and 30-minute terminal tombstones
- Runtime health snapshots tracking login health, replyability, and recent inbound/context timestamps
- Replyability refresh based on the latest valid `context_token`

### Changed
- Main runtime now exposes machine-driven account lifecycle control for `coco-dashboard` integration
- Admin token files now self-heal if missing or invalid

### Fixed
- Finalize now preserves `WECHAT_ACCOUNT_CONFLICT` so callers receive the correct 409 conflict semantics

## [0.1.0] - 2026-03-22

### Added
- Component skeleton with zylos-component-template structure
- Interface contract v0.1 (inbound/outbound schema, error codes)
- WeChat iLink Bot API client (`api-client.js`) with real endpoints
- QR code login flow (`qr-login.js`) with retry and 8-min timeout
- Long-poll manager (`poller.js`) with error recovery and session expiry handling
- Multi-account credential and sync state persistence (`account-store.js`)
- Account lifecycle manager (`account-manager.js`)
- Context token cache with disk persistence (`context-tokens.js`)
- AES-128-ECB media encryption/decryption (`media-crypto.js`)
- Media upload pipeline (`media-upload.js`) with CDN encrypt+upload
- Typing indicator manager (`typing.js`) with auto-refresh
- Outbound send script (`scripts/send.js`) supporting text and media
- C4 comm-bridge integration for inbound message dispatch
- SKILL.md with component metadata and lifecycle hooks
- PM2 ecosystem config with proper paths and log files
- Lifecycle hooks (post-install, pre-upgrade, post-upgrade)
- Crypto roundtrip test suite (26 tests)
- Complete API reference documentation (`docs/WECHAT-API.md`)
