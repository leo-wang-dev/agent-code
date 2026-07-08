"""18 章配套：抽取批量化的 debounce 机制。

对应文章第五节细节 2"抽取批量化"：用户连发 5 条消息，每条都触发抽取 = 5 次 LLM 调用。
优化：用户停下 window 秒后才触发抽取，把最近 N 轮对话合并成一个抽取任务。

文章用 Redis SETEX 做 debounce；本文件提供不依赖 Redis 的等价实现（可注入时钟便于测试），
同时保留 redis 路径（有 REDIS_URL + redis 包时启用）。

离线可运行：`python3 18_layered_memory/debounce.py`
"""

from __future__ import annotations

import os
import time
from collections import defaultdict
from typing import Callable


class Debouncer:
    """按 key 的时间窗口去抖：window 秒内的多次触发合并成一次。

    accumulate() 累积对话；每次刷新截止时间；到期后 flush() 一次性交给回调。
    离线用逻辑时钟（now 参数）驱动，避免真的 sleep 30 秒。
    """

    def __init__(self, window: float = 30.0, on_flush: Callable[[str, list[str]], None] | None = None) -> None:
        self.window = window
        self.on_flush = on_flush or (lambda key, msgs: None)
        self._buffers: dict[str, list[str]] = defaultdict(list)
        self._deadline: dict[str, float] = {}
        self._redis = self._maybe_redis()

    @staticmethod
    def _maybe_redis():
        url = os.environ.get("REDIS_URL")
        if not url:
            return None
        try:
            import redis

            client = redis.Redis.from_url(url)
            client.ping()
            return client
        except Exception as exc:
            print(f"[debounce] Redis 不可用（{exc}），用内存去抖。安装：pip install redis")
            return None

    def accumulate(self, key: str, message: str, now: float | None = None) -> None:
        """收到一条消息：累积并把截止时间推后 window 秒（重置去抖窗口）。"""
        now = time.time() if now is None else now
        self._buffers[key].append(message)
        self._deadline[key] = now + self.window
        if self._redis is not None:
            self._redis.setex(f"extract_pending:{key}", int(self.window), "pending")

    def tick(self, now: float | None = None) -> int:
        """时钟推进：把所有已到期的 key flush 出去。返回 flush 的 key 数。"""
        now = time.time() if now is None else now
        flushed = 0
        for key in list(self._deadline.keys()):
            if now >= self._deadline[key]:
                messages = self._buffers.pop(key, [])
                self._deadline.pop(key, None)
                if self._redis is not None:
                    self._redis.delete(f"extract_pending:{key}")
                if messages:
                    self.on_flush(key, messages)
                    flushed += 1
        return flushed


def _demo() -> None:
    triggered: list[tuple[str, list[str]]] = []
    deb = Debouncer(window=30.0, on_flush=lambda key, msgs: triggered.append((key, msgs)))

    key = "u1:conv1"
    t = 1000.0
    # 用户快速连发 5 条（每条间隔 5s < 30s 窗口）——不应各触发一次
    for i in range(5):
        deb.accumulate(key, f"消息{i+1}", now=t)
        fired = deb.tick(now=t)
        print(f"  t={t:.0f} 收到消息{i+1}，本 tick flush={fired}")
        t += 5

    # 用户停下，时钟推进到窗口之外
    t += 30
    fired = deb.tick(now=t)
    print(f"  t={t:.0f} 用户停顿 30s+，flush={fired}")

    print(f"\n5 条消息合并成 {len(triggered)} 次抽取任务：")
    for key, msgs in triggered:
        print(f"  {key}: {msgs}")
    saved = (5 - len(triggered)) / 5 * 100
    print(f"节省 LLM 抽取调用 ≈ {saved:.0f}%（文章：debounce 可省 60-80%）")


if __name__ == "__main__":
    _demo()
