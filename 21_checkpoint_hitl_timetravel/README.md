# 21 LangGraph 稀缺三件事：Checkpoint 与 HITL 与 TimeTravel

配套文章：《LangGraph 稀缺三件事：Checkpoint 与 HITL 与 TimeTravel》

这三件事是别的框架做不好、LangGraph 开箱即用的能力，也是"能上线的 Agent"和
"看起来能跑的 demo"之间的分水岭。本目录逐个跑通，再合成一个端到端采购项目。

## 安装依赖

```bash
pip install langgraph
# 可选（用于 SqliteSaver / PostgresSaver 对照）：
pip install langgraph-checkpoint-sqlite langgraph-checkpoint-postgres
```

- 缺少 `langgraph` 时脚本打印安装提示并以退出码 0 退出，不崩溃。
- 所有示例都用内置的 `MemorySaver`，无需外部数据库、无需密钥即可运行。
- `01` 会额外探测 Sqlite / Postgres saver 是否安装，未装则给出安装命令。

## 文件对照表

| 文件 | 对应产物 | 说明 |
|------|----------|------|
| `01_checkpoint_savers.py` | Checkpoint 三种 saver 对照 | MemorySaver 实跑持久化 + 探测 Sqlite/Postgres 可用性 |
| `02_hitl_approval.py` | HITL 完整审批流 | `interrupt()` 暂停 + `Command(resume=...)` 恢复 |
| `03_time_travel.py` | Time Travel 历史回放 demo | `get_state_history` 列快照 + 从指定 checkpoint 重跑 |
| `04_procurement_agent.py` | 端到端项目 | 采购 Agent + ≥5w 审批 + Time Travel 流程审计（三件事协同） |
| `demo.py` | 章节统一入口 | 委托 `series_projects.chapter_runner` |

## 运行

```bash
python3 01_checkpoint_savers.py
python3 02_hitl_approval.py
python3 04_procurement_agent.py
```

## 核心认知

- Checkpoint 是"加上就立刻有工业级价值"的能力：一个 saver 换来会话持久化 + 故障恢复 + 调试审计。三种 saver 按部署规模选（Memory 只用于测试）。
- HITL 用 `interrupt()` + Checkpointer：涉及真实世界副作用的操作必须卡在节点等人点确认，框架负责状态保存、流程暂停、恢复。
- Time Travel 是流程的 git checkout：保留所有历史快照，可从任意一步重跑——线上 bug 复现、从问题节点重跑、A/B 测试、回归测试全靠它。
- 三件事合起来 = 工业级 Agent 系统的基础设施，这是大型企业级项目选 LangGraph 的核心原因。
