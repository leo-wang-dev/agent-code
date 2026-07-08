"""Event 事件流捕获脚本。

对应文章第二节"Events —— 事件流"。

ADK 的执行模型不是调用栈，是事件流：每次 Runner 执行 Agent，所有发生的
事都被序列化成不可变 Event，追加到 session.events。每个 Event 含：
    author               谁产生的（Agent name / Tool name）
    content              内容（LLM 输出 / Tool 返回）
    actions.state_delta  这一步对 state 的修改
    actions.artifact_delta  这一步保存了哪些 artifacts
    actions.escalate / skip_summarization  流程控制信号

真实 ADK 里遍历事件：
    session = await session_service.get_session(...)
    for event in session.events:
        print(event.author, event.actions.state_delta)

本脚本用确定性 mock 产生一条典型事件流（用户消息 -> 工具调用带 state_delta
-> Agent 回复），并演示"审计回放"：完整追踪数据从哪来、经过谁、变成什么。
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field

try:  # google-adk 导入 try/except 保护
    from google.adk.events import Event  # noqa: F401

    HAS_ADK = True
except ImportError:
    HAS_ADK = False


@dataclass(frozen=True)  # Event 不可变
class EventActions:
    state_delta: dict = field(default_factory=dict)
    artifact_delta: dict = field(default_factory=dict)
    escalate: bool = False
    skip_summarization: bool = False


@dataclass(frozen=True)
class Event:  # 与 ADK Event 同名同形（mock）
    author: str
    text: str | None = None
    actions: EventActions = field(default_factory=EventActions)


def simulate_run() -> list[Event]:
    """产生一条典型事件流（确定性）。"""
    return [
        Event(author="user", text="帮我查北京天气并记住我用中文"),
        Event(
            author="get_weather",
            text="{'city': '北京', 'temp': '22C'}",
            actions=EventActions(
                state_delta={"search_count": 1, "user:language": "Chinese"},
            ),
        ),
        Event(
            author="save_report",
            text="已保存天气报告",
            actions=EventActions(
                artifact_delta={"weather_report.md": 1},  # 版本号 1
            ),
        ),
        Event(
            author="weather_assistant",
            text="北京今天多云，22C。已记住你使用中文。",
            actions=EventActions(skip_summarization=False),
        ),
    ]


def print_event_stream(events: list[Event]) -> None:
    print("== 原始事件流 ==")
    for i, ev in enumerate(events):
        print(f"[{i}] author={ev.author}")
        if ev.text:
            print(f"      content: {ev.text}")
        if ev.actions.state_delta:
            print(f"      state_delta:    {ev.actions.state_delta}")
        if ev.actions.artifact_delta:
            print(f"      artifact_delta: {ev.actions.artifact_delta}")
        if ev.actions.escalate:
            print("      escalate: True")


def replay_audit(events: list[Event]) -> None:
    """审计回放：从事件流重建最终 state 和 artifact 版本。"""
    print("\n== 审计回放：从事件流重建 state / artifacts ==")
    state: dict = {}
    artifacts: dict = {}
    for ev in events:
        for key, value in ev.actions.state_delta.items():
            state[key] = value
            print(f"  {ev.author} 修改 state[{key!r}] = {value!r}")
        for name, version in ev.actions.artifact_delta.items():
            artifacts[name] = version
            print(f"  {ev.author} 保存 artifact {name!r} -> v{version}")
    print(f"\n  最终 state:     {state}")
    print(f"  最终 artifacts: {artifacts}")


def main() -> int:
    if not HAS_ADK:
        print("[提示] 未检测到 google-adk，使用确定性 mock 演示事件流捕获。")
        print("       安装： pip install google-adk")
        print("-" * 60)

    events = simulate_run()
    print_event_stream(events)
    replay_audit(events)

    print("\n工业级价值：Event 不可变 + 细粒度（每个工具调用都是一个 Event）"
          "= 完整审计日志 + 流程回放。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
