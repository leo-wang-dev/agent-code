"""Event Sourcing 审计追溯脚本。

对应文章第五节"Event Sourcing —— ADK 的审计杀手锏"。

每次 state 写、artifact 保存、工具调用都自动生成不可变 Event，追加到
session.events。审计时遍历 events 即可完整还原"数据从哪来、经过谁、变成什么"。

真实 ADK 里：
    for event in session.events:
        print(event.author, event.actions.state_delta, event.actions.artifact_delta)

本脚本用确定性 mock 复刻第六节的"生成 Q3 销售报告"完整场景，产出事件流，
再演示按字段级粒度追溯某个值是被谁、在第几步改的。
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field


@dataclass(frozen=True)  # Event 不可变
class Actions:
    state_delta: dict = field(default_factory=dict)
    artifact_delta: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Event:
    step: int
    author: str
    message: str = ""
    actions: Actions = field(default_factory=Actions)


def build_session_events() -> list[Event]:
    """复刻文章"生成 Q3 销售报告"场景的 10 步事件流。"""
    return [
        Event(1, "main_agent", "读取用户角色", Actions(state_delta={"user:role": "sales_lead"})),
        Event(2, "main_agent", "读取模板偏好",
              Actions(state_delta={"user:report_template_preference": "标准季度模板"})),
        Event(3, "main_agent", "激活 report_generation 技能(自建模式)",
              Actions(state_delta={"active_skills": ["report_generation"]})),
        Event(4, "memory_tool", "跨会话检索 Q3 sales"),
        Event(5, "fetch_data_tool", "拉取真实销售数据"),
        Event(6, "analyze_tool", "分析数据",
              Actions(state_delta={"q3_growth": "12%"})),
        Event(7, "report_tool", "保存报告 v0",
              Actions(artifact_delta={"Q3_report.md": 0})),
        Event(8, "review_tool", "审校 v0"),
        Event(9, "report_tool", "保存报告 v1(最终)",
              Actions(artifact_delta={"Q3_report.md": 1})),
        Event(10, "main_agent", "更新全局计数",
              Actions(state_delta={"app:total_reports_generated": 1})),
    ]


def print_stream(events: list[Event]) -> None:
    print("== 事件流（不可变，永久记录） ==")
    for ev in events:
        print(f"  [step {ev.step:>2}] {ev.author}: {ev.message}")
        if ev.actions.state_delta:
            print(f"           state_delta:    {ev.actions.state_delta}")
        if ev.actions.artifact_delta:
            print(f"           artifact_delta: {ev.actions.artifact_delta}")


def trace_field(events: list[Event], key: str) -> None:
    print(f"\n== 字段级追溯：'{key}' 的每一次变更 ==")
    found = False
    for ev in events:
        if key in ev.actions.state_delta:
            found = True
            print(f"   step {ev.step} 由 {ev.author} 改为 {ev.actions.state_delta[key]!r}")
    if not found:
        print("   （无变更记录）")


def trace_artifact(events: list[Event], name: str) -> None:
    print(f"\n== 产物追溯：'{name}' 的版本历史 ==")
    for ev in events:
        if name in ev.actions.artifact_delta:
            print(f"   step {ev.step} 由 {ev.author} 保存 v{ev.actions.artifact_delta[name]}")


def main() -> int:
    try:  # google-adk 导入 try/except 保护
        from google.adk.events import Event as _Real  # noqa: F401

        has_adk = True
    except ImportError:
        has_adk = False

    if not has_adk:
        print("[提示] 未检测到 google-adk，使用确定性 mock Event 流演示审计追溯。")
        print("       安装： pip install google-adk")
        print("-" * 60)

    events = build_session_events()
    print_stream(events)
    trace_field(events, "active_skills")
    trace_artifact(events, "Q3_report.md")

    print("\n工业级价值：字段级/产物级原子 Event -> 客户问'为什么是这个金额'可完整回放。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
