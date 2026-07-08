# 22 用 LangGraph 实现 Orchestrator-Worker 多 Agent

配套文章：《用 LangGraph 实现 Orchestrator-Worker 多 Agent》

多 Agent 在 LangGraph 里就是"子图 + 并行边"。本目录从 Subgraph 封装讲起，
搭出完整的 Orchestrator-Worker 团队，再对照两种 State 策略、拆解五个生产坑。

## 安装依赖

```bash
pip install langgraph
```

- 缺少 `langgraph` 时脚本打印安装提示并以退出码 0 退出，不崩溃。
- 所有 Worker / Orchestrator 均为纯 Python + mock 逻辑（`call_llm` 是本地 mock），无需 `OPENAI_API_KEY`。

## 文件对照表

| 文件 | 对应产物 | 说明 |
|------|----------|------|
| `01_subgraph.py` | Subgraph 完整封装示例 | 编译好的子图当主图节点，可独立测试/复用/State 隔离 |
| `02_orchestrator_worker.py` | Orchestrator-Worker 完整实现 | Orchestrator 选 Worker → 并行 fan-out → Aggregator fan-in |
| `03_shared_vs_subgraph_state.py` | 共享 State vs 子图 State 对照 | 两种方案并列跑，展示子图内部字段如何被隔离 |
| `04_fanout_fanin.py` | fan-out/fan-in 并行示例 | 带耗时的 Worker 证明并行（总耗时≈最慢 Worker） |
| `05_production_pitfalls.py` | 五个生产坑的应对代码 | 协调风暴/Worker 失败降级/成本/幻觉回检/调试轨迹 |
| `demo.py` | 章节统一入口 | 委托 `series_projects.chapter_runner` |

## 运行

```bash
python3 02_orchestrator_worker.py
python3 04_fanout_fanin.py
python3 05_production_pitfalls.py
```

## 核心认知

- Subgraph = 把编译好的图当节点用，带来可独立测试、可复用、State 隔离三个红利。
- Orchestrator 一个节点连多个 Worker → 自动并行 fan-out；多个 Worker 连 Aggregator → fan-in 等全部完成。整体延迟取决于最慢的 Worker。
- Worker 用 `if not selected: return {}` 实现"选择性上场"，既省 token 又不污染 State。
- State 策略从共享起步、复杂了再拆子图，别一开始就上多级子图。
- 五个坑的应对（一次性下发、try/except 降级、选中才调 LLM、事实回检、Checkpoint+trace）是多 Agent 上线的必备加固。
