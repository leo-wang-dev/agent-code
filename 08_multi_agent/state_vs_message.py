"""共享状态 vs 消息传递：多 Agent 协作的两条路对照。

对应文章第 08 篇「四、协作的本质：状态还是消息」。

- 共享状态：所有 Agent 读写同一任务状态（research_notes / draft / review_comments）。
  全局可见，适合状态机和长任务；坏处是并发写入与状态污染要管好。
- 消息传递：Agent 之间通过明确消息互相交付。边界清楚易追踪；坏处是上下文重复传递。

两者都复用 src/agent_code/multi_agent.py 的 SharedState / MessageBus，
并排跑一遍同一个「研究→写作」协作，直观对照。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_code.multi_agent import MessageBus, SharedState


def run_shared_state() -> None:
    print("=== 共享状态：全局可见 ===")
    state = SharedState()
    # researcher 写入笔记，writer 从同一状态读出再写草稿。
    state.write("researcher", "notes", "来源1/来源2/来源3")
    notes = state.read_namespace("researcher")["notes"]
    state.write("writer", "draft", f"依据[{notes}]写成初稿")
    for key, value in state.values.items():
        print(f"  {key} = {value}")


def run_message_passing() -> None:
    print("\n=== 消息传递：边界清楚可追踪 ===")
    bus = MessageBus()
    bus.send("researcher", "writer", "notes: 来源1/来源2/来源3")
    inbox = bus.inbox("writer")
    delivered = inbox[0].content
    bus.send("writer", "reviewer", f"draft based on [{delivered}]")
    for message in bus.messages:
        print(f"  {message.sender} -> {message.recipient}: {message.content}")


def main() -> None:
    run_shared_state()
    run_message_passing()
    print("\n工业实践：关键业务状态放共享 State，Agent 间交互留消息记录，全部进 trace。")


if __name__ == "__main__":
    main()
