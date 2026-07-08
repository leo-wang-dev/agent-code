"""18 章配套：5 个核心监控指标采集脚本。

对应文章第七节"运维要点 · 监控指标"，原样落地这张表：

| 指标 | 含义 | 告警阈值 |
|------|------|---------|
| extract_queue_depth   | 抽取队列堆积深度       | > 1000 |
| extract_failure_rate  | 抽取失败率            | > 5%   |
| extract_avg_latency   | 抽取平均耗时          | > 5s   |
| memory_per_user_cost  | 每用户月均 Memory 成本 | 自定    |
| recall_relevance_score| 召回相关性指标(A/B)    | < 0.7  |

MetricsCollector 采集这 5 个指标并按阈值判定告警。纯内存实现，无需 Prometheus；
线上把 snapshot() 的输出 push 到 Prometheus / StatsD 即可。

离线可运行：`python3 18_layered_memory/metrics.py`
"""

from __future__ import annotations

from dataclasses import dataclass, field


# 告警阈值（direction: '>' 表示超过告警，'<' 表示低于告警）
THRESHOLDS = {
    "extract_queue_depth":    (1000, ">"),
    "extract_failure_rate":   (0.05, ">"),
    "extract_avg_latency":    (5.0, ">"),
    "memory_per_user_cost":   (None, ">"),   # 自定，无默认阈值
    "recall_relevance_score": (0.7, "<"),
}


@dataclass
class MetricsCollector:
    """抽取/召回链路的 5 个核心指标采集器。"""

    queue_depth: int = 0
    _extract_total: int = 0
    _extract_failed: int = 0
    _latencies: list[float] = field(default_factory=list)
    _user_cost: dict[str, float] = field(default_factory=dict)
    _relevance_samples: list[float] = field(default_factory=list)

    # --- 采点接口（由抽取 worker / 检索器打点）---
    def set_queue_depth(self, depth: int) -> None:
        self.queue_depth = depth

    def record_extraction(self, latency_s: float, ok: bool, user_id: str, cost: float) -> None:
        self._extract_total += 1
        if not ok:
            self._extract_failed += 1
        self._latencies.append(latency_s)
        self._user_cost[user_id] = self._user_cost.get(user_id, 0.0) + cost

    def record_recall_relevance(self, score: float) -> None:
        self._relevance_samples.append(score)

    # --- 5 个指标 ---
    def extract_queue_depth(self) -> float:
        return float(self.queue_depth)

    def extract_failure_rate(self) -> float:
        return self._extract_failed / self._extract_total if self._extract_total else 0.0

    def extract_avg_latency(self) -> float:
        return sum(self._latencies) / len(self._latencies) if self._latencies else 0.0

    def memory_per_user_cost(self) -> float:
        if not self._user_cost:
            return 0.0
        return sum(self._user_cost.values()) / len(self._user_cost)

    def recall_relevance_score(self) -> float:
        return sum(self._relevance_samples) / len(self._relevance_samples) if self._relevance_samples else 1.0

    def snapshot(self) -> dict[str, float]:
        return {
            "extract_queue_depth": self.extract_queue_depth(),
            "extract_failure_rate": round(self.extract_failure_rate(), 4),
            "extract_avg_latency": round(self.extract_avg_latency(), 3),
            "memory_per_user_cost": round(self.memory_per_user_cost(), 4),
            "recall_relevance_score": round(self.recall_relevance_score(), 4),
        }

    def alerts(self) -> list[str]:
        firing = []
        snap = self.snapshot()
        for name, value in snap.items():
            threshold, direction = THRESHOLDS[name]
            if threshold is None:
                continue
            if (direction == ">" and value > threshold) or (direction == "<" and value < threshold):
                firing.append(f"{name}={value} {direction} {threshold}")
        return firing


def _demo() -> None:
    mc = MetricsCollector()

    # 模拟一批抽取打点：20 条，其中 2 条失败，个别延迟偏高
    import random

    random.seed(7)
    for i in range(20):
        ok = i not in (5, 13)                       # 2/20 失败 = 10% > 5%
        latency = random.uniform(0.4, 2.0) if ok else 6.5
        mc.record_extraction(latency, ok, user_id=f"u{i % 4}", cost=random.uniform(0.001, 0.01))
    mc.set_queue_depth(1240)                         # > 1000
    for s in [0.82, 0.61, 0.75, 0.58, 0.9]:          # 召回相关性样本，均值 < 0.7 边界
        mc.record_recall_relevance(s)

    print("指标快照（可直接 push 到 Prometheus）：")
    for name, value in mc.snapshot().items():
        print(f"  {name:24s} = {value}")

    print("\n触发告警：")
    alerts = mc.alerts()
    if not alerts:
        print("  （无）")
    for a in alerts:
        print(f"  ⚠️  {a}")


if __name__ == "__main__":
    _demo()
