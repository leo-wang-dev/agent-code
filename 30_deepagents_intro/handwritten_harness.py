"""180 行手搓 Harness —— 把 DeepAgents 的三大模式拆开自己实现一遍。

对应文章第 30 篇「四、180 行手搓 vs 5 行 SDK」。

这一版不依赖 deepagents / langgraph，纯标准库实现，任何机器都能直接跑：

    python3 30_deepagents_intro/handwritten_harness.py

它把 Harness 内核拆成六段（每段行数与文章对照）：
  1. State：Todo 类型 + file_reducer + DeepAgentState        (~20 行)
  2. write_todos / read_todos 工具                            (~30 行)
  3. ls / read_file / write_file 工具                         (~50 行)
  4. _create_task_tool：子 Agent 注册 + task 工具            (~60 行)
  5. System Prompt：工作流指令                                (~20 行)
  6. 组装 + ReAct 循环                                        (~5 行)

没有 API key 时用确定性 mock「LLM」，让循环逻辑可复现、可单测。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable

# ---------------------------------------------------------------------------
# 1. State —— Todo 类型 + file_reducer + DeepAgentState  (~20 行)
# ---------------------------------------------------------------------------

Todo = dict[str, str]  # {"content": ..., "status": "pending|in_progress|completed"}


def file_reducer(left: dict[str, str] | None, right: dict[str, str] | None) -> dict[str, str]:
    """合并两个虚拟文件系统（后写覆盖），对应 LangGraph 的 reducer 语义。"""

    merged = dict(left or {})
    merged.update(right or {})
    return merged


@dataclass
class DeepAgentState:
    messages: list[dict[str, Any]] = field(default_factory=list)
    todos: list[Todo] = field(default_factory=list)
    files: dict[str, str] = field(default_factory=dict)  # 虚拟文件系统：不落磁盘

    def update_files(self, patch: dict[str, str]) -> None:
        self.files = file_reducer(self.files, patch)


# ---------------------------------------------------------------------------
# 2. write_todos / read_todos —— 任务规划 + 复述（防 Context Rot）  (~30 行)
# ---------------------------------------------------------------------------


def make_todo_tools(state: DeepAgentState) -> dict[str, Callable[..., str]]:
    def write_todos(items: list[str]) -> str:
        state.todos = [{"content": text, "status": "pending"} for text in items]
        return f"已写入 {len(items)} 条 TODO"

    def complete_todo(index: int) -> str:
        if 0 <= index < len(state.todos):
            state.todos[index]["status"] = "completed"
            return f"TODO#{index} 标记完成"
        return f"TODO#{index} 不存在"

    def read_todos() -> str:
        if not state.todos:
            return "（空）"
        lines = [
            f"[{'x' if todo['status'] == 'completed' else ' '}] {i}. {todo['content']}"
            for i, todo in enumerate(state.todos)
        ]
        return "\n".join(lines)

    return {"write_todos": write_todos, "complete_todo": complete_todo, "read_todos": read_todos}


# ---------------------------------------------------------------------------
# 3. ls / read_file / write_file —— 虚拟文件系统（防 Context Overflow） (~50 行)
# ---------------------------------------------------------------------------


def make_fs_tools(state: DeepAgentState) -> dict[str, Callable[..., str]]:
    def ls() -> str:
        return "\n".join(sorted(state.files)) or "（空目录）"

    def write_file(path: str, content: str) -> str:
        state.update_files({path: content})
        return f"已写入 {path}（{len(content)} 字符）"

    def read_file(path: str) -> str:
        return state.files.get(path, f"[错误] 文件不存在：{path}")

    def edit_file(path: str, old: str, new: str) -> str:
        if path not in state.files:
            return f"[错误] 文件不存在：{path}"
        state.update_files({path: state.files[path].replace(old, new)})
        return f"已编辑 {path}"

    return {"ls": ls, "write_file": write_file, "read_file": read_file, "edit_file": edit_file}


# ---------------------------------------------------------------------------
# 4. _create_task_tool —— 子 Agent 注册 + task 工具（防 Context Clash）(~60 行)
# ---------------------------------------------------------------------------


@dataclass
class SubAgent:
    name: str
    description: str
    system_prompt: str
    runner: Callable[[str], str]


def _create_task_tool(subagents: list[SubAgent]) -> Callable[..., str]:
    """返回一个 task 工具：主 Agent 把开放式子任务委托给隔离的子 Agent。

    子 Agent 有自己独立的上下文（这里用独立 runner 模拟），只把「结论」返回主
    Agent，主 Agent 的上下文因此不会被子任务的中间步骤污染 —— 这就是隔离。
    """

    registry = {sub.name: sub for sub in subagents}

    def task(subagent_name: str, instruction: str) -> str:
        sub = registry.get(subagent_name)
        if sub is None:
            available = "、".join(registry) or "（无）"
            return f"[错误] 未注册的子 Agent：{subagent_name}，可用：{available}"
        # 子 Agent 在独立上下文里跑，只回传摘要结论。
        summary = sub.runner(instruction)
        return f"[子Agent:{sub.name}] {summary}"

    return task


# ---------------------------------------------------------------------------
# 5. System Prompt —— 工作流指令  (~20 行)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """你是一个长任务研究助手，遵循以下工作流：
1. 收到任务先用 write_todos 拆解成 3-6 步，并复述计划。
2. 每完成一步就 complete_todo，保持对整体目标的记忆（防漂移）。
3. 中间产物（草稿、检索结果）一律 write_file 落到虚拟文件系统，
   不要把长文塞进对话（防上下文溢出）。
