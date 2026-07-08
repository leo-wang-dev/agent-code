"""延迟监控仪表盘 —— 每次调用记录分阶段延迟，聚合 P50/P95/P99 + 阶段构成。

对应文章第 45 篇 六、监控和持续优化 + 一、Agent 延迟的真实构成。

真实可跑：`python3 latency_dashboard.py`（生成一批带抖动的样本并出报表）。
"""

from __future__ import annotations

import random

STAGES = ("gateway", "memory", "rag", "llm", "tool", "guardrails")


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = (len(s) - 1) * p
    lo = int(k)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


class LatencyCollector:
    def __init__(self) -> None:
        self.records: list[dict] = []

    def record(self, stages: dict[str, float], ttft: float) -> None:
        rec = dict(stages)
        rec["ttft"] = ttft
        rec["end_to_end"] = sum(stages.values())
        self.records.append(rec)

    def summary(self) -> dict:
        out = {}
        for key in ("ttft", "end_to_end", *STAGES):
            vals = [r[key] for r in self.records]
            out[key] = {
                "p50": percentile(vals, 0.50),
                "p95": percentile(vals, 0.95),
                "p99": percentile(vals, 0.99),
                "mean": sum(vals) / len(vals) if vals else 0.0,
            }
        return out

    def stage_composition(self) -> dict[str, float]:
        totals = {s: sum(r[s] for r in self.records) for s in STAGES}
        grand = sum(totals.values()) or 1.0
        return {s: v / grand for s, v in totals.items()}


def _simulate(collector: LatencyCollector, n: int = 500, seed: int = 7) -> None:
    random.seed(seed)
    for _ in range(n):
        stages = {
            "gateway": random.uniform(20, 100),
            "memory": random.uniform(20, 100),
            "rag": random.uniform(50, 300),
            "llm": random.uniform(300, 1500),
            "tool": random.uniform(0, 800),
            "guardrails": random.uniform(100, 500),
        }
        ttft = random.uniform(300, 1500)
        collector.record(stages, ttft)


def _bar(ratio: float, width: int = 20) -> str:
    return "█" * int(ratio * width) + "░" * (width - int(ratio * width))


def _demo() -> None:
    collector = LatencyCollector()
    _simulate(collector)

    summ = collector.summary()
    print("=" * 56)
    print(f"[延迟监控仪表盘]  样本 {len(collector.records)} 次调用 (单位 ms)")
    print("=" * 56)
    print(f"{'指标':<14}{'P50':>8}{'P95':>8}{'P99':>8}")
    for key in ("ttft", "end_to_end", "llm", "rag", "tool", "guardrails"):
        s = summ[key]
        print(f"{key:<14}{s['p50']:>8.0f}{s['p95']:>8.0f}{s['p99']:>8.0f}")

    print("-" * 56)
    print("各阶段延迟构成（占端到端总耗时）:")
    comp = collector.stage_composition()
    for stage, ratio in sorted(comp.items(), key=lambda kv: kv[1], reverse=True):
        print(f"  {stage:<12} {_bar(ratio)} {ratio:.0%}")
    print("-" * 56)
    print("洞察：LLM 推理通常只占 40-60%，其余全是可优化的工程开销（文章结论）。")


if __name__ == "__main__":
    _demo()
