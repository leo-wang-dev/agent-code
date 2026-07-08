# 07 Agent 循环的本质 — 配套代码

对应文章《Agent 循环的本质：一边想，一边动，一边修正》。

Agent 循环 = 一个反复调用 LLM 的 while 循环。每一轮模型要么给最终答案，
要么请求你的代码再执行一个动作。本目录把文章承诺的每个具名产物落成可离线
运行的文件（无需 API key，`get_weather` / `calculate` 用确定性 mock）。

## 产物对照表

| 文章承诺 | 文件 | 说明 |
| --- | --- | --- |
| ReAct 循环 | `react_loop.py` | Thought → Action → Observation 回填的多轮循环 |
| Plan-and-Execute | `plan_and_execute.py` | 先规划完整步骤，再逐步执行校验 |
| 终止防护 | `termination_guard.py` | 四层：最大迭代 / token 总预算 / 重复动作 / 业务状态机 |
| 同义循环检测 | `semantic_loop_detector.py` | 精确重复 + 参数归一化后的同义重复检测 |
| Token 预算守卫 | `token_budget_guard.py` | 任务级（非每轮）总预算，超支即停 |
| AgentExecutor 重写版 | `agent_executor_rewrite.py` | 收紧守卫 + 错误分类 + 状态持久化 + 完整 trace |
| 汇总入口 | `run_demo.py` | 原有委托 `src/agent_code` 的组合 demo |

## 运行

```bash
python3 07_agent_loop/react_loop.py
python3 07_agent_loop/plan_and_execute.py
python3 07_agent_loop/termination_guard.py
python3 07_agent_loop/semantic_loop_detector.py
python3 07_agent_loop/token_budget_guard.py
python3 07_agent_loop/agent_executor_rewrite.py
python3 07_agent_loop/run_demo.py
```

## 复用关系

底层能力在 `src/agent_code/agent_loop.py`（`ReactAgent` / `PlanAndExecute` /
`TerminationGuard` / `JsonStateStore` / `detect_semantic_loop` /
`rewrite_agent_executor`）与 `tool_essence.py`、`llm_call.py`。本目录的文件是
面向文章具名产物的、可单独运行的教学封装，不重复造轮子。
