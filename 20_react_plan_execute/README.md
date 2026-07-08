# 20 用 LangGraph 重写 ReAct 与 Plan-and-Execute

配套文章：《用 LangGraph 重写 ReAct + Plan-and-Execute》

一行 `create_react_agent` 替代第 10 篇 200 行手搓循环；再看 LangGraph 里
ReAct / Plan-and-Execute / 分阶段级联三种范式怎么落地，以及默认配置埋了哪些坑。

## 安装依赖

```bash
pip install langgraph langchain-openai
```

- 所有示例缺少 `langgraph` 时会打印安装提示并以退出码 0 退出，不崩溃。
- `01_create_react_agent.py` 有 `OPENAI_API_KEY` 时用真实 `ChatOpenAI`，否则自动切换到内置的 `FakeToolCallingModel`，无密钥也能完整跑通 ReAct 循环。
- 其余示例的节点均为纯 Python / mock 逻辑，不需要密钥。

> 注：LangGraph V1.0 起 `create_react_agent` 已迁移到 `langchain.agents.create_agent`，运行时会有 Deprecation 提示，不影响示例运行。

## 文件对照表

| 文件 | 对应产物 | 说明 | 需要密钥 |
|------|----------|------|:---:|
| `01_create_react_agent.py` | `create_react_agent` 极简版 | 一行代码跑 ReAct；无密钥时用 FakeToolCallingModel | 可选 |
| `02_custom_react_graph.py` | 自定义 ReAct 图 | 两节点 + 条件路由，补上 `step_count` 强制终止（修坑 1/2） | 否 |
| `03_plan_and_execute.py` | Plan-and-Execute 完整实现 | Planner / Executor / Replanner 三节点结构 | 否 |
| `04_staged_cascade.py` | 分阶段级联模式 | 分类(Python) → 分支处理 → 格式化输出(Python) | 否 |
| `05_fanout_fanin.py` | 并行 fan-out/fan-in 示例 | 并行三路检索 + reducer 汇合 | 否 |
| `06_conditional_loop.py` | 条件循环示例 | draft → review → revise 循环，直到评审通过 | 否 |
| `demo.py` | 章节统一入口 | 委托 `series_projects.chapter_runner` | — |

## 运行

```bash
python3 01_create_react_agent.py
python3 03_plan_and_execute.py
python3 05_fanout_fanin.py
```

## 核心认知

- ReAct 是一张极简状态图（两节点 + 条件路由），不是黑盒 while 循环。
- `create_react_agent` 默认配置全是 demo 级（无 max_iterations、错误吞掉、状态在内存、无 Token 守卫），必须当半成品加固。
- 范式按场景选：探索性任务用 ReAct，步骤可枚举用 Plan-and-Execute，生产里大多是分阶段级联。
- 只在真正需要 LLM 思考的地方用 LLM，意图分类 / 格式化用 Python 写死，成本和延迟低一个数量级。
