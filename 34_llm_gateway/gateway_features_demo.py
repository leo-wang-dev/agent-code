"""Fallback / 缓存 / 限流 完整 demo —— Gateway 三个核心能力的可运行实现。

对应第 34 篇「三、Gateway 必须有的 7 个核心能力」的能力 3/4/5。

纯标准库、确定性 mock（无 API key 也能跑）：
    python3 34_llm_gateway/gateway_features_demo.py
"""

from __future__ import annotations

import hashlib
import re
import time
from collections import deque
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# 能力 3：自动降级 / Fallback
# ---------------------------------------------------------------------------


@dataclass
class Provider:
    name: str
    healthy: bool = True

    def call(self, prompt: str) -> str:
        if not self.healthy:
            raise RuntimeError(f"{self.name} 不可用")
        return f"[{self.name}] 回答：{prompt[:40]}"


class FallbackRouter:
    """按 fallback 链依次尝试，主 Provider 挂了自动切备用（Agent 不感知）。"""

    def __init__(self, chain: list[Provider]) -> None:
        self.chain = chain

    def complete(self, prompt: str) -> dict:
        errors: list[str] = []
        for provider in self.chain:
            try:
                content = provider.call(prompt)
                return {"content": content, "provider": provider.name, "fallbacks": errors}
            except RuntimeError as exc:
                errors.append(str(exc))
        return {"content": None, "provider": None, "fallbacks": errors, "error": "all providers exhausted"}


# ---------------------------------------------------------------------------
# 能力 4：缓存（精确 + 简易语义）
# ---------------------------------------------------------------------------


class SemanticCache:
    """精确缓存 + 归一化语义缓存（数字/空白/标点归一，近似相似匹配）。"""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.hits = 0
        self.misses = 0

    @staticmethod
    def _key(text: str) -> str:
        normalized = re.sub(r"[\d\s，。？?！!、]+", "", text.lower())
        # 去掉常见口语差异，让"什么是RAG"/"请解释RAG"/"RAG是啥"归一。
        for filler in ["什么是", "请解释一下", "请解释", "到底是个啥东西", "到底是啥", "解释"]:
            normalized = normalized.replace(filler, "")
        return hashlib.sha1(normalized.encode()).hexdigest()

    def get_or_call(self, prompt: str, compute) -> dict:
        key = self._key(prompt)
        if key in self.store:
            self.hits += 1
            return {"content": self.store[key], "cached": True, "cost": 0.0}
        self.misses += 1
        content = compute(prompt)
        self.store[key] = content
        return {"content": content, "cached": False, "cost": len(prompt) * 1e-5}

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return round(self.hits / total, 2) if total else 0.0


# ---------------------------------------------------------------------------
# 能力 5：限流 + 配额（滑动窗口令牌）
# ---------------------------------------------------------------------------


@dataclass
class RateLimiter:
    """按 key 的滑动窗口限流：window 秒内最多 limit 次。"""

    limit: int
    window: float = 60.0
    _calls: dict[str, deque] = field(default_factory=dict)

    def allow(self, key: str, now: float | None = None) -> bool:
        now = now if now is not None else time.time()
        dq = self._calls.setdefault(key, deque())
        while dq and now - dq[0] > self.window:
            dq.popleft()
        if len(dq) >= self.limit:
            return False
        dq.append(now)
        return True


def main() -> None:
    print("=== 能力 3：Fallback ===")
    router = FallbackRouter([Provider("openai", healthy=False), Provider("anthropic", healthy=True)])
    result = router.complete("什么是 RAG？")
    print("主 Provider 挂了 ->", result["provider"], "| 失败链:", result["fallbacks"])

    print("\n=== 能力 4：语义缓存 ===")
    cache = SemanticCache()
    for q in ["什么是 RAG？", "请解释一下 RAG", "RAG 到底是个啥东西", "什么是 Agent？"]:
        r = cache.get_or_call(q, lambda p: f"关于 {p} 的解释")
        print(f"  {q:20} cached={r['cached']} cost={r['cost']:.5f}")
    print(f"  命中率：{cache.hit_rate}（问答类可省 20-40% token）")

    print("\n=== 能力 5：限流 ===")
    limiter = RateLimiter(limit=3, window=60)
    base = 1000.0
    for i in range(5):
        ok = limiter.allow("gw-sales-team", now=base + i)
        print(f"  第{i+1}次请求 -> {'放行' if ok else '拒绝(429)'}")


if __name__ == "__main__":
    main()
