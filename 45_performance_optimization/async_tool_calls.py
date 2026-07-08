"""异步工具调用模式 —— 立即返回+异步通知 / 流式进度 / 工具内部并发。

对应文章第 45 篇 四、异步工具调用。

真实可跑：`python3 async_tool_calls.py`
"""

from __future__ import annotations

import asyncio
import time
import uuid
from typing import AsyncIterator


class TaskQueue:
    """极简后台任务队列（内存版）。生产替换为 Celery / RQ / arq 等。"""

    def __init__(self) -> None:
        self._results: dict[str, dict] = {}

    def submit(self, coro_factory, *args) -> str:
        task_id = uuid.uuid4().hex[:8]
        self._results[task_id] = {"status": "processing"}

        async def _run() -> None:
            result = await coro_factory(*args)
            self._results[task_id] = {"status": "done", "result": result}

        asyncio.create_task(_run())
        return task_id

    def status(self, task_id: str) -> dict:
        return self._results.get(task_id, {"status": "unknown"})


async def _actual_long_task(payload: str) -> str:
    await asyncio.sleep(0.3)
    return f"完成分析: {payload}"


# 模式1：立即返回 + 异步通知
def long_running_task(payload: str, queue: TaskQueue) -> dict:
    task_id = queue.submit(_actual_long_task, payload)
    return {
        "status": "processing",
        "task_id": task_id,
        "estimated_completion": "30 seconds",
        "user_message": "任务正在处理中，完成后会通知您",
    }


# 模式2：流式进度更新
async def long_running_with_progress(steps: list[str]) -> AsyncIterator[dict]:
    yield {"status": "starting", "progress": 0.0}
    for i, step in enumerate(steps, 1):
        await asyncio.sleep(0.1)
        yield {"status": "running", "progress": i / len(steps), "step": step}
    yield {"status": "completed", "result": "全部步骤完成"}


# 工具内部真异步并发
async def comprehensive_research(topic: str) -> dict:
    async def search(source: str, sec: float) -> str:
        await asyncio.sleep(sec)
        return f"{source}:{topic}"

    start = time.perf_counter()
    google, news, papers = await asyncio.gather(
        search("google", 0.3), search("news", 0.3), search("papers", 0.3)
    )
    return {
        "synthesized": f"{google} + {news} + {papers}",
        "elapsed": round(time.perf_counter() - start, 3),
    }


async def _demo() -> None:
    queue = TaskQueue()

    print("=== 模式1：立即返回 + 异步通知 ===")
    ack = long_running_task("500 条数据", queue)
    print(f"  立即返回: {ack['user_message']}  (task_id={ack['task_id']})")
    await asyncio.sleep(0.4)
    print(f"  轮询状态: {queue.status(ack['task_id'])}")

    print("\n=== 模式2：流式进度更新 ===")
    async for update in long_running_with_progress(["抓取", "清洗", "分析", "汇总"]):
        if update["status"] == "running":
            print(f"  进度 {update['progress']:.0%} - {update['step']}")
        else:
            print(f"  {update['status']}")

    print("\n=== 工具内部并发（3 数据源同时）===")
    res = await comprehensive_research("视黄醇")
    print(f"  {res['synthesized']}")
    print(f"  耗时 {res['elapsed']}s (= max 而非 sum)")


if __name__ == "__main__":
    asyncio.run(_demo())
