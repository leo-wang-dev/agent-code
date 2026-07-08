"""三大 Context Engineering 模式的完整手搓实现。

对应文章第 31 篇一~三节。三个模式各自独立可跑、可单测，纯标准库：

    python3 31_context_engineering/three_patterns.py

  模式 1  TodoBoard          治 Context Rot（漂移）  —— 全量覆盖 + 复述
  模式 2  VirtualFileSystem  治 Context Overflow（溢出）—— 上下文卸载 + file_reducer
  模式 3  SubAgentIsolation  治 Context Clash（冲突）  —— messages 隔离、files 共享
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

# ---------------------------------------------------------------------------
# 模式 1：TODO 规划 + 复述 —— 治 Context Rot
# ---------------------------------------------------------------------------


@dataclass
class TodoBoard:
    """全量覆盖（非增量 append），强制 LLM 每次审视完整任务列表。"""

    todos: list[dict[str, str]] = field(default_factory=list)

    def write_todos(self, items: list[str]) -> str:
        # 关键：完全覆盖，不是 append —— 强制复述。
        self.todos = [{"content": text, "status": "pending"} for text in items]
        return f"已写入 {len(items)} 条 TODO（全量覆盖）"

    def complete(self, index: int) -> str:
        self.todos[index]["status"] = "completed"
        return f"TODO#{index} 完成"

    def read_todos(self) -> str:
        """把目标复述到上下文末尾，对抗 Lost in the Middle + Recency Bias。"""

        icon = {"pending": "⏳", "completed": "✅"}
        lines = [f"{i}. {icon[t['status']]} {t['content']}" for i, t in enumerate(self.todos)]
        return "Current TODO List:\n" + "\n".join(lines)


# ---------------------------------------------------------------------------
# 模式 2：虚拟文件系统 —— 治 Context Overflow
# ---------------------------------------------------------------------------


def file_reducer(left: dict[str, str], right: dict[str, str]) -> dict[str, str]:
    """并发写入的优雅合并：新覆盖旧，两个子 Agent 写不同文件不会 race。"""

    return {**left, **right}


@dataclass
class VirtualFileSystem:
    """State 里的 files dict，不落磁盘。工具返回大数据时：存文件 + 只回摘要。"""

    files: dict[str, str] = field(default_factory=dict)

    def ls(self) -> list[str]:
        return sorted(self.files)

    def write_file(self, name: str, content: str) -> str:
        self.files = file_reducer(self.files, {name: content})
        return f"已写入 {name}（{len(content)} 字符）"

    def read_file(self, name: str) -> str:
        return self.files.get(name, f"[错误] 文件不存在：{name}")

    def grep(self, pattern: str) -> list[str]:
        return [name for name, body in self.files.items() if pattern in body]

    def offload_tool_result(self, name: str, big_content: str, summary: str) -> str:
        """上下文卸载：完整数据进文件，messages 只放摘要 + 索引。"""

        self.write_file(name, big_content)
        return f"{summary}（完整 {len(big_content)} 字已存 {name}，用 read_file 取详情）"


# ---------------------------------------------------------------------------
# 模式 3：子 Agent 隔离 —— 治 Context Clash
# ---------------------------------------------------------------------------


@dataclass
class SubAgent:
    name: str
    runner: Callable[[str, VirtualFileSystem], str]


class SubAgentIsolation:
    """task 工具：子 Agent messages 全新隔离，files 共享，todos 不传。"""

    def __init__(self, shared_fs: VirtualFileSystem) -> None:
        self.shared_fs = shared_fs
        self.registry: dict[str, SubAgent] = {}
        self.isolation_log: list[str] = []

    def register(self, sub: SubAgent) -> None:
        self.registry[sub.name] = sub

    def task(self, subagent_name: str, description: str) -> str:
        sub = self.registry[subagent_name]
        # 子 Agent 只看到自己的任务描述（全新 messages），但共享 files。
        self.isolation_log.append(f"{subagent_name} 独立上下文启动：{description[:20]}")
        summary = sub.runner(description, self.shared_fs)  # files 共享传入
        # 只把结论摘要回流主 Agent（messages 不共享）。
        return f"[子Agent:{subagent_name} 完成] {summary}"


def _demo() -> None:
    print("=== 模式 1：TODO 复述（治漂移）===")
    board = TodoBoard()
    print(board.write_todos(["Research costs", "Research impact", "Research adoption", "Synthesize"]))
    board.complete(0)
    print(board.read_todos())

    print("\n=== 模式 2：虚拟文件系统（治溢出）===")
    fs = VirtualFileSystem()
    big = "太阳能面板成本数据" * 500  # 模拟 8000 字网页
    print(fs.offload_tool_result("costs_solar.md", big, "找到 3 条成本资料"))
    print("ls:", fs.ls(), "| grep 成本:", fs.grep("成本"))

    print("\n=== 模式 3：子 Agent 隔离（治冲突）===")
    iso = SubAgentIsolation(fs)
    for company in ["OpenAI", "Anthropic", "DeepMind"]:
        iso.register(
            SubAgent(
                name=f"research-{company}",
                runner=(lambda c: lambda desc, shared: (
                    shared.write_file(f"{c}.md", f"{c} 安全工作详情"),
                    f"{c} 安全工作已研究，结论存 {c}.md",
                )[1])(company),
            )
        )
        print(iso.task(f"research-{company}", f"Research {company}'s AI safety work"))
    print("隔离日志：", iso.isolation_log)
    print("共享文件系统最终包含：", fs.ls())


if __name__ == "__main__":
    _demo()
