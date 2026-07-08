"""16 章配套：异步任务队列接入（抽取的 fire-and-forget 通道）。

对应文章第三节①"一定要异步"：主流程立即返回回答，抽取丢队列异步处理。

- 有 redis 依赖 + REDIS_URL 时，用 Redis List 作队列（线上形态）；
- 缺依赖时，用内置的内存队列 + 后台线程做等价实现（离线默认）。

两条路径对上层暴露同一个接口：enqueue_extraction() / run_worker()。

离线可运行：`python3 16_memory_pipeline/async_queue.py`
"""

from __future__ import annotations

import json
import os
import queue
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from extraction_prompt import extract_facts  # noqa: E402
from memory_system import MemoryStore  # noqa: E402


class InMemoryQueue:
    """Redis List 的离线等价：线程安全的 FIFO。"""

    def __init__(self) -> None:
        self._q: "queue.Queue[str]" = queue.Queue()

    def push(self, payload: str) -> None:
        self._q.put(payload)

    def pop(self, timeout: float = 0.5) -> str | None:
        try:
            return self._q.get(timeout=timeout)
        except queue.Empty:
            return None

    def empty(self) -> bool:
        return self._q.empty()


def _get_redis():
    """尝试连 Redis；缺依赖或连不上返回 None，调用方自动降级。"""
    url = os.environ.get("REDIS_URL")
    if not url:
        return None
    try:
        import redis  # noqa: import 不发网络，仅在实例化/命令时连接

        client = redis.Redis.from_url(url)
        client.ping()
        return client
    except Exception as exc:
        print(f"[queue] Redis 不可用（{exc}），降级内存队列。安装：pip install redis")
        return None


EXTRACT_QUEUE_KEY = "memory:extract:queue"


class ExtractionDispatcher:
    """把抽取任务 fire-and-forget 推入队列，worker 异步消费入库。"""

    def __init__(self, store: MemoryStore) -> None:
        self.store = store
        self._redis = _get_redis()
        self._mem_queue = InMemoryQueue() if self._redis is None else None
        self.backend = "redis" if self._redis else "in-memory"

    def enqueue_extraction(self, user_id: str, utterance: str, conversation_id: str) -> None:
        payload = json.dumps(
            {"user_id": user_id, "utterance": utterance, "conversation_id": conversation_id},
            ensure_ascii=False,
        )
        if self._redis is not None:
            self._redis.rpush(EXTRACT_QUEUE_KEY, payload)
        else:
            self._mem_queue.push(payload)

    def _process(self, payload: str) -> int:
        job = json.loads(payload)
        facts = extract_facts(job["user_id"], job["utterance"], job["conversation_id"])
        for fact in facts:
            operation = self.store.upsert(fact)
            print(f"[worker] {operation:6s} {fact.key}={fact.value}")
        return len(facts)

    def drain(self, max_jobs: int = 100) -> int:
        """把当前队列里的任务全部消费掉（demo / 测试用同步消费）。"""
        processed = 0
        while processed < max_jobs:
            if self._redis is not None:
                payload = self._redis.lpop(EXTRACT_QUEUE_KEY)
                if payload is None:
                    break
                payload = payload.decode("utf-8") if isinstance(payload, bytes) else payload
            else:
                payload = self._mem_queue.pop(timeout=0.1)
                if payload is None:
                    break
            self._process(payload)
            processed += 1
        return processed

    def run_worker(self, stop_after_idle: float = 1.0) -> threading.Thread:
        """启动后台 worker 线程（线上形态：独立 worker 池长驻消费）。"""

        def loop() -> None:
            idle_since = time.time()
            while time.time() - idle_since < stop_after_idle:
                if self.drain(max_jobs=1) > 0:
                    idle_since = time.time()
                else:
                    time.sleep(0.05)

        thread = threading.Thread(target=loop, daemon=True)
        thread.start()
        return thread


def _demo() -> None:
    store = MemoryStore()
    dispatcher = ExtractionDispatcher(store)
    print(f"队列后端：{dispatcher.backend}")

    # 主流程：把抽取任务 fire-and-forget 推入队列，不等待
    for conv_id, utterance in [
        ("c1", "我家在上海，刚搬到浦东。"),
        ("c2", "我是产品经理，喜欢简洁的回答。"),
        ("c3", "我最近出差去成都了。"),
    ]:
        dispatcher.enqueue_extraction("u1", utterance, conv_id)
    print("三条抽取任务已入队（主流程已可返回回答）。\n")

    print("后台 worker 消费：")
    processed = dispatcher.drain()
    print(f"\n共处理 {processed} 个任务，库中事实数：{len(store.all_facts())}")


if __name__ == "__main__":
    _demo()
