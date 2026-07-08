"""18 章配套：失败重试 + 死信队列（DLQ）。

对应文章第五节细节 1"失败重试 + 死信队列"：

  抽取任务执行
    ├─ 成功 → 入库
    └─ 失败
        ├─ 第 1 次重试（30s 后，指数退避）
        ├─ 第 2 次重试（2 分钟后）
        ├─ 第 3 次重试（10 分钟后）
        └─ 仍失败 → 进死信队列 → 人工 review

离线用逻辑时钟驱动（不真的 sleep），确定性复现重试节奏与进 DLQ 的过程。

离线可运行：`python3 18_layered_memory/retry_dlq.py`
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable


# 指数退避节奏（秒）：30s / 2min / 10min，对齐文章
BACKOFF_SCHEDULE = [30, 120, 600]


@dataclass
class Job:
    id: str
    payload: str
    attempts: int = 0
    next_at: float = 0.0
    last_error: str = ""


@dataclass
class RetryQueue:
    """带指数退避重试 + 死信兜底的抽取任务队列。"""

    handler: Callable[[str], None]
    schedule: list[int] = field(default_factory=lambda: list(BACKOFF_SCHEDULE))
    _ready: list[Job] = field(default_factory=list)
    dead_letter: list[Job] = field(default_factory=list)
    done: list[Job] = field(default_factory=list)

    def submit(self, job: Job, now: float) -> None:
        job.next_at = now
        self._ready.append(job)

    def tick(self, now: float) -> None:
        """处理所有到点的任务：成功入 done，失败按退避重排或进 DLQ。"""
        due = [j for j in self._ready if j.next_at <= now]
        for job in due:
            self._ready.remove(job)
            job.attempts += 1
            try:
                self.handler(job.payload)
                self.done.append(job)
            except Exception as exc:
                job.last_error = str(exc)
                if job.attempts <= len(self.schedule):
                    delay = self.schedule[job.attempts - 1]
                    job.next_at = now + delay
                    self._ready.append(job)
                    print(f"  [{job.id}] 第 {job.attempts} 次失败（{exc}），{delay}s 后重试")
                else:
                    self.dead_letter.append(job)
                    print(f"  [{job.id}] 重试耗尽 → 进死信队列（人工 review）")

    def pending(self) -> int:
        return len(self._ready)


def _demo() -> None:
    processed: list[str] = []

    # flaky handler：payload=always_fail 永远炸；payload=flaky 前两次炸第三次成
    counters: dict[str, int] = {}

    def handler(payload: str) -> None:
        counters[payload] = counters.get(payload, 0) + 1
        if payload == "always_fail":
            raise RuntimeError("LLM 限流")
        if payload == "flaky" and counters[payload] < 3:
            raise ValueError("JSON 解析失败")
        processed.append(payload)

    q = RetryQueue(handler=handler)
    now = 0.0
    q.submit(Job("j1", "ok_fact"), now)
    q.submit(Job("j2", "flaky"), now)
    q.submit(Job("j3", "always_fail"), now)

    # 推进逻辑时钟：0 → 30 → 120 → 600 → 1200 覆盖所有退避点
    for now in [0, 30, 120, 600, 1200]:
        print(f"t={now}s tick：")
        q.tick(float(now))

    print(f"\n成功入库：{[j.payload for j in q.done]}")
    print(f"死信队列：{[j.id + ':' + j.last_error for j in q.dead_letter]}")
    print(f"仍在队列：{q.pending()}")


if __name__ == "__main__":
    _demo()
