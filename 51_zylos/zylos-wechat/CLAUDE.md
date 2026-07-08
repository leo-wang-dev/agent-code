# AI Component Development Guide

This document guides AI assistants to create new zylos components using this template.

For the full technical specification, see [COMPONENT-SPEC.md](./COMPONENT-SPEC.md).

## Project Conventions

- **ESM only** — `import`/`export`, never `require()`. `"type": "module"` in package.json
- **Node.js 20+** — Minimum runtime version
- **Conventional commits** — `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`
- **No `files` in package.json** — Rely on `.gitignore` to exclude
- **Secrets in `.env` only** — Never commit secrets. `~/zylos/.env` for credentials, `config.json` for non-sensitive runtime config
- **English for code** — Comments, commit messages, PR descriptions, documentation

## Release Process

When releasing a new version, **all four files** must be updated in the same commit:

1. **`package.json`** — Bump `version` field
2. **`package-lock.json`** — Run `npm install` after bumping package.json to sync the lock file
3. **`SKILL.md`** — Update `version` in YAML frontmatter to match package.json
4. **`CHANGELOG.md`** — Add new version entry following [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format

Version bump commit message: `chore: bump version to X.Y.Z`

CHANGELOG entry format:
```markdown
## [X.Y.Z] - YYYY-MM-DD

### Added / Changed / Fixed / Removed / Security
- Description of change (#PR)
```

After merge, create a GitHub Release with tag `vX.Y.Z` from the merge commit.

## Quick Start

### Step 1: Copy Template

```bash
cd ~/src
git clone https://github.com/zylos-ai/zylos-component-template.git temp-clone
cp -r temp-clone/template zylos-<name>
rm -rf temp-clone
cd zylos-<name>
```

### Step 2: Gather Component Info

Confirm with user:
- **Name**: lowercase, e.g., `discord`, `slack`, `browser`
- **Description**: one-line description
- **Type**: `communication` | `capability` | `utility`

### Step 3: Replace Placeholders

| Placeholder | Replace With | Example |
|-------------|--------------|---------|
| `{{COMPONENT_NAME}}` | Component name (lowercase) | `discord` |
| `{{COMPONENT_NAME_UPPER}}` | Component name (uppercase) | `DISCORD` |
| `{{COMPONENT_TITLE}}` | Component title | `Discord` |
| `{{COMPONENT_DESCRIPTION}}` | Component description | `Discord bot integration` |
| `{{COMPONENT_TYPE}}` | Component type | `communication` |
| `{{DATE}}` | Current date | `2026-02-09` |

```bash
find . -type f -exec sed -i "s|{{COMPONENT_NAME}}|$NAME|g" {} \;
# Repeat for all placeholders
```

### Step 4: Handle Component Type

- **communication**: Keep all files as-is
- **capability / utility**: Delete `scripts/send.js`

### Step 5: Implement Component Logic

Read the type-specific guide:
- **Communication**: See [references/communication.md](./references/communication.md) — C4 bridge integration, message format, owner binding, group context. Also see [references/channel-standards.md](./references/channel-standards.md) — security pitfalls, coding standards, and pre-commit checklist
- **Capability / Utility**: See [references/capability.md](./references/capability.md) — service pattern, CLI tool pattern

### Step 6: Update SKILL.md

The SKILL.md `description` field is how Claude decides when to use this component. Write it following create-skill principles:

- Include **what** the component does AND **when** to use it (trigger patterns)
- Put all "when to use" information in the frontmatter `description`, NOT in the body
- Body should contain only concise usage examples — Claude can run `--help` for details

Example description for a discord component:
```
Discord messaging for Zylos agents. Use when the user wants to communicate via
Discord, send messages to Discord channels, or configure Discord bot settings.
```

Fill in `config.required` if the component needs API keys or secrets.

### Step 7: Update README.md

Replace placeholder features with actual features. The template includes centered logo, badge icons, and standard sections — fill in component-specific content.

### Step 8: Initialize Git

```bash
git init && git add . && git commit -m "Initial commit: zylos-<name>"
git branch -M main
git remote add origin git@github.com:zylos-ai/zylos-<name>.git
git push -u origin main
```

## Best Practices

### Config Management

| Location | What goes here | Example |
|----------|---------------|---------|
| `~/zylos/.env` | Secrets and credentials | `DISCORD_BOT_TOKEN=xxx` |
| `~/zylos/components/<name>/config.json` | Runtime configuration | `{"enabled": true}` |

Secrets NEVER go in config.json. Declare them in SKILL.md frontmatter:

```yaml
config:
  required:
    - name: DISCORD_BOT_TOKEN
      description: Discord bot token
      sensitive: true
```

### Directory Convention

```
Code:    ~/zylos/.claude/skills/<component>/    # Overwritten on upgrade
Data:    ~/zylos/components/<component>/         # Preserved across upgrades
Secrets: ~/zylos/.env                            # Shared across components
```

**Code is disposable, data is permanent.** Never store user data in the skills directory.

### Logging

Use consistent prefix: `[component-name]`

### Error Handling

- **Startup**: Fail fast on missing credentials (`process.exit(1)`)
- **Runtime**: Log and continue (don't crash the service)
- **Shutdown**: Graceful on SIGINT/SIGTERM

### Hooks

| Hook | When | Purpose |
|------|------|---------|
| `post-install.js` | After `zylos add` | Create data dirs, default config |
| `pre-upgrade.js` | Before `zylos upgrade` | Backup config. Exit 1 to abort |
| `post-upgrade.js` | After `zylos upgrade` | Migrate config schema |

## Acceptance Checklist

- [ ] SKILL.md frontmatter complete (name, version, type, lifecycle, upgrade)
- [ ] SKILL.md description includes trigger patterns (what + when to use)
- [ ] SKILL.md body has concise usage examples only
- [ ] README.md has real features, badges, and setup instructions
- [ ] `npm install && npm start` works
- [ ] post-install.js creates data directory and default config
- [ ] post-upgrade.js handles config migrations
- [ ] PM2 can manage the service (`pm2 start ecosystem.config.cjs`)
- [ ] (communication) scripts/send.js sends text and media
- [ ] (communication) Messages forwarded to C4 in correct format

## Reference Implementations

- [zylos-telegram](https://github.com/zylos-ai/zylos-telegram) — Telegram communication component
- [zylos-lark](https://github.com/zylos-ai/zylos-lark) — Lark/Feishu communication component
- [zylos-imagegen](https://github.com/zylos-ai/zylos-imagegen) — Image generation capability component
