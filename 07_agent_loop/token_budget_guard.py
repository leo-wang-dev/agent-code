"""Token 预算守卫：整个任务级别的总预算，而不是每轮预算。

对应文章第 07 篇「五、终止条件是硬骨头 · 第二层：总 token 预算」。

复用 src/agent_code/llm_call.py 的 estimate_tokens 做离线 token 估算，
在这里包一个「任务级」守卫：每消费一段文本就累计，超预算即停。
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_code.llm_call import estimate_tokens


@dataclass
class TokenBudgetGuard:
    """整个任务共享一个预算池，跨轮累计。"""

    total_budget: int
    spent: int = 0
    log: list[dict[str, int]] = field(default_factory=list)

    def would_exceed(self, text: str) -> bool:
        return self.spent + estimate_tokens(text) > self.total_budget

    def charge(self, label: str, text: str) -> bool:
        cost = estimate_tokens(text)
        if self.spent + cost > self.total_budget:
            self.log.append({"label": label, "cost": cost, "charged": 0})
            return False
        self.spent += cost
        self.log.append({"label": label, "cost": cost, "charged": cost})
        return True

    @property
    def remaining(self) -> int:
        return self.total_budget - self.spent


def main() -> None:
    guard = TokenBudgetGuard(total_budget=120)
    turns = [
        ("system", "You are a small reliable agent that uses tools."),
        ("round-1 prompt", "user asks: what is the weather in Shanghai today?"),
        ("round-1 observation", "Shanghai: 31C, clear"),
        ("round-2 prompt", "user asks a much longer follow up " * 20),
    ]
    print(f"任务总预算: {guard.total_budget} tokens\n")
    for label, text in turns:
        ok = guard.charge(label, text)
        status = "计费成功" if ok else "超预算 -> 拒绝并终止任务"
        print(f"  [{label}] 估算 {estimate_tokens(text)} tokens, 剩余 {guard.remaining} -> {status}")
        if not ok:
            break


if __name__ == "__main__":
    main()
