"""语义缓存完整实现 —— Embedding 相似度命中 + 租户隔离 + TTL + 关键词绕过。

对应文章第 44 篇 一、语义缓存。

覆盖文章的三个隐藏陷阱：
- 陷阱1 跨用户隐私：按 (tenant_id) 分区，只在同租户内匹配；
- 陷阱2 时效性：含"今天/现在/最新"等词的 query 跳过缓存 + TTL 过期淘汰；
- 陷阱3 错配：阈值可调 + 记录 miss/hit 供监控。

离线可运行：`python3 semantic_cache.py`
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _models import cosine, local_embed  # noqa: E402

# 含这些词的 query 属于时效性/状态相关，跳过缓存（文章陷阱2 对策）
_BYPASS_KEYWORDS = ("今天", "现在", "最新", "此刻", "刚刚", "实时", "股价", "天气")


@dataclass
class CacheEntry:
    query: str
    embedding: list[float]
    response: str
    created_at: float


@dataclass
class SemanticCache:
    threshold: float = 0.92
    ttl: float = 86400.0
    _store: dict[str, list[CacheEntry]] = field(default_factory=dict)
    hits: int = 0
    misses: int = 0
    bypassed: int = 0

    def _should_bypass(self, query: str) -> bool:
        return any(k in query for k in _BYPASS_KEYWORDS)

    def get(self, query: str, tenant_id: str = "default") -> str | None:
        if self._should_bypass(query):
            self.bypassed += 1
            return None

        q_emb = local_embed(query)
        now = time.time()
        entries = self._store.get(tenant_id, [])
        # 淘汰过期项
        entries = [e for e in entries if now - e.created_at < self.ttl]
        self._store[tenant_id] = entries

        best: CacheEntry | None = None
        best_sim = 0.0
        for e in entries:
            sim = cosine(q_emb, e.embedding)
            if sim > best_sim:
                best_sim, best = sim, e

        if best is not None and best_sim >= self.threshold:
            self.hits += 1
            return best.response

        self.misses += 1
        return None

    def set(self, query: str, response: str, tenant_id: str = "default") -> None:
        if self._should_bypass(query):
            return
        entry = CacheEntry(query, local_embed(query), response, time.time())
        self._store.setdefault(tenant_id, []).append(entry)

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total else 0.0


def _demo() -> None:
    cache = SemanticCache(threshold=0.85)

    # 用户 A 首次问 → miss → 写入
    variants = ["什么是 RAG？", "请解释一下 RAG", "RAG 是个啥东西", "RAG 的概念是什么意思"]
    print("=== 同一租户内，4 种问法 ===")
    for i, q in enumerate(variants):
        hit = cache.get(q, tenant_id="t1")
        if hit is None:
            resp = f"RAG 是检索增强生成（第 {i} 次真实计算）"
            cache.set(q, resp, tenant_id="t1")
            print(f"  MISS  {q!r} → 调用 LLM")
        else:
            print(f"  HIT   {q!r} → 命中缓存: {hit!r}")

    print(f"\n命中率: {cache.hit_rate:.0%}  (hits={cache.hits}, misses={cache.misses})")

    # 陷阱1：跨租户隔离——t2 问同样的问题不会命中 t1 的缓存
    print("\n=== 跨租户隔离 ===")
    hit = cache.get("什么是 RAG？", tenant_id="t2")
    print(f"  t2 问同样问题 → {'命中(错!)' if hit else 'MISS（正确，隔离生效）'}")

    # 陷阱2：时效性 query 跳过缓存
    print("\n=== 时效性绕过 ===")
    cache.get("今天上海天气怎么样", tenant_id="t1")
    print(f"  含'今天'的 query 被绕过, bypassed={cache.bypassed}")


if __name__ == "__main__":
    _demo()
