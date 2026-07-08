"""并发 fan-out / fan-in 完整 demo —— 用 asyncio 真并发，对比串行 vs 并行。

对应文章第 45 篇 二、并发优化 —— 能并行的全部并行。

真实可跑：`python3 concurrent_fanout.py`（用真实 asyncio.sleep 模拟 IO 延迟）。
"""

from __future__ import annotations

import asyncio
import time


async def _io_task(name: str, seconds: float) -> str:
    """模拟一次独立 IO（工具调用 / 检索），耗时 seconds。"""
    await asyncio.sleep(seconds)
    return f"{name}(done in {seconds}s)"


async def run_serial(tasks: list[tuple[str, float]]) -> tuple[list[str], float]:
    start = time.perf_counter()
    results = []
    for name, sec in tasks:
        results.append(await _io_task(name, sec))
    return results, time.perf_counter() - start


async def run_parallel(tasks: list[tuple[str, float]]) -> tuple[list[str], float]:
    start = time.perf_counter()
    results = await asyncio.gather(*(_io_task(n, s) for n, s in tasks))
    return list(results), time.perf_counter() - start


# ---- fan-out / fan-in：多 worker 汇聚到 aggregator（对齐文章 LangGraph 例子）----

async def orchestrator(query: str) -> dict:
    async def research_worker() -> str:
        await asyncio.sleep(0.3)
        return f"research({query})"

    async def pricing_worker() -> str:
        await asyncio.sleep(0.2)
        return f"pricing({query})"

    async def compliance_worker() -> str:
        await asyncio.sleep(0.25)
        return f"compliance({query})"

    start = time.perf_counter()
    # fan-out：三个 worker 并行
    research, pricing, compliance = await asyncio.gather(
        research_worker(), pricing_worker(), compliance_worker()
    )
    # fan-in：aggregator 汇聚
    aggregated = f"[汇总] {research} | {pricing} | {compliance}"
    return {"result": aggregated, "elapsed": time.perf_counter() - start}


async def _demo() -> None:
    tasks = [("get_weather", 0.3), ("get_calendar", 0.3), ("get_news", 0.3)]

    _, serial_t = await run_serial(tasks)
    _, parallel_t = await run_parallel(tasks)

    print("=== 工具调用：串行 vs 并行 ===")
    print(f"  串行(逐个 await)   : {serial_t:.2f}s")
    print(f"  并行(asyncio.gather): {parallel_t:.2f}s")
    print(f"  加速               : {serial_t / parallel_t:.1f}x\n")

    print("=== fan-out / fan-in（3 worker → aggregator）===")
    out = await orchestrator("采购不锈钢")
    print(f"  {out['result']}")
    print(f"  总耗时 {out['elapsed']:.2f}s (= max(worker) 而非 sum)")


if __name__ == "__main__":
    asyncio.run(_demo())
