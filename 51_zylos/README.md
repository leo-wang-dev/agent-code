# 第 51–60 篇配套代码：把 Claude Code 封装成 7×24 数字员工

本目录是第五部分「真实开源系统解剖篇」（第 51–60 篇）的配套代码。

与前 50 篇不同，这一部分不是我们自己写的教学代码，而是**逐模块精读一套真实开源的 Agent 基础设施** —— [zylos](https://github.com/zylos-ai/zylos-core)（Autonomous AI Agent Infrastructure）。文章讲到的每一行代码，都能在这里对着文件路径与行号找到。

## 目录结构

```
51_zylos/
├── zylos-core/     # 核心源码快照（v0.5.3，MIT License，出处见其 LICENSE / README）
│   ├── cli/lib/runtime/     → 52 / 59 / 60 篇（进程封装、上下文监控、RuntimeAdapter）
│   ├── skills/comm-bridge/  → 53 / 54 篇（消息总线、投递引擎）
│   ├── skills/activity-monitor/ → 56 / 57 篇（感知层、守护自愈）
│   ├── skills/zylos-memory/ → 58 篇（记忆系统）
│   ├── skills/new-session/  → 59 篇（会话轮换）
│   └── templates/           → 52 篇（指令三层模板、PM2 生态）
├── zylos-wechat/   # 个人微信渠道组件快照（v0.3.1）→ 55 篇
│   ├── src/index.js         # 服务主干
│   ├── src/lib/             # api-client / poller / qr-login / bridge / context-tokens …
│   └── scripts/send.js      # 出站契约实现
└── labs/           # 每篇的动手实验清单（51-setup.md … 60-adapter.md）
```

## 两份源码是原样收录的开源代码

`zylos-core/` 和 `zylos-wechat/` 是上游开源仓库的快照，**保留各自的 LICENSE 与出处声明**。文章以讲解开源项目的方式引用它们（如同第 17 篇讲 Mem0）。要跑起来请以上游最新版为准：

```bash
# 官方安装（会装齐 git / tmux / Node.js / zylos CLI 并跑 zylos init）
curl -fsSL https://raw.githubusercontent.com/zylos-ai/zylos-core/main/scripts/install.sh | bash
```

## 环境准备

- Linux 服务器或 Mac（VPS 最低配即可）
- Node.js 18+、git、tmux
- Claude Code（推荐）或 Codex CLI —— API key 与 base_url 自备（支持自定义 base_url，中转网关可用）
- 一个微信**小号**（55 篇实验用；个人微信机器人接口有其风险边界，务必勿用大号）

## 篇目与源码对照

| 篇 | 主题 | 主要源码 |
|----|------|---------|
| 51 | 开篇 · 全景 + 简历 | 本 README + `labs/51-setup.md` |
| 52 | 进程封装 | `zylos-core/cli/lib/runtime/{tmux-launcher,tmux-env,tmux-helpers,instruction-builder}.js`、`templates/` |
| 53 | 消息总线 | `zylos-core/skills/comm-bridge/{init-db.sql,scripts/c4-receive.js,c4-send.js,c4-control.js,c4-utils.js}` |
| 54 | 投递引擎 | `zylos-core/skills/comm-bridge/scripts/{c4-dispatcher.js,tmux-input-state.js}` |
| 55 | 微信接入 | `zylos-wechat/`（`src/index.js`、`src/lib/poller.js`、`qr-login.js`、`bridge.js`、`context-tokens.js`、`scripts/send.js`） |
| 56 | 感知层 | `zylos-core/cli/lib/sync-settings-hooks.js`、`skills/activity-monitor/scripts/{hook-activity,hook-auth-prompt,context-monitor,proc-sampler}.js` |
| 57 | 守护自愈 | `zylos-core/skills/activity-monitor/scripts/{guardian,health-engine,message-router}.js`、`cli/lib/heartbeat/claude-probe.js` |
| 58 | 记忆系统 | `zylos-core/skills/zylos-memory/`、`skills/comm-bridge/scripts/{c4-session-init,c4-checkpoint}.js` |
| 59 | 上下文生命周期 | `zylos-core/cli/lib/runtime/{context-monitor-base,claude-context-monitor,codex-context-monitor,session-handoff}.js`、`skills/new-session/SKILL.md` |
| 60 | RuntimeAdapter | `zylos-core/cli/lib/runtime/{base,index,claude,codex}.js` |

> 文章正文为付费内容，存放在独立私有仓库，不在此处。本目录只提供可对照阅读、可实际部署的源码与实验清单。
