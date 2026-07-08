# zylos-wechat roadmap (bootstrap phase)

## Milestone A: skeleton + contract (this PR)
- [x] Repository bootstrap
- [x] PM2 config
- [x] Config + logger + C4 bridge wrapper
- [x] Outbound CLI (`scripts/send.js`)
- [x] Interface contract v0.1

## Milestone B: API transport hardening
- [ ] Confirm real endpoint paths + request signatures
- [ ] Implement QR login lifecycle + token refresh
- [ ] Normalize inbound message model from getUpdates
- [ ] Implement typed error mapping

## Milestone C: feature completeness
- [ ] Media upload AES-128-ECB + CDN flow
- [ ] sendtyping support in runtime and CLI
- [ ] getconfig integration + diagnostics output
- [ ] multi-account concurrent pollers
- [ ] integration smoke tests
