"""工具定义示例 —— CrewAI 的 @tool 装饰器。

CrewAI 的工具系统极度简洁：@tool 装饰一个纯函数，docstring 就是给 LLM 的说明，
直接把函数塞进 Agent(tools=[...])。

关键哲学："Agent 自主执行，工具只是辅助"——CrewAI 的 Tool 不能访问 State、
不能转移控制权（对比 LangGraph 的 InjectedState/Command、ADK 的 ToolContext）。
如果你要在工具里做复杂流程控制，说明该换 Flow 或 LangGraph。

工具函数本身是纯 Python，可直接调用；构造 Agent 需要占位 key。

需要依赖：pip install crewai
"""
from __future__ import annotations

import os

os.environ.setdefault("OPENAI_API_KEY", "sk-demo-placeholder")
os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")
os.environ.setdefault("CREWAI_TELEMETRY_OPT_OUT", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")

try:
    from crewai import Agent
    from crewai.tools import tool
except ImportError:
    print("需要先安装依赖：pip install crewai")
    print("（本示例演示 @tool 定义，缺少 crewai 无法运行）")
    raise SystemExit(0)


@tool("Web Search")
def search_web(query: str) -> str:
    """搜索网络获取最新信息。

    Args:
        query: 搜索关键词

    Returns:
        搜索结果文本
    """
    # 实现略：这里返回 mock 结果
    return f"关于「{query}」的搜索结果（mock）"


@tool("Read PDF")
def read_pdf(path: str) -> str:
    """读取 PDF 文件并返回文本内容。

    Args:
        path: PDF 文件路径

    Returns:
        提取出的纯文本
    """
    return f"[{path}] 的正文内容（mock）"


def main() -> None:
    # 工具是纯函数，可脱离 Agent 直接被框架调用
    print("直接调用工具（纯函数，无副作用入口）：")
    print("  search_web:", search_web.run(query="新能源汽车 2025"))
    print("  read_pdf  :", read_pdf.run(path="report.pdf"))

    # 直接把工具传给 Agent
    researcher = Agent(
        role="资深市场研究员",
        goal="找到最新趋势和数据",
        backstory="严谨的研究员",
        tools=[search_web, read_pdf],  # 直接传函数
        verbose=False,
    )
    print("\nAgent 已装载工具：", [t.name for t in researcher.tools])


if __name__ == "__main__":
    main()
