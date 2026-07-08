"""fan-out / fan-in 并行示例 —— Orchestrator-Worker 的并行内核单独演示。

一个节点连到多个下游 → 框架自动并行执行（fan-out）；
多个节点连到同一下游 → 框架等全部完成才继续（fan-in）。
整体延迟取决于最慢的 Worker，而不是三者之和。

用带时间戳的 trace 直观展示"三个 Worker 确实并行、汇集节点等它们全部完成"。

需要依赖：pip install langgraph
"""
from __future__ import annotations

import operator
import time
from typing import Annotated, TypedDict

try:
    from langgraph.graph import StateGraph, START, END
except ImportError:
    print("需要先安装依赖：pip install langgraph")
    print("（本示例演示 fan-out/fan-in 并行，缺少 langgraph 无法运行）")
    raise SystemExit(0)


class State(TypedDict, total=False):
    task: str
    trace: Annotated[list, operator.add]
    merged: str


def worker(name: str, cost: float):
    def _fn(state: State) -> dict:
        time.sleep(cost)  # 模拟耗时
        return {"trace": [f"{name} 完成(耗时 {cost}s)"]}
    return _fn


def split(state: State) -> dict:
    return {}


def merge(state: State) -> dict:
    return {"merged": f"汇集 {len(state['trace'])} 个 Worker 结果"}


def build_app():
    graph = StateGraph(State)
    graph.add_node("split", split)
    graph.add_node("w1", worker("w1", 0.1))
    graph.add_node("w2", worker("w2", 0.3))  # 最慢
    graph.add_node("w3", worker("w3", 0.2))
    graph.add_node("merge", merge)

    graph.add_edge(START, "split")
    for w in ("w1", "w2", "w3"):
        graph.add_edge("split", w)   # fan-out
        graph.add_edge(w, "merge")   # fan-in
    graph.add_edge("merge", END)
    return graph.compile()


def main() -> None:
    app = build_app()
    t0 = time.time()
    result = app.invoke({"task": "并行检索", "trace": []})
    elapsed = time.time() - t0
    for line in result["trace"]:
        print("  -", line)
    print(result["merged"])
    # 并行 → 总耗时≈最慢 Worker(0.3s)，而非三者之和(0.6s)
    print(f"总耗时 ≈ {elapsed:.2f}s（并行，取决于最慢 Worker 而非累加）")


if __name__ == "__main__":
    main()
