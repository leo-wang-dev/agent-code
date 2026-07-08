"""4 类监控指标采集脚本。

对应文章第六节"关键监控指标体系"：业务侧 / 性能侧 / 系统侧 / 质量侧。
每个指标带健康阈值，采集后自动判健康度并汇总告警项。

零依赖，可运行。生产把 `_mock_raw_events` 换成从 trace 后端
（LangSmith/Langfuse/Helicone）或 usage_logs 拉取的真实数据即可。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Metric:
    name: str
    value: float
    unit: str
    threshold: float
    higher_is_better: bool
    category: str

    @property
    def healthy(self) -> bool:
        return self.value >= self.threshold if self.higher_is_better else self.value <= self.threshold


# ---------------------------------------------------------------------------
# mock 原始事件（生产：从 trace 后端聚合）
# ---------------------------------------------------------------------------
def _mock_raw_events() -> dict:
    return {
        "sessions": 1000,
        "resolved": 918,             # 任务完成
        "first_turn_resolved": 726,  # 首轮解决
        "escalated": 120,            # 转人工
        "thumbs_up": 820,
        "thumbs_total": 1000,
        "repeated": 85,              # 重复提问
        "ttft_ms": 780,
        "tps": 34.0,
        "p95_ms": 4600,
        "cache_hits": 360,
        "llm_calls": 5200,
        "llm_errors": 31,
        "tool_calls": 2100,
        "tool_errors": 55,
        "fallback": 210,
        "ratelimit": 18,
        "rag_relevance": 0.82,       # LLM-judge 抽样
        "hallucination": 0.06,
        "intent_accuracy": 0.91,
        "drift_score": 0.08,
    }


def collect_metrics() -> list[Metric]:
    e = _mock_raw_events()
    n = e["sessions"]
    return [
        # 业务侧
        Metric("任务完成率", e["resolved"] / n, "", 0.90, True, "业务"),
        Metric("首轮解决率", e["first_turn_resolved"] / n, "", 0.70, True, "业务"),
        Metric("人工升级率", e["escalated"] / n, "", 0.15, False, "业务"),
        Metric("用户满意度", e["thumbs_up"] / e["thumbs_total"], "", 0.80, True, "业务"),
        Metric("用户重复提问率", e["repeated"] / n, "", 0.10, False, "业务"),
        # 性能侧
        Metric("TTFT", e["ttft_ms"] / 1000, "s", 1.0, False, "性能"),
        Metric("TPS", e["tps"], "tok/s", 30.0, True, "性能"),
        Metric("P95 响应", e["p95_ms"] / 1000, "s", 5.0, False, "性能"),
        Metric("缓存命中率", e["cache_hits"] / e["llm_calls"], "", 0.30, True, "性能"),
        # 系统侧
        Metric("LLM 调用错误率", e["llm_errors"] / e["llm_calls"], "", 0.01, False, "系统"),
        Metric("Tool 调用错误率", e["tool_errors"] / e["tool_calls"], "", 0.02, False, "系统"),
        Metric("Fallback 触发率", e["fallback"] / e["llm_calls"], "", 0.05, False, "系统"),
        Metric("限流触发率", e["ratelimit"] / n, "", 0.01, False, "系统"),
        # 质量侧（最容易被忽略）
        Metric("RAG 召回质量", e["rag_relevance"], "", 0.80, True, "质量"),
        Metric("答案幻觉率", e["hallucination"], "", 0.10, False, "质量"),
        Metric("意图分类准确率", e["intent_accuracy"], "", 0.85, True, "质量"),
        Metric("行为漂移", e["drift_score"], "", 0.15, False, "质量"),
    ]


def main() -> None:
    print("=" * 60)
    print("4 类监控指标采集")
    print("=" * 60)
    metrics = collect_metrics()
    unhealthy: list[Metric] = []
    last_cat = None
    for m in metrics:
        if m.category != last_cat:
            print(f"\n[{m.category}侧]")
            last_cat = m.category
        flag = "OK " if m.healthy else "警告"
        op = "≥" if m.higher_is_better else "≤"
        val = f"{m.value:.2%}" if not m.unit else f"{m.value:.2f}{m.unit}"
        thr = f"{m.threshold:.0%}" if not m.unit else f"{m.threshold}{m.unit}"
        print(f"  [{flag}] {m.name:<16} {val:<10} (阈值 {op}{thr})")
        if not m.healthy:
            unhealthy.append(m)

    print("\n" + "=" * 60)
    if unhealthy:
        print(f"需关注指标（{len(unhealthy)}）：" + "、".join(m.name for m in unhealthy))
    else:
        print("全部指标健康 ✅")


if __name__ == "__main__":
    main()