4. 遇到「深度研究 / 独立子任务」时，用 task 委托子 Agent，
   只接收它的结论（防上下文冲突）。
5. 所有 TODO 完成后，read_file 汇总产出最终答案。
"""


# ---------------------------------------------------------------------------
# 6. 组装 + ReAct 循环  (~5 行 + mock LLM)
# ---------------------------------------------------------------------------


def _mock_llm(state: DeepAgentState, step: int) -> dict[str, Any]:
    """确定性 mock：无 API key 时驱动一条可复现的 ReAct 轨迹。

    真实实现里这里换成 Anthropic /v1/messages 调用（见 deepagents_minimal.py）。
    """

    plan = [
        {"tool": "write_todos", "args": {"items": ["检索资料", "委托深度研究", "写报告"]}},
        {"tool": "read_todos", "args": {}},
        {"tool": "write_file", "args": {"path": "notes.md", "content": "检索到 3 条供应商资料"}},
        {"tool": "complete_todo", "args": {"index": 0}},
        {"tool": "task", "args": {"subagent_name": "researcher", "instruction": "深挖 Q235 行情"}},
        {"tool": "complete_todo", "args": {"index": 1}},
        {"tool": "write_file", "args": {"path": "report.md", "content": "# 比价报告\n供应商B 更优"}},
        {"tool": "complete_todo", "args": {"index": 2}},
    ]
    if step < len(plan):
        return plan[step]
    return {"tool": "finish", "args": {}}


def create_deep_agent(
    tools: dict[str, Callable[..., str]] | None = None,
    system_prompt: str = SYSTEM_PROMPT,
    subagents: list[SubAgent] | None = None,
    max_steps: int = 12,
):
    """手搓版 create_deep_agent —— 与 SDK 同名同形，暴露相同的 5 行心智。"""

    state = DeepAgentState()
    registry: dict[str, Callable[..., str]] = {}
    registry.update(make_todo_tools(state))
    registry.update(make_fs_tools(state))
    registry["task"] = _create_task_tool(subagents or [])
    registry.update(tools or {})

    def invoke(user_input: str) -> dict[str, Any]:
        state.messages.append({"role": "system", "content": system_prompt})
        state.messages.append({"role": "user", "content": user_input})
        trace: list[str] = []
        for step in range(max_steps):
            action = _mock_llm(state, step)
            if action["tool"] == "finish":
                break
            fn = registry.get(action["tool"])
            observation = fn(**action["args"]) if fn else f"[错误] 未知工具 {action['tool']}"
            trace.append(f"step={step} {action['tool']}({action['args']}) -> {observation}")
        return {
            "answer": state.files.get("report.md", "（无产出）"),
            "todos": state.todos,
            "files": list(state.files),
            "trace": trace,
        }

    return type("HandwrittenHarness", (), {"invoke": staticmethod(invoke), "state": state})()


def main() -> None:
    researcher = SubAgent(
        name="researcher",
        description="深度研究子 Agent，独立上下文",
        system_prompt="你只做资料调研，返回一句话结论。",
        runner=lambda instruction: f"结论：{instruction} -> 现货偏紧、报价上行",
    )
    agent = create_deep_agent(
        tools={"web_search": lambda q: f"搜索：{q}"},
        subagents=[researcher],
    )
    result = agent.invoke("帮我对 Q235 钢板做一次深度比价并出报告")
    print("=== 手搓 Harness 运行轨迹 ===")
    for line in result["trace"]:
        print(" ", line)
    print("\n=== TODO 状态 ===")
    print(json.dumps(result["todos"], ensure_ascii=False, indent=2))
    print("\n=== 虚拟文件系统 ===", result["files"])
    print("\n=== 最终答案 ===\n", result["answer"])


if __name__ == "__main__":
    main()
