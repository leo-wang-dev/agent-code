"""DeepAgents SDK 版本对照 —— 手搓三大模式 vs SDK 内置 Middleware。

对应文章第 31 篇：三大模式在 DeepAgents 里由 Middleware 自动提供。

未安装 deepagents 时打印安装指引 + 手搓/ SDK 对照表并 exit 0（不联网）。
"""

from __future__ import annotations

import sys

# 手搓实现 <-> SDK Middleware 的对照关系。
MAPPING = [
    ("模式 1 TODO 复述", "three_patterns.TodoBoard", "TodoListMiddleware", "write_todos / read_todos"),
    ("模式 2 虚拟文件系统", "three_patterns.VirtualFileSystem", "FilesystemMiddleware", "ls/read_file/write_file/edit_file/glob/grep"),
    ("模式 3 子 Agent 隔离", "three_patterns.SubAgentIsolation", "SubAgentMiddleware", "task 工具 + 子 Agent 注册"),
    ("上下文过长自动摘要", "（手搓版未做）", "SummarizationMiddleware", "自动压缩历史"),
    ("并发写文件合并", "three_patterns.file_reducer", "file_reducer (state)", "{**left, **right}"),
]


def _print_mapping() -> None:
    print("=== 手搓三大模式  <->  DeepAgents SDK Middleware 对照 ===\n")
    for pattern, handmade, middleware, tools in MAPPING:
        print(f"{pattern}")
        print(f"    手搓：{handmade}")
        print(f"    SDK ：{middleware}  ({tools})")


def main() -> int:
    _print_mapping()
    try:
        from deepagents import create_deep_agent
    except ImportError:
        print("\n未安装 deepagents，仅展示对照表。安装：pip install deepagents")
        return 0

    # SDK 版：三大模式全由 create_deep_agent 内置 Middleware 自动挂载。
    def web_search(query: str) -> str:
        """检索工具：真实项目里换成 Tavily/Bing。"""

        return f"[mock] {query} 检索到 3 条"

    research_sub = {
        "name": "researcher",
        "description": "隔离上下文的深度研究子 Agent",
        "system_prompt": "你只做单主题深度研究，返回结论摘要。",
    }
    create_deep_agent(tools=[web_search], system_prompt="研究助手", subagents=[research_sub])
    print("\nSDK 版：5 行 create_deep_agent 已自动挂载 TodoList/Filesystem/SubAgent/Summarization 等 Middleware。")
    print("即：手搓 180 行做的三大模式，SDK 用内置 Middleware 一次性提供。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
