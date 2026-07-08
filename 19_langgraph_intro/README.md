# 19 LangGraph 入门：状态机驱动的 Agent

配套文章：《LangGraph 入门：状态机驱动的 Agent》

LangGraph 的入门门槛只有 5 个概念：State / Node / StateGraph / Edge / Compile。
本目录把这 5 个概念逐个拆成可运行示例，再拼成一个完整的"分类 → 处理 → 输出"小图。

## 安装依赖

```bash
pip install langgraph langchain-openai
```

- 纯概念示例（`01_state.py`、`02_node.py`）与 reducer 对照实验的模拟分支，**无需任何依赖**即可运行。
- 涉及真实图（StateGraph / Edge / compile）的示例需要 `langgraph`。缺少依赖时脚本会打印安装提示并以退出码 0 正常退出，不会崩溃。
- 本章示例**不需要** `OPENAI_API_KEY`——所有节点都是纯 Python 逻辑（这正是 LangGraph 的卖点：只在真正需要思考的地方才用 LLM）。

## 文件对照表

| 文件 | 对应产物 | 说明 | 需要 langgraph |
|------|----------|------|:---:|
| `01_state.py` | 核心概念 1：State | TypedDict 静态契约 + Annotated Reducer 合并语义（纯 stdlib 模拟框架合并） | 否 |
| `02_node.py` | 核心概念 2：Node | Node 是普通 Python 函数，简单分类不必走 LLM | 否 |
| `03_stategraph.py` | 核心概念 3：StateGraph | 把 Node 装进图容器 | 是 |
| `04_edge.py` | 核心概念 4：Edge | `add_edge` 确定性顺序 + `add_conditional_edges` 条件分支 | 是 |
| `05_compile.py` | 核心概念 5：Compile | 图 → 可执行 app，`invoke` 运行 | 是 |
| `conditional_routing_demo.py` | 条件路由 demo | 按订单金额路由到 vip / normal / small 三条流程 | 是 |
| `annotated_reducer_experiment.py` | Annotated Reducer 对照实验 | 有 reducer vs 没 reducer 两种写法对比（无 langgraph 时用 stdlib 模拟） | 可选 |
| `classify_process_output_graph.py` | 完整"分类-处理-输出"小图 | 5 个概念拼成的第一个可跑状态机 | 是 |
| `demo.py` | 章节统一入口 | 委托 `series_projects.chapter_runner` | — |

## 运行

```bash
python3 01_state.py
python3 04_edge.py
python3 classify_process_output_graph.py
```

## 核心认知

- 状态 = TypedDict 静态契约 + reducer 自动合并，不是拼接的 messages。
- 路由是代码确定性（Python `if/else` / 路由函数返回节点名），LLM 只在节点内决策。
- 节点是 Python 函数，含不含 LLM 看需要。
- 整个流程没有一个 while 循环——状态机自己跑，且可视化、可审计、可回放。
