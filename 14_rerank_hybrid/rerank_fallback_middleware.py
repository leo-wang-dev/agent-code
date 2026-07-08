"""重排降级容错中间件（离线可运行）。

一个能上线的 RAG 必须对每个故障点都有降级路径。重排层的契约：
  - 阶段 1 召回**不允许失败**（失败直接 raise，因为没有它就没有任何候选）；
  - 阶段 2 重排**允许失败**（超时/异常/限流时，降级到 Bi-Encoder 召回原序）。

对照原文 `robust_retrieve`：这里用 `concurrent.futures` 实现 timeout，用一个可注入故障的
假 Reranker 演示三种情况：正常、超时降级、异常降级。

    python3 14_rerank_hybrid/rerank_fallback_middleware.py
"""

from __future__ import annotations

import sys
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent_examples.rag import (  # noqa: E402
    InMemoryVectorStore,
    build_chunks,
    sample_corpus,
)
from agent_examples.text import ScoredText  # noqa: E402

from reranker_adapters import BgeReranker, Reranker, _offline_score  # noqa: E402


class RerankerException(Exception):
    pass


class FlakyReranker(Reranker):
    """可注入故障的重排器，用于演示降级路径。"""

    name = "flaky"

    def __init__(self, mode: str = "ok", delay: float = 0.0):
        self.mode = mode  # ok | slow | error
        self.delay = delay

    def rerank(self, query, candidates, top_n=3):
        # 直接实现，绕过基类的厂商级兜底——让故障真正传播到中间件，由中间件降级
        if self.mode == "error":
            raise RerankerException("模拟重排服务 500")
        if self.mode == "slow":
            time.sleep(self.delay)
        scores = _offline_score(query, [c.text for c in candidates])
        paired = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
        return [ScoredText(c.text, s, c.metadata) for c, s in paired[:top_n]]

    def _score_impl(self, query, passages):
        return _offline_score(query, passages)


# 简单的可观测计数器（真实系统里这是 metrics.increment）
METRICS = {"rerank_success": 0, "rerank_fallback": 0}


def robust_retrieve(store, reranker, query, k_recall=8, k_final=3, timeout=1.0):
    # 阶段 1：召回（不允许失败）
    candidates = store.search(query, k=k_recall)

    # 阶段 2：重排（允许失败，失败降级到向量原序）
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(reranker.rerank, query, candidates, k_final)
            result = future.result(timeout=timeout)
        METRICS["rerank_success"] += 1
        top = result[0].score if result else 0.0
        print(f"    [ok] rerank succeeded, top score={top:.3f}")
        return result
    except (FutureTimeout, RerankerException, Exception) as exc:  # noqa: BLE001
        METRICS["rerank_fallback"] += 1
        print(f"    [warn] rerank failed → 降级到向量原序：{type(exc).__name__}: {exc}")
        return candidates[:k_final]


def main() -> None:
    store = InMemoryVectorStore(build_chunks(sample_corpus(), "structure"))
    query = "我今年能休几天假"

    print("=" * 72)
    print("重排降级容错中间件：三种情况")
    print("=" * 72)

    print("\n[1] 正常：Cross-Encoder 重排生效")
    r1 = robust_retrieve(store, BgeReranker(), query, timeout=2.0)
    print(f"    结果 top1：{r1[0].text[:36] if r1 else '(空)'}")

    print("\n[2] 超时：重排 2s > 阈值 1s，降级到召回原序")
    r2 = robust_retrieve(store, FlakyReranker("slow", delay=2.0), query, timeout=1.0)
    print(f"    结果 top1：{r2[0].text[:36] if r2 else '(空)'}")

    print("\n[3] 异常：重排抛错，降级到召回原序")
    r3 = robust_retrieve(store, FlakyReranker("error"), query, timeout=1.0)
    print(f"    结果 top1：{r3[0].text[:36] if r3 else '(空)'}")

    print("\n" + "=" * 72)
    print(f"可观测指标：{METRICS}")
    print("=" * 72)
    print("关键：无论重排成功还是降级，用户永远拿到结果——不会因为重排挂了整条链路崩。")


if __name__ == "__main__":
    main()
