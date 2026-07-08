"""模型组合 Pipeline 示例 —— 一个 Agent 流程里不同节点用不同模型。

对应文章第 44 篇 三、模型组合策略。

每个节点声明式配置用哪个模型（方便审计/调整），跑一遍统计总成本，
并与"全程用顶级模型"对比。

离线可运行：`python3 model_pipeline.py`
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _models import MINI, TOP, MockModel  # noqa: E402


@dataclass
class Node:
    name: str
    model: MockModel | None  # None = 纯逻辑节点（不调 LLM，如 RAG 检索）
    run: Callable[[dict], dict]


def _intent(state: dict) -> dict:
    return {**state, "intent": "query_order"}


def _rag(state: dict) -> dict:
    return {**state, "context": "订单在 30 天内可退货"}


def _answer(state: dict) -> dict:
    return {**state, "answer": "根据政策，您的订单符合退货条件。"}


def _guardrail(state: dict) -> dict:
    return {**state, "safe": True}


def _feedback(state: dict) -> dict:
    return {**state, "sentiment": "neutral"}


# 声明式：每个节点配"最便宜的能胜任的模型"（对齐文章 Pipeline 图）
PIPELINE = [
    Node("1.意图分类", MINI, _intent),
    Node("2.RAG检索", None, _rag),          # 不调 LLM
    Node("3.答案综合", TOP, _answer),        # 需要质量 → 顶级
    Node("4.输出Guardrails", MINI, _guardrail),
    Node("5.反馈分析", MINI, _feedback),
]


def run_pipeline(query: str, all_top: bool = False) -> dict:
    state = {"query": query}
    total_cost = 0.0
    trace = []
    for node in PIPELINE:
        model = TOP if (all_top and node.model is not None) else node.model
        if model is not None:
            resp = model.complete(query)
            total_cost += resp["cost_usd"]
            trace.append(f"{node.name}:{model.name}")
        else:
            trace.append(f"{node.name}:(no-llm)")
        state = node.run(state)
    return {"state": state, "total_cost_usd": total_cost, "trace": trace}


def _demo() -> None:
    q = "我要退货，订单号 12345"

    mixed = run_pipeline(q, all_top=False)
    baseline = run_pipeline(q, all_top=True)

    print("=== 模型组合 Pipeline ===")
    for step in mixed["trace"]:
        print(f"  {step}")
    print(f"\n组合方案成本 : ${mixed['total_cost_usd']:.8f}")
    print(f"全程顶级成本 : ${baseline['total_cost_usd']:.8f}")
    saved = 1 - mixed["total_cost_usd"] / baseline["total_cost_usd"]
    print(f"节省         : {saved:.0%}")


if __name__ == "__main__":
    _demo()
