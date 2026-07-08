# 06 · Function Calling 的本质：让模型先想清楚再动手

对应文章《Function Calling 的本质：让模型先想清楚再动手》（系列第 06 篇）。文末承诺本目录包含：两轮 Function Calling demo、并行 tool_calls、极简 MCP Server、Skill 封装、幂等中间件、错误翻译层。

Function Calling 的本质：模型负责决策（该调哪个函数、参数是什么），你的代码负责执行，模型再负责解释结果。真正危险、复杂、需要工程能力的部分都在你的代码里。全部离线可跑、确定性输出。

## 产物 → 文件 → 运行命令

| 承诺产物 | 文件 | 运行命令 |
|---|---|---|
| 两轮 Function Calling demo | `two_round_function_calling.py` | `python3 two_round_function_calling.py` |
| 并行 tool_calls（并发执行 + 结果聚合 + 失败隔离） | `parallel_tool_calls.py` | `python3 parallel_tool_calls.py` |
| 极简 MCP Server（JSON-RPC tools/list、tools/call） | `minimal_mcp_server.py` | `python3 minimal_mcp_server.py` |
| Skill 封装（一组工具 + 引导 Prompt + 资源） | `skill_packaging.py` | `python3 skill_packaging.py` |
| 幂等中间件（idempotency_key，重试只执行一次） | `idempotency_middleware.py` | `python3 idempotency_middleware.py` |
| 错误翻译层（异常 → 结构化可决策错误） | `error_translation.py` | `python3 error_translation.py` |
| 汇总（两轮调用 + MCP 一把跑） | `run_demo.py` | `python3 run_demo.py` |

## 一次跑全部

```bash
for f in two_round_function_calling parallel_tool_calls minimal_mcp_server skill_packaging idempotency_middleware error_translation; do
  echo "===== $f ====="; python3 "$f.py"; echo
done
```

## 复用的核心实现

复用 `src/agent_code/tool_essence.py`：`Tool` / `ToolRegistry` / `default_registry`（工具定义与 schema）、`FunctionCallingDemo`（两轮交互）、`execute_tool_calls_parallel`（并发）、`MinimalMCPServer`（MCP）、`Skill`（能力封装）、`IdempotencyStore`（幂等）、`ErrorTranslator`（错误翻译）、`safe_calculate`（AST 安全求值）。
