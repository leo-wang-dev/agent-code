# 23 CrewAI 入门：角色驱动的 Agent 团队

配套文章：《CrewAI 入门：角色驱动的 Agent 团队》

CrewAI 的心智和 LangGraph 完全不同：Agent 是"角色"，Task 是一等公民，
Crew 把它们打包 kickoff。本目录跑通三件套、两种 Process、工具、Memory、Flow。

## 安装依赖

```bash
pip install crewai
```

- 缺少 `crewai` 时脚本打印安装提示并以退出码 0 退出，不崩溃。
- CrewAI 构造 Agent 时就会初始化 LLM，因此脚本在**无 `OPENAI_API_KEY`** 时会设置一个占位 key，让所有对象照常构造（演示真实 API），仅在检测到**真实 key** 时才发起 `crew.kickoff()`。
- 脚本已设置 `CREWAI_TRACING_ENABLED=false` 等环境变量关闭首次运行的遥测/追踪交互。
- `03_tool_definition.py`（工具是纯函数）和 `05_flow.py`（Flow 路由是纯 Python）**无需真实 key 即可完整跑通**。

## 文件对照表

| 文件 | 对应产物 | 说明 | 需真实 key |
|------|----------|------|:---:|
| `01_agent_task_crew.py` | Agent / Task / Crew 三件套 | role/goal/backstory + expected_output 契约 + context 依赖 | 仅 kickoff |
| `02_process_sequential_hierarchical.py` | Sequential / Hierarchical 对照 | 流水线模式 vs 自动 Manager 经理模式 | 仅 kickoff |
| `03_tool_definition.py` | 工具定义示例 | `@tool` 装饰纯函数，装进 Agent | 否 |
| `04_memory.py` | Memory 开启 demo | `memory=True` 一行开启 Short/Long/Entity 三种记忆 | 仅 kickoff |
| `05_flow.py` | Flow 完整实现示例 | `@start`/`@router`/`@listen` 条件分支路由 | 否 |
| `demo.py` | 章节统一入口 | 委托 `series_projects.chapter_runner` | — |

## 运行

```bash
python3 03_tool_definition.py     # 无需 key
python3 05_flow.py                # 无需 key
export OPENAI_API_KEY=sk-...      # 有 key 后可跑真实 kickoff
python3 01_agent_task_crew.py
```

## 核心认知

- Agent 是"角色"：role/goal/backstory 三层人设注入 system prompt，行为比单薄的 LangGraph 节点更稳定。
- Task 是一等公民：expected_output 是输出契约，agent 显式绑定执行者，context 显式声明依赖。
- Process 二选一：80% 场景用 Sequential（可预测、可调试）；Hierarchical 的 Manager 决策本身是 LLM 调用，不稳定。
- Tool 是最简化的纯函数——不能访问 State、不能转移控制权。要复杂流程控制就上 Flow 或换 LangGraph。
- Memory 一行 `memory=True` 开启三种记忆，但默认 OpenAI Embedding 有隐藏成本。
- Flow 是 Crew 的逃生口，用于 Crew 之间的条件分支——到这一层 CrewAI 正向 LangGraph 收敛。
