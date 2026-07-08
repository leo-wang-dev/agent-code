"""产物：分层记忆（Hierarchical Memory）——工业级 Agent 的真实形态（对应文章 §二 末）。

标准结构：
  [system]
  [核心事实摘要]        ← 用户不变信息（长时记忆检索命中）
  [早期对话滚动摘要]     ← 超过 N 轮前的内容压缩
  [最近 K 轮完整原文]    ← 近期上下文高保真
  [本轮 user 输入]

本文件用仓库 LayeredMemory（short_term + summary + long_term 三层）跑一段对话，
按一个 token 预算组装最终上下文，并打印每一层贡献了什么。long_term 检索走词频余弦，
所以事实用英文以便命中演示。

    python3 layered_memory.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_code.memory_essence import LayeredMemory, budget_breakdown


def main() -> None:
    mem = LayeredMemory(user_id="u1")

    # 长时层：用户跨会话不变的事实（永不淘汰）。
    mem.remember_fact("The user is a VIP customer named Zhang Wei.")
    mem.remember_fact("The user prefers concise Python examples.")
    mem.remember_fact("The user works on a RAG project.")

    # 短时层 + 摘要层：本次会话的多轮对话。
    mem.add_turn("I am learning RAG.", "Start with retrieval before generation.")
    mem.add_turn("How do I chunk documents?", "Chunk by semantic boundaries, ~500 tokens.")
    mem.add_turn("Give me a Python snippet.", "Here is a minimal splitter ...")

    query = "Need a Python RAG example for the VIP user"
    context = mem.build_context(query, max_tokens=300)

    print(f"本轮 query: {query}\n")
    print("按 300 token 预算组装出的最终上下文：")
    print("-" * 60)
    for msg in context:
        tag = "长时/摘要层" if msg.role == "system" else "短时层"
        print(f"  [{msg.role:<9}|{tag}] {msg.content}")
    print("-" * 60)
    print(f"预算拆解: {budget_breakdown(context)}")
    print("\n要点：极重要事实永不淘汰(长时)，早期对话压缩(摘要)，近几轮完整保留(短时)，")
    print("      整体再被 token 预算裁一刀——这就是 Hierarchical Memory。")


if __name__ == "__main__":
    main()
