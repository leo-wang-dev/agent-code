"""级联式路由 —— 先用便宜模型试，质量不达标再升级。

对应文章第 44 篇 二、策略3 级联式路由（推荐）。

自动找到"最便宜的能解决问题"的模型；失败时累计成本，供 ROI 判断。
质量评估用离线确定性打分（生产替换为小模型/规则/评测集打分）。

离线可运行：`python3 cascade_router.py`
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _models import MID, MINI, TOP, MockModel  # noqa: E402

# 级联梯队：从便宜到顶级
CASCADE = [MINI, MID, TOP]


def quality_ok(response: dict, query: str, min_score: float = 0.6) -> bool:
    """离线质量评估：模型越强、query 越简单，分越高。

    生产替换：
        score = judge_model.score(query, response) 或 用规则/评测集
    """
    strength = {"gpt-4o-mini": 0.4, "claude-3-5-haiku": 0.7, "gpt-4o": 0.95}
    base = strength.get(response["model"], 0.5)
    # 复杂 query 对弱模型更不利
    hard = any(k in query for k in ["对比", "分析", "规划", "研究", "推理"])
    score = base - (0.3 if hard else 0.0)
    return score >= min_score


def cascade_route(query: str, min_score: float = 0.6) -> dict:
    attempts: list[str] = []
    total_cost = 0.0
    for model in CASCADE:
        resp = model.complete(query)
        attempts.append(model.name)
        total_cost += resp["cost_usd"]
        if quality_ok(resp, query, min_score):
            return {
                "final_model": model.name,
                "attempts": attempts,
                "response": resp["text"],
                "total_cost_usd": total_cost,
                "escalated": len(attempts) > 1,
            }
    # 全部尝试过，返回最强模型的结果
    return {
        "final_model": CASCADE[-1].name,
        "attempts": attempts,
        "response": resp["text"],
        "total_cost_usd": total_cost,
        "escalated": True,
    }


def _demo() -> None:
    print("=== 级联路由：便宜→顶级，够用即停 ===\n")
    for q in ["什么是 RAG", "订单到哪了", "对比这 10 个产品并深度分析推荐"]:
        r = cascade_route(q)
        chain = " → ".join(r["attempts"])
        print(f"query   : {q!r}")
        print(f"  链路  : {chain}")
        print(f"  最终  : {r['final_model']}  (升级={r['escalated']})")
        print(f"  累计成本: ${r['total_cost_usd']:.8f}\n")


if __name__ == "__main__":
    _demo()
