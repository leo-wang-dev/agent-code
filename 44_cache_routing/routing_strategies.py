"""三种降级路由策略 —— 规则路由 / LLM 判别路由 / 级联路由（入口）。

对应文章第 44 篇 二、模型降级路由 —— 三种路由策略。

级联路由的完整实现见 `cascade_router.py`，本文件提供统一对比入口。

离线可运行：`python3 routing_strategies.py`
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _models import MINI, TINY, TOP, MockModel  # noqa: E402
from cascade_router import cascade_route  # noqa: E402


def rule_route(query: str, agent_type: str = "chat") -> MockModel:
    """策略1：规则路由——基于明确规则决定，可控可解释。"""
    if agent_type == "intent_classifier":
        return MINI
    if "写一份" in query or "创作" in query or "方案" in query:
        return TOP
    if len(query) < 20:
        return MINI
    return TOP


def llm_route(query: str) -> MockModel:
    """策略2：LLM 判别路由——用极便宜的小模型先判复杂度。

    这里用启发式模拟"小模型判别"的输出（simple/medium/complex）。
    生产替换：complexity = tiny_model.complete("判断复杂度: ...").strip()
    """
    text = query.lower()
    if any(k in query for k in ["对比", "分析", "规划", "研究", "推理", "为什么"]):
        complexity = "complex"
    elif len(query) > 30:
        complexity = "medium"
    else:
        complexity = "simple"
    return {"simple": TINY, "medium": MINI, "complex": TOP}[complexity]


def _demo() -> None:
    queries = [
        "什么是 RAG",
        "帮我写一份 30 天护肤方案",
        "对比这 10 个产品并给出推荐",
        "订单到哪了",
    ]

    print("=== 策略1 规则路由 ===")
    for q in queries:
        print(f"  {q!r:<30} → {rule_route(q).name}")

    print("\n=== 策略2 LLM 判别路由 ===")
    for q in queries:
        print(f"  {q!r:<30} → {llm_route(q).name}")

    print("\n=== 策略3 级联路由（详见 cascade_router.py）===")
    for q in queries[:2]:
        result = cascade_route(q)
        chain = " → ".join(result["attempts"])
        print(f"  {q!r:<30} 最终 {result['final_model']}  链路[{chain}]")


if __name__ == "__main__":
    _demo()
