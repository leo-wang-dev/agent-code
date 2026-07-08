"""产物：无状态 messages 与三种角色（对应文章 §二 "messages 里那三个角色"）。

核心事实：OpenAI 的 API 完全无状态，每次调用都是一张白纸。所谓"多轮对话"只是把
之前的全部对话手动重新发送一次。这个演示把两轮对话的实际请求逐字打印出来，让你看到
第二轮请求里塞满了第一轮的 user + assistant，模型并不"记得"任何东西。

    python3 stateless_messages.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_code.llm_call import ChatMessage, LLMRequest


SYSTEM = ChatMessage("system", "你是一个友好的助手。")


def as_payload_messages(messages: list[ChatMessage]) -> list[dict[str, str]]:
    return [m.as_dict() for m in messages]


def role_notes() -> None:
    print("三种角色的真相（90% 的人理解错）：")
    print("  system    : 不是 root 指令，只是 RLHF 训练出的统计倾向；安全要放 Guardrail 层")
    print("  user      : 外部数据（RAG/工具返回）也装这里 → 间接 Prompt Injection 攻击面")
    print("  assistant : 最反直觉——API 无状态，靠把它重新发回去才产生'记忆'的错觉")


def main() -> None:
    role_notes()

    # 第一轮：只有 system + user。
    turn1 = [SYSTEM, ChatMessage("user", "我叫张伟")]
    reply1 = ChatMessage("assistant", "你好，张伟。")

    # 第二轮：必须把第一轮的 user + assistant 原样塞回去，再追加新的 user。
    turn2 = [SYSTEM, ChatMessage("user", "我叫张伟"), reply1, ChatMessage("user", "我叫什么？")]

    print("\n" + "=" * 60)
    print("第一轮请求 messages")
    print("=" * 60)
    print(json.dumps(as_payload_messages(turn1), ensure_ascii=False, indent=2))
    print(f"模型回复 → {reply1.content}")

    print("\n" + "=" * 60)
    print("第二轮请求 messages（注意：第一轮全部被重新发送）")
    print("=" * 60)
    print(json.dumps(as_payload_messages(turn2), ensure_ascii=False, indent=2))
    print("模型回复 → 你叫张伟。   （不是记得，是又读了一遍脚本）")

    print("\n" + "=" * 60)
    print("由此推出的四个工程结论")
    print("=" * 60)
    print("  1. 对话越长，每一轮请求越贵（历史线性增长）")
    print("  2. 会话持久化不是模型的事，是你存 Redis 的事")
    print("  3. 容器重启 / 浏览器刷新，记忆就没了，除非自己持久化")
    print("  4. 上下文窗口是整段对话的硬顶，超了得截断或摘要")

    # 顺带展示：stream 请求体会自动带上 stream_options。
    req = LLMRequest(model="gpt-4o", messages=turn2, stream=False)
    print(f"\n实际 payload 键：{sorted(req.payload().keys())}")


if __name__ == "__main__":
    main()
