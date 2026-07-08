# 27_adk_tools —— ADK Tools 体系 + agent_as_tool + Callbacks

配套文章：《ADK Tools 体系 + agent_as_tool + Callbacks》

在原有 `demo.py`（连续项目入口）之外，补齐文章文末"包含："承诺的每一件具名产物，均为**独立可运行**脚本。
约定同全系列：`google-adk` 导入 `try/except` 保护，缺依赖打印安装指引并降级到**确定性 mock**，`exit 0`；无 API key 时不联网。

其中 `function_tool_auto_schema.py` 用标准库 `inspect` + `typing` **真的把自动 Schema 生成跑了出来**（不依赖 google-adk 即可复现 ADK 的推断结果）。

## 安装（跑真实 ADK 时）

```bash
pip install google-adk
export GOOGLE_API_KEY=...   # 或 GEMINI_API_KEY
```

## 产物对照表

| 文章承诺产物 | 文件 | 说明 | 运行 |
|---|---|---|---|
| FunctionTool 自动 Schema 示例 | `function_tool_auto_schema.py` | 从类型标注+docstring 推断 JSON Schema，跳过 `tool_context` | `python3 27_adk_tools/function_tool_auto_schema.py` |
| ToolContext 完整用法 demo | `tool_context_demo.py` | state 四作用域 / actions / save_artifact 版本化 / search_memory | `python3 27_adk_tools/tool_context_demo.py` |
| agent_as_tool 完整封装示例 | `agent_as_tool.py` | AgentTool 把 Agent 包成工具 + 上下文隔离 + 与 Delegation 对比 | `python3 27_adk_tools/agent_as_tool.py` |
| 3×3 Callbacks 五种用途 | `callbacks_3x3.py` | 审计/成本/安全/参数清洗/降级 + before/after/on_error 返回值语义 | `python3 27_adk_tools/callbacks_3x3.py` |
| Callback 挂 Agent vs 工具对照 | `callback_agent_vs_tool.py` | 同一 search_web 被两个 Agent 复用，策略按 Agent 注入 | `python3 27_adk_tools/callback_agent_vs_tool.py` |

## 3×3 Callbacks 矩阵

| | before | after | on_error |
|---|---|---|---|
| Agent | before_agent | after_agent | on_agent_error |
| Model | before_model | after_model | on_model_error |
| Tool | before_tool | after_tool | on_tool_error |

返回值语义：`before_*` 非 None = 短路；`after_*` 非 None = 替换结果；`on_*_error` 非 None = 兜底。

> `demo.py` 仍是连续项目的第 27 章阶段入口，不受本目录新增文件影响。
