"""产物：极简 MCP Server（对应文章 §五 "MCP 的本质"）。

MCP 要解决集成爆炸：N 个 Agent × M 个工具系统 = N×M 个集成。工具方实现 MCP Server，
Agent 方实现 MCP Client，双方遵守协议，工具就能被不同 Agent 发现、读 schema、调用——
让工具像 USB 一样可插拔。

MCP 基于 JSON-RPC 2.0。本文件用仓库 MinimalMCPServer 演示两个核心方法：
  tools/list  → 发现有哪些工具（返回 schema）
  tools/call  → 调用某个工具
外加一个非法 method，展示标准错误响应。全程离线，纯内存 JSON-RPC。

    python3 minimal_mcp_server.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_code.tool_essence import MinimalMCPServer, default_registry


def rpc(server: MinimalMCPServer, request: dict) -> None:
    print(f"→ 请求 : {json.dumps(request, ensure_ascii=False)}")
    response = server.handle(request)
    print(f"← 响应 : {json.dumps(response, ensure_ascii=False)}\n")


def main() -> None:
    server = MinimalMCPServer(default_registry())

    print("① tools/list —— Agent 发现工具（拿到 schema）")
    rpc(server, {"jsonrpc": "2.0", "id": 1, "method": "tools/list"})

    print("② tools/call —— Agent 调用工具")
    rpc(server, {
        "jsonrpc": "2.0", "id": 2, "method": "tools/call",
        "params": {"name": "get_weather", "arguments": {"city": "Shanghai"}},
    })

    print("③ 非法 method —— 标准 JSON-RPC 错误响应")
    rpc(server, {"jsonrpc": "2.0", "id": 3, "method": "tools/teleport"})

    print("同一个 registry，换成 Slack / Claude Desktop / 自研 Agent 都能连——")
    print("这就是把工具做成可插拔基础设施的意义。")


if __name__ == "__main__":
    main()
