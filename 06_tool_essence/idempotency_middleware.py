"""产物：幂等中间件（对应文章 §二/§六 "副作用工具必须有 idempotency_key"）。

创建订单、退款、发邮件、扣钱这类有副作用的工具，不能因为模型重试就执行两次。标准做法：
每次调用带一个 idempotency_key，中间件对同一个 key 只真正执行一次，之后直接返回首次结果。

本文件用仓库 IdempotencyStore + idempotent_refund_demo 演示：同一个 idempotency_key
重复提交退款，真实 handler 只跑一次；不同 key 才会产生新退款。

    python3 idempotency_middleware.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_code.tool_essence import IdempotencyStore, default_registry, idempotent_refund_demo


def main() -> None:
    registry = default_registry()
    store = IdempotencyStore()

    # 统计真实 handler 到底被执行了几次（用一个计数器包裹）。
    calls = {"n": 0}
    original = registry.tools["create_refund"].handler

    def counting_handler(args):
        calls["n"] += 1
        return original(args)

    # 通过 __dict__ 替换 handler（frozen dataclass 的字段是只读的，这里换的是 registry 内引用）。
    object.__setattr__(registry.tools["create_refund"], "handler", counting_handler)

    args = {"order_id": "A1001", "amount": 99.0, "idempotency_key": "key-xyz"}

    print("① 同一个 idempotency_key 提交三次（模拟模型重试 / 网络重发）")
    results = [idempotent_refund_demo(store, registry, args) for _ in range(3)]
    for i, r in enumerate(results, 1):
        print(f"    第{i}次返回 refund_id={r['refund_id']} amount={r['amount']}")
    print(f"    → 真实 handler 实际执行次数 = {calls['n']}（三次调用只扣一次款）")

    print("\n② 换一个 idempotency_key = 一笔新退款")
    args2 = args | {"idempotency_key": "key-new"}
    r2 = idempotent_refund_demo(store, registry, args2)
    print(f"    返回 refund_id={r2['refund_id']}  真实执行次数累计 = {calls['n']}")

    print("\n幂等键是副作用工具的底线：模型可以重试，钱不能扣两次。")


if __name__ == "__main__":
    main()
