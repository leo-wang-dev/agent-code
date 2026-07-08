"""DeepAgents 极简上手 demo —— 5 行代码 = 一个完整 Agent。

对应文章第 30 篇「三、5 行代码 = 一个完整 Agent」。

未安装 deepagents 时打印安装指引并 exit 0（不报错、不联网）。
未配置 ANTHROPIC_API_KEY 时只演示「如何组装」，不发起真实调用。
"""

from __future__ import annotations

import os
import sys


def _think_tool(thought: str) -> str:
    """一个最小的自定义工具：让 Agent 显式写下思考（对齐 DeepAgents 的 think_tool）。"""

    return f"记录思考：{thought}"


def _web_search(query: str) -> str:
    """占位检索工具。真实项目里换成 Tavily / Bing / 自建检索。"""

    return f"[mock] 关于「{query}」检索到 3 条资料"


def main() -> int:
    try:
        from deepagents import create_deep_agent
    except ImportError:
        print("未安装 deepagents。安装方式：")
        print("    pip install deepagents")
        print("（它会自动带上 langchain>=1.2.11 与 langgraph>=1.1.1）")
        print("\n本 demo 展示的核心就是这 5 行：")
        print(
            "    agent = create_deep_agent(\n"
            "        tools=[web_search, think_tool],\n"
            "        system_prompt='You are a research assistant.',\n"
            "        subagents=[research_sub_agent],\n"
            "    )\n"
            "    result = agent.invoke({'messages': [...]})"
        )
        return 0

    # 5 行核心：工具 + system prompt + （可选）子 Agent。
    research_sub_agent = {
        "name": "researcher",
        "description": "对单个问题做深度研究的子 Agent",
        "system_prompt": "你只负责深度研究，返回结论摘要。",
    }
    agent = create_deep_agent(
        tools=[_web_search, _think_tool],
        system_prompt="You are a research assistant. 用中文回答。",
        subagents=[research_sub_agent],
    )
    print("已构建 DeepAgents 实例：内置 TODO / 虚拟文件系统 / 子Agent / 摘要压缩 / Prompt缓存。")

    if not os.getenv("ANTHROPIC_API_KEY"):
        print("\n未设置 ANTHROPIC_API_KEY，跳过真实调用。")
        print("设置后可运行：agent.invoke({'messages': [{'role':'user','content':'调研 Q235 钢板行情'}]})")
        return 0

    result = agent.invoke(
        {"messages": [{"role": "user", "content": "帮我调研 Q235 钢板供应商并给出比价建议"}]}
    )
    final = result["messages"][-1]
    print("\n=== DeepAgents 回答 ===")
    print(getattr(final, "content", final))
    return 0


if __name__ == "__main__":
    sys.exit(main())
