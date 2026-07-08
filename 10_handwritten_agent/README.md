# 10 不用框架，200 行手写工业级雏形 Agent — 配套代码

对应文章《不用框架，200 行 Python 手写一个工业级雏形 Agent》。

本章的核心是「不用任何 Agent 框架，纯原生 Python 手写」。因此这里的基础版和
plus 版都**自包含**（只用 stdlib + 同目录文件），不导入 `src/agent_code` 的循环
框架，忠实还原文章「亲手把零件粘起来一次」的意图。无需 API key，离线可跑。

## 产物对照表

| 文章承诺 | 文件 | 说明 |
| --- | --- | --- |
| 两文件基础版 · 工具层 | `tools.py` | 工具函数 + schema + 注册表（受限 AST 求值，非裸 eval） |
| 两文件基础版 · Agent 主体 | `agent.py` | 消息管理 + ReAct 主循环 + 终止条件 + 错误分类 + trace |
| plus 版（流式 + 持久化） | `agent_plus.py` | 逐 token 流式输出 + JSON 状态落盘断点恢复 |
| 汇总入口 | `run_demo.py` | 原有委托 `src/agent_code` 的组合 demo |

## 基础版覆盖的工业级要点（对应文章各节）

- 消息管理（三）：自己维护 system/user/assistant/tool 四类 messages。
- ReAct 主循环（四）：模型要么给最终答案，要么请求工具调用。
- 终止条件（四）：最大轮数 + 重复动作检测，而不是裸 `while True`。
- 错误处理（五）：工具异常分类（临时/权限/参数/未知），不 `except: pass`。
- Trace（六）：每步 thought / tool / arguments / observation / error_class 全记录。

## 运行

```bash
python3 10_handwritten_agent/tools.py        # 只看工具层
python3 10_handwritten_agent/agent.py        # 基础版完整循环
python3 10_handwritten_agent/agent_plus.py   # plus 版：流式 + 持久化
python3 10_handwritten_agent/run_demo.py     # src 版组合 demo
```

`agent.py` 依赖同目录 `tools.py`，`agent_plus.py` 依赖同目录 `agent.py` 与
`tools.py`，因此直接 `python3 10_handwritten_agent/<file>.py` 运行即可（脚本目录
会自动进入 import 路径）。
