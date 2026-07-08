"""三层混合架构 demo —— 按场景分层：轻量 Framework / 深度 DeepAgents / Harness。

对应文章第 48 篇 九、混合架构 —— 真实工业级最优解 + 美容平台例子。

核心思想：用最贵的方案服务最有价值的场景，用最便宜的方案服务大众场景。
- 轻量层（Framework）：95% 用户日常问答，低成本；
- 深度咨询层（DeepAgents）：10% 高价值用户的长任务；
- Harness 层：不论档次，研究/深度分析类任务走这里。

离线可跑：`python3 hybrid_architecture.py`（跑一批混合流量，出分流 + 成本报表）。
"""

from __future__ import annotations

import random
from dataclasses import dataclass

# 每层单次请求的相对成本（对齐文章：轻量便宜、深度贵）
LAYER_COST = {"light": 1.0, "deep": 12.0, "harness": 20.0}


@dataclass
class Request:
    user_tier: str        # normal / vip
    task: str
    complexity: str       # simple / long / research


def route(req: Request) -> str:
    """路由到三层之一（对齐文章扩展决策树的思想）。"""
    # 研究/深度分析类：不论档次都走 Harness
    if req.complexity == "research":
        return "harness"
    # VIP + 长任务 → 深度咨询层
    if req.user_tier == "vip" and req.complexity == "long":
        return "deep"
    # 其余 → 轻量层
    return "light"


def simulate(n: int = 1000, seed: int = 7) -> dict:
    random.seed(seed)
    counts = {"light": 0, "deep": 0, "harness": 0}
    total_cost = 0.0
    all_top_cost = 0.0  # 假设全走 harness 的基线

    for _ in range(n):
        # 90% normal / 10% vip
        tier = "vip" if random.random() < 0.1 else "normal"
        r = random.random()
        complexity = "research" if r < 0.03 else ("long" if r < 0.15 else "simple")
        req = Request(tier, "task", complexity)

        layer = route(req)
        counts[layer] += 1
        total_cost += LAYER_COST[layer]
        all_top_cost += LAYER_COST["harness"]

    return {
        "n": n,
        "counts": counts,
        "total_cost": total_cost,
        "baseline_cost": all_top_cost,
        "saved_ratio": 1 - total_cost / all_top_cost if all_top_cost else 0.0,
    }


def _bar(v: int, total: int, width: int = 22) -> str:
    f = int(v / total * width) if total else 0
    return "█" * f + "░" * (width - f)


def _demo() -> None:
    stats = simulate(1000)
    total = stats["n"]
    print("=" * 52)
    print(f"[三层混合架构]  {total} 次混合流量")
    print("=" * 52)
    for layer in ("light", "deep", "harness"):
        c = stats["counts"][layer]
        print(f"  {layer:<8} {_bar(c, total)} {c:>4} ({c / total:.0%})")
    print("-" * 52)
    print(f"混合总成本 : {stats['total_cost']:.0f}")
    print(f"全走 Harness: {stats['baseline_cost']:.0f}")
    print(f"节省       : {stats['saved_ratio']:.0%}")
    print("\n结论：90%+ 流量在轻量层(低成本)，10% 高价值走深度层(高客单价)。")


if __name__ == "__main__":
    _demo()
