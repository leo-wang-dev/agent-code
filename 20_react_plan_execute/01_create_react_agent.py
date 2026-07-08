"""`create_react_agent` 极简版 —— 一行代码替代第 10 篇 200 行手搓 ReAct 循环。

有 OPENAI_API_KEY 时用真实 ChatOpenAI；否则用一个极简的 FakeToolCallingModel，
让示例在无网络、无密钥的情况下也能完整跑通 ReAct 循环（思考 → 调工具 → 回答）。

需要依赖：pip install langgraph langchain-openai
"""
from __future__ import annotations

import os

try:
    from langchain_core.tools import tool
    from langchain_core.messages import AIMessage, ToolMessage
    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_core.outputs import ChatResult, ChatGeneration
    from langgraph.prebuilt import create_react_agent
except ImportError:
    print("需要先安装依赖：pip install langgraph langchain-openai")
    print("（本示例演示 create_react_agent，缺少 langgraph/langchain 无法运行）")
    raise SystemExit(0)


@tool
def get_weather(city: str) -> str:
    """查询指定城市的天气。"""
    return f"{city}今天多云，25°C。"


@tool
def calculate(expr: str) -> str:
    """计算一个算术表达式。"""
    return str(eval(expr, {"__builtins__": {}}, {}))  # noqa: S307 (demo)


@tool
def search_web(query: str) -> str:
    """联网搜索。"""
    return f"关于「{query}」的搜索结果（mock）。"


class FakeToolCallingModel(BaseChatModel):
    """极简可调用工具的假模型：第一轮发起 get_weather 调用，第二轮给出最终答复。"""

    @property
    def _llm_type(self) -> str:
        return "fake-tool-calling"

    def bind_tools(self, tools, **kwargs):  # create_react_agent 会调用它
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        has_tool_result = any(isinstance(m, ToolMessage) for m in messages)
        if has_tool_result:
            msg = AIMessage(content="上海今天多云，25°C，适合出行。")
        else:
            msg = AIMessage(
                content="",
                tool_calls=[{"name": "get_weather", "args": {"city": "上海"}, "id": "call_1"}],
            )
        return ChatResult(generations=[ChatGeneration(message=msg)])


def build_llm():
    if os.getenv("OPENAI_API_KEY"):
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model="gpt-4o")
    print("（未检测到 OPENAI_API_KEY，使用 FakeToolCallingModel 演示）")
    return FakeToolCallingModel()


def main() -> None:
    llm = build_llm()
    tools = [get_weather, calculate, search_web]  # 跟第 10 篇一样的三个工具

    agent = create_react_agent(llm, tools)

    result = agent.invoke(
        {"messages": [{"role": "user", "content": "上海今天天气怎么样？"}]}
    )
    print(result["messages"][-1].content)


if __name__ == "__main__":
    main()
