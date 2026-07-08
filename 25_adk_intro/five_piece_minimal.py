"""五件套最小示例 —— Agent / Tool / Runner / Session / Events。

对应文章《Google ADK 入门 —— 五件套心智模型》第四节"最小可跑示例"。

设计约定（本章所有脚本一致）：
- google-adk 的导入全部用 try/except 保护；缺依赖时打印安装指引，
  并继续用"确定性 mock"演示同一套 API 形态，最后 exit 0。
- 真实 ADK 的模型调用需要 GOOGLE_API_KEY / GEMINI_API_KEY；无 key 时用 mock。

真实 ADK 写法（文章正文展示，仅在装了 google-adk 时可跑）：

    from google.adk.agents import LlmAgent
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.adk.app import App

    def get_weather(city: str) -> dict:
        '''查询指定城市的天气。'''
        return {"city": city, "temp": "22C", "condition": "多云"}

    weather_agent = LlmAgent(
        name="weather_assistant",
        model="gemini-2.0-flash",
        instruction="你是一个天气助手，用户问天气时调用 get_weather。",
        tools=[get_weather],
    )
    app = App(name="weather_app", root_agent=weather_agent)
    runner = Runner(app=app, session_service=InMemorySessionService())

    async for event in runner.run_async(
        user_id="user_1", session_id="session_1",
        new_message="北京今天天气怎么样？",
    ):
        if event.content:
            print(event.author, event.content.parts[0].text)
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from typing import Callable

try:  # google-adk 导入全部 try/except 保护
    from google.adk.agents import LlmAgent  # noqa: F401
    from google.adk.runners import Runner  # noqa: F401
    from google.adk.sessions import InMemorySessionService  # noqa: F401

    HAS_ADK = True
except ImportError:
    HAS_ADK = False


def install_hint() -> None:
    print("[提示] 未检测到 google-adk，使用确定性 mock 演示五件套。")
    print("       安装真实框架： pip install google-adk")
    print("       配置模型密钥： export GOOGLE_API_KEY=...  (或 GEMINI_API_KEY)")
    print("-" * 60)


# ---------------------------------------------------------------------------
# 确定性 mock：镜像 ADK 五件套的 API 形态，无网络、无 key 即可运行
# ---------------------------------------------------------------------------
@dataclass
class MockPart:
    text: str


@dataclass
class MockContent:
    parts: list


@dataclass
class MockEvent:
    author: str
    content: MockContent | None = None


@dataclass
class MockSession:
    user_id: str
    session_id: str
    events: list = field(default_factory=list)


class MockSessionService:
    """对应 InMemorySessionService。"""

    def __init__(self) -> None:
        self._store: dict[tuple[str, str], MockSession] = {}

    def get_or_create(self, user_id: str, session_id: str) -> MockSession:
        key = (user_id, session_id)
        if key not in self._store:
            self._store[key] = MockSession(user_id, session_id)
        return self._store[key]


@dataclass
class MockAgent:
    """对应 LlmAgent。"""

    name: str
    instruction: str
    tools: list = field(default_factory=list)


@dataclass
class MockApp:
    name: str
    root_agent: MockAgent


class MockRunner:
    """对应 Runner —— 把五件套组装起来跑，产出事件流。"""

    def __init__(self, app: MockApp, session_service: MockSessionService) -> None:
        self.app = app
        self.session_service = session_service

    def run(self, user_id: str, session_id: str, new_message: str):
        session = self.session_service.get_or_create(user_id, session_id)
        agent = self.app.root_agent

        # 事件 1：用户消息进入
        yield MockEvent("user", MockContent([MockPart(new_message)]))

        # 事件 2：Agent 决定调用工具（确定性路由：命中城市名即调用天气工具）
        tool = _pick_tool(agent.tools, new_message)
        if tool is not None:
            city = _extract_city(new_message)
            result = tool(city)
            yield MockEvent(tool.__name__, MockContent([MockPart(str(result))]))
            reply = f"{result['city']}今天{result['condition']}，气温{result['temp']}。"
        else:
            reply = "（mock）没有匹配到工具，直接回答。"

        # 事件 3：Agent 最终回复
        final = MockEvent(agent.name, MockContent([MockPart(reply)]))
        session.events.append(final)
        yield final


def _pick_tool(tools: list[Callable], message: str) -> Callable | None:
    return tools[0] if tools else None


def _extract_city(message: str) -> str:
    for city in ("北京", "上海", "深圳", "广州"):
        if city in message:
            return city
    return "北京"


# ---------------------------------------------------------------------------
# Step 1: Tool —— 普通 Python 函数 + 类型标注 + docstring
# ---------------------------------------------------------------------------
def get_weather(city: str) -> dict:
    """查询指定城市的天气（确定性 mock 数据）。"""
    table = {
        "北京": {"temp": "22C", "condition": "多云"},
        "上海": {"temp": "26C", "condition": "小雨"},
    }
    info = table.get(city, {"temp": "20C", "condition": "晴"})
    return {"city": city, **info}


def main() -> int:
    if not HAS_ADK:
        install_hint()

    # Step 2-4: Agent -> App -> Runner
    agent = MockAgent(
        name="weather_assistant",
        instruction="你是一个天气助手，用户问天气时调用 get_weather 工具。",
        tools=[get_weather],
    )
    app = MockApp(name="weather_app", root_agent=agent)
    runner = MockRunner(app=app, session_service=MockSessionService())

    # Step 5: 跑起来 —— 消费事件流
    print("== 五件套最小示例：事件流输出 ==")
    for event in runner.run(
        user_id="user_1",
        session_id="session_1",
        new_message="北京今天天气怎么样？",
    ):
        if event.content:
            print(f"[{event.author}] {event.content.parts[0].text}")

    if os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"):
        print("\n[提示] 检测到模型密钥，可把上面 Mock* 替换成真实 LlmAgent/Runner。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
