"""产物：Token 预算管理——主动规划而非被动报错（对应文章 §三）。

玩具路径：list 存历史，每轮 append，直到某天 OpenAI 报 context_length_exceeded 才加截断。
工业做法：建一张预算表，每次拼装 messages 之前先做预算核算，超了就压缩历史——
上下文溢出应该是"从来不会出现"的 error。

本文件建出文章里的预算表，并用仓库 fit_messages_to_budget 演示"历史超预算 → 主动裁剪"，
再打印 budget_breakdown。

    python3 token_budget_planner.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_code.llm_call import ChatMessage, estimate_message_tokens
from agent_code.memory_essence import budget_breakdown, fit_messages_to_budget


# 文章 §三 的预算表。
BUDGET_TABLE = [
    ("System Prompt", 800, "固定"),
    ("Tool Schemas", 500, "固定"),
    ("用户档案注入", 300, "半固定"),
    ("RAG 检索结果", 3000, "动态，上限"),
    ("对话历史", 4000, "动态，超过就压缩"),
    ("输出预留 max_tokens", 2000, "硬预留"),
]
HISTORY_BUDGET = 4000


def show_budget_table() -> None:
    print("① 预算表（拼装前先核算，而不是等报错）")
    print(f"    {'项':<22}{'≈token':>8}  备注")
    total = 0
    for name, tok, note in BUDGET_TABLE:
        total += tok
        print(f"    {name:<22}{tok:>8}  {note}")
    print(f"    {'合计':<22}{total:>8}")


def show_active_trimming() -> None:
    # 造一段"超预算"的历史（每条约 60~80 token，凑到 > 4000）。
    history = [
        ChatMessage("user" if i % 2 == 0 else "assistant", f"这是第 {i} 轮对话的内容，" + "细节铺陈 " * 12)
        for i in range(80)
    ]
    before = estimate_message_tokens(history)
    trimmed = fit_messages_to_budget(history, HISTORY_BUDGET)
    after = estimate_message_tokens(trimmed)
    print("\n② 主动裁剪：历史超预算就压缩，保留最近的")
    print(f"    裁剪前 {len(history)} 条 ≈ {before} tokens")
    print(f"    裁剪后 {len(trimmed)} 条 ≈ {after} tokens（预算 {HISTORY_BUDGET}）")
    print(f"    breakdown: {budget_breakdown(trimmed)}")


def main() -> None:
    show_budget_table()
    show_active_trimming()
    print("\n③ 更进一步（都很'后端'）：")
    print("    - 按用户维度统计 token 消耗，防注入/防单人烧光全公司预算")
    print("    - 按会话降级：预算超了先降模型 → 再降历史长度 → 最后才拒绝服务")
    print("    - 冷热分离：近期历史放 Redis，更早放 Postgres，再早压缩归档")


if __name__ == "__main__":
    main()
