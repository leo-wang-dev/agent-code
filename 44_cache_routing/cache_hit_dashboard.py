"""缓存命中率监控面板 —— 语义缓存 + 降级路由叠加后的成本节省报表。

对应文章第 44 篇 一、实际效果 + 五、缓存 + 降级路由的协同。

模拟一批带重复/相似的真实流量，跑「语义缓存 → 降级路由」两级，
统计命中率、各模型占比、总成本 vs 全程顶级基线的节省。

离线可运行：`python3 cache_hit_dashboard.py`
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _models import TOP  # noqa: E402
from routing_strategies import llm_route  # noqa: E402
from semantic_cache import SemanticCache  # noqa: E402

# 一组高频问题（会被大量重复问，制造缓存命中）
FAQ = [
    "什么是 RAG",
    "请解释一下 RAG",
    "如何退货",
    "退货流程是什么",
    "运费怎么算",
]
# 一组长尾/复杂问题（低重复，走降级路由）
LONGTAIL = [
    "对比这 10 个产品并深度分析",
    "帮我规划 30 天护肤方案",
    "研究视黄醇的最新使用方案",
]


def simulate(n: int = 1000, seed: int = 42) -> dict:
    random.seed(seed)
    cache = SemanticCache(threshold=0.85)

    total_cost = 0.0
    baseline_cost = 0.0
    model_counts: dict[str, int] = {}

    for _ in range(n):
        # 70% 高频，30% 长尾
        q = random.choice(FAQ) if random.random() < 0.7 else random.choice(LONGTAIL)

        baseline_cost += TOP.complete(q)["cost_usd"]

        cached = cache.get(q, tenant_id="t1")
        if cached is not None:
            model_counts["cache"] = model_counts.get("cache", 0) + 1
            continue

        model = llm_route(q)
        resp = model.complete(q)
        total_cost += resp["cost_usd"]
        model_counts[model.name] = model_counts.get(model.name, 0) + 1
        cache.set(q, resp["text"], tenant_id="t1")

    return {
        "n": n,
        "hit_rate": cache.hit_rate,
        "model_counts": model_counts,
        "total_cost": total_cost,
        "baseline_cost": baseline_cost,
        "saved_ratio": 1 - total_cost / baseline_cost if baseline_cost else 0.0,
    }


def _bar(value: int, total: int, width: int = 24) -> str:
    filled = int(value / total * width) if total else 0
    return "█" * filled + "░" * (width - filled)


def _demo() -> None:
    stats = simulate(1000)
    total = stats["n"]
    print("=" * 56)
    print(f"[缓存命中率监控面板]  样本 {total} 次请求")
    print("=" * 56)
    print(f"语义缓存命中率 : {stats['hit_rate']:.1%}")
    print("-" * 56)
    print("请求分流（缓存 / 各降级模型）:")
    for name, cnt in sorted(stats["model_counts"].items(), key=lambda kv: kv[1], reverse=True):
        print(f"  {name:<18} {_bar(cnt, total)} {cnt:>4} ({cnt / total:.0%})")
    print("-" * 56)
    print(f"实际成本   : ${stats['total_cost']:.6f}")
    print(f"全程顶级   : ${stats['baseline_cost']:.6f}")
    print(f"总节省     : {stats['saved_ratio']:.0%}  （缓存 + 降级路由叠加）")


if __name__ == "__main__":
    _demo()
