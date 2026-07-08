"""投机执行（Speculative Execution）示例 —— 预判最可能的分支，提前 prefetch。

对应文章第 45 篇 二、几个非并行的常见误区 —— 投机执行。

在能预判的场景下，一边跑分类，一边预取"最可能 intent"的数据：
- 命中 → 数据已就绪，省掉一次串行等待；
- 未命中 → 取消预取，改取真实 intent 的数据。

真实可跑：`python3 speculative_execution.py`（对比投机 vs 纯串行的耗时）。
"""

from __future__ import annotations

import asyncio
import time

LIKELY_INTENT = "query_order"


async def llm_classify(query: str) -> str:
    await asyncio.sleep(0.3)  # 分类调用延迟
    if "退货" in query:
        return "refund"
    return "query_order"


async def fetch_for_intent(intent: str) -> str:
    await asyncio.sleep(0.3)  # 数据获取延迟
    return f"data[{intent}]"


async def with_speculation(query: str) -> dict:
    start = time.perf_counter()
    # 投机：先假设最常见 intent，提前开跑
    likely_task = asyncio.create_task(fetch_for_intent(LIKELY_INTENT))

    actual_intent = await llm_classify(query)
    if actual_intent == LIKELY_INTENT:
        data = await likely_task  # 已经在跑，几乎立即拿到
        hit = True
    else:
        likely_task.cancel()
        data = await fetch_for_intent(actual_intent)
        hit = False
    return {"data": data, "elapsed": time.perf_counter() - start, "spec_hit": hit}


async def without_speculation(query: str) -> dict:
    start = time.perf_counter()
    actual_intent = await llm_classify(query)  # 先分类
    data = await fetch_for_intent(actual_intent)  # 再串行取数
    return {"data": data, "elapsed": time.perf_counter() - start}


async def _demo() -> None:
    print("=== 投机命中（query 属于最可能 intent）===")
    spec = await with_speculation("我的订单到哪了")
    base = await without_speculation("我的订单到哪了")
    print(f"  纯串行     : {base['elapsed']:.2f}s")
    print(f"  投机执行   : {spec['elapsed']:.2f}s (命中={spec['spec_hit']})")
    print(f"  节省       : {(1 - spec['elapsed'] / base['elapsed']):.0%}\n")

    print("=== 投机未命中（预取被取消，回退）===")
    spec2 = await with_speculation("我要退货")
    print(f"  投机执行   : {spec2['elapsed']:.2f}s (命中={spec2['spec_hit']})")
    print("  未命中时约等于串行——投机只在可预判场景有净收益。")


if __name__ == "__main__":
    asyncio.run(_demo())
