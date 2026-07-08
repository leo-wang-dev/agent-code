"""产物：四种上下文，全部靠你自己塞进去（对应文章 §一）。

LLM API 无状态，模型看到的世界就是你发过去的 messages 数组。它做任何事需要的信息，
必须分成四类装进去：

  Who     角色与行为约束  → 通常放 System
  What    任务与目标      → User 或 System 末尾
  Context 背景知识与数据  → 工业级系统里占比最大（RAG/历史/工具返回）
  How     输出规范        → 纯文本 / JSON / Markdown / schema

本文件把这四类拼成一段真实的 messages，并打印每类占了多少 token，让你看到工程重心
在哪里——不是找咒语，是搭一条"稳定、低成本"地组装这四类上下文的流水线。

    python3 four_context_types.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_code.llm_call import ChatMessage, estimate_tokens


def assemble_messages() -> list[tuple[str, ChatMessage]]:
    who = ChatMessage("system", "你是严谨的企业客服助手，只依据提供的资料回答，不编造。")
    how = ChatMessage("system", "输出规范：只返回一个 JSON 对象，字段 answer(string)、cited(bool)。")
    context = ChatMessage(
        "user",
        "【检索到的资料】\n- 退款政策：7 天内未拆封可全额退款。\n- 运费：满 99 包邮。",
    )
    what = ChatMessage("user", "任务：用户问'买了 5 天想退能退吗'，据资料回答。")
    # 标注每条属于四类上下文里的哪一类。
    return [("Who", who), ("How", how), ("Context", context), ("What", what)]


def main() -> None:
    tagged = assemble_messages()
    print("把四类上下文拼成一段模型'读得懂、做得对'的 messages：\n")
    total = 0
    for kind, msg in tagged:
        tokens = estimate_tokens(msg.content)
        total += tokens
        print(f"[{kind:<7}] role={msg.role:<9} ≈{tokens:>3}tok  {msg.content.splitlines()[0]}")
    print(f"\n合计 ≈ {total} tokens。")
    print("注意 Context（背景知识/数据）占比最大——工业级 Prompt 的工程量几乎都在这一类：")
    print("  如何把 RAG 结果 / 历史 / 工具返回，稳定、高效、低成本地装进 messages。")
    print("所谓 Prompt 工程 = 搭建这条上下文组装流水线，不是找对咒语。")


if __name__ == "__main__":
    main()
