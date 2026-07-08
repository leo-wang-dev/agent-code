"""17 章配套：Mem0 与手搓 Memory 的性能对照基准。

对应文章第二节"也要知道的代价" + 第七节④"大规模性能优化不够"。

对照两条写入路径在同一批对话上的开销：
- 手搓 INSERT：抽取后直接入库，每条事实 O(1)，不做去重/合并/否定检测；
- Mem0-like Operation Engine：每条新事实要先向量检索召回相关旧事实，再做
  ADD/UPDATE/DELETE/NOOP 决策（文章："每次新事实进库都多一次决策开销"）。

基准用离线确定性代码测量：
- 写入耗时（wall clock）；
- 每条事实的"决策调用次数"（线上即 LLM 调用次数，成本主因）；
- 最终库中事实数（体现 Operation Engine 的去重/合并收益）。

结论对齐文章：Operation Engine 拿"每条多一次决策"的成本，换来去重、版本化、
否定检测——异步执行时这笔开销不打到用户延迟上，但同步执行会拖慢回复。

离线可运行：`python3 17_mem0/perf_benchmark.py`
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from operation_engine import OperationEngine  # noqa: E402


def _make_corpus(rounds: int) -> list[tuple[str, str]]:
    """生成含大量重复 + 少量变更的对话事实流（模拟真实用户）。"""
    corpus: list[tuple[str, str]] = []
    cities = ["Shanghai", "Shanghai", "Shanghai", "Shenzhen"]  # 3 次重复 + 1 次变更
    for i in range(rounds):
        city = cities[i % len(cities)]
        corpus.append((f"user lives in {city}", "location"))
    return corpus


class NaiveInsertStore:
    """手搓做法：抽取到就 INSERT，不去重、不合并、不检测否定。"""

    def __init__(self) -> None:
        self.rows: list[str] = []
        self.decision_calls = 0  # 恒为 0：不做任何决策

    def add(self, text: str, slot: str) -> None:
        self.rows.append(text)


def bench(rounds: int) -> None:
    corpus = _make_corpus(rounds)

    # --- 手搓 INSERT ---
    naive = NaiveInsertStore()
    t0 = time.perf_counter()
    for text, slot in corpus:
        naive.add(text, slot)
    naive_ms = (time.perf_counter() - t0) * 1000

    # --- Mem0-like Operation Engine ---
    engine = OperationEngine()
    t0 = time.perf_counter()
    for i, (text, slot) in enumerate(corpus):
        engine.apply(f"f{i}", text, slot)
    engine_ms = (time.perf_counter() - t0) * 1000
    decision_calls = sum(engine.op_counter.values())

    print(f"\n--- 规模：{rounds} 条对话事实 ---")
    print(f"手搓 INSERT     : {naive_ms:7.2f} ms | 决策调用 {naive.decision_calls:4d} | 库中行数 {len(naive.rows)}（含重复）")
    print(f"Operation Engine: {engine_ms:7.2f} ms | 决策调用 {decision_calls:4d} | 活跃事实 {len(engine.active_facts())}（去重后）")
    print(f"操作分布：{engine.op_counter}")
    ratio = engine_ms / naive_ms if naive_ms else float('inf')
    print(f"写入开销比：Operation Engine ≈ 手搓 {ratio:.1f}x（每条多一次决策；线上即多一次 LLM 调用）")


def _demo() -> None:
    print("Mem0(Operation Engine) vs 手搓(INSERT) 性能对照基准")
    for rounds in (100, 1000, 5000):
        bench(rounds)
    print("\n要点：")
    print("  - 手搓 INSERT 快但库里堆重复；Operation Engine 慢但自动去重/合并/否定检测。")
    print("  - 决策开销的真实代价在线上是『每条事实多一次 LLM 调用』——必须异步执行。")
    print("  - 百万级 fact + 同步决策路径会显著拖慢响应（文章第七节④），需异步 + 分片。")


if __name__ == "__main__":
    _demo()
