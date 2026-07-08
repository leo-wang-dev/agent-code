# 48 · Harness 选型扩展：OpenHands / Hermes / DeepAgents 当 Harness 用

配套文章：《Harness vs Framework 的选型扩展》（系列第 48 篇）。

Python demo 全部离线可跑（deepagents 已装时展示真实接线方式，但 demo 不构造模型/不联网）。

## 文章"包含"清单 → 文件对照

| 文章承诺的产物 | 位置 | 运行 |
|---|---|---|
| OpenHands 自部署 | `openhands_selfhost/`（docker-compose.yml + README） | `docker compose up -d` |
| 工具挂载完整示例 | `openhands_tools.py` | `python3 openhands_tools.py` |
| DeepAgents 自定义 Middleware 完整实现 | `deepagents_middleware.py` | `python3 deepagents_middleware.py` |
| 三层混合架构 demo | `hybrid_architecture.py` | `python3 hybrid_architecture.py` |
| per-user 实例编排脚本 | `per_user_orchestrator.py` | `python3 per_user_orchestrator.py` |

## 覆盖的文章要点

- **工具挂载**：给通用 Harness 挂美容领域工具 + 注入 system prompt，跑"计划→调工具→汇总"循环。
- **DeepAgents Middleware**：共享知识库 / 集体洞察(k-匿名) / 隐私控制(opt-in + 出站脱敏) 三层中间件；对齐文章"用 DeepAgents SDK 替代 fork OpenHands"的建议。
- **三层混合架构**：按 用户档次 × 任务复杂度 路由到 轻量/深度/Harness 层，跑混合流量出成本报表（90%+ 走轻量层）。
- **per-user 编排**：mock 容器管理器演示 按需拉起 / 故障自愈 / 不活跃回收 / 资源分档 / 成本核算。

## 生产替换点

- `openhands_tools.MockHarness`：离线 mock；生产换自部署 OpenHands（见 `openhands_selfhost/`）。
- `deepagents_middleware.MockDeepAgent`：离线 middleware 链；生产用 `deepagents.create_deep_agent(...)`（真实接线见 `describe_real_wiring()`）。
- `per_user_orchestrator.MockContainerManager`：生产换 K8s（Deployment/StatefulSet + HPA）或 Nomad。
