"""产物：无状态 API 意味着什么（对应文章 §一）。

模型 API 就是一个纯函数：response = f(messages, params)。没有 session、没有 cookie、
没有任何跨请求状态。所谓"Agent 记住了用户"，完整流程是：后端把历史存进 DB → 新消息
时取出拼成长 messages → 发给 LLM → 把新的一问一答写回 DB → 下一轮重复。

记忆不在模型里，在你的代码和数据库里。本文件用一个内存"数据库"复现这条回路，并演示
"忘记塞回历史" = 记忆从未存在过（那个上线第一天就翻车的客服 Agent）。

    python3 stateless_memory.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_code.llm_call import ChatMessage


def llm_pure_function(messages: list[ChatMessage]) -> str:
    """模型是纯函数：只根据这次收到的 messages 作答，之前发生过什么它不知道。"""
    joined = " ".join(m.content for m in messages if m.role == "user")
    if "张伟" in joined or "VIP" in joined:
        return "好的张总，已记录您是 VIP。"
    return "请问您贵姓？我这边没有您的信息。"


def turn(db: list[ChatMessage], user_text: str, *, persist_history: bool) -> str:
    """一轮对话。persist_history=False 模拟'忘记把历史塞回去'。"""
    context = list(db) if persist_history else []
    context.append(ChatMessage("user", user_text))
    reply = llm_pure_function(context)
    # 无论如何都写回 DB（记忆是 DB 的事），但请求时是否带上历史，才决定模型看不看得到。
    db.append(ChatMessage("user", user_text))
    db.append(ChatMessage("assistant", reply))
    return reply


def main() -> None:
    print("① 正确：每轮都从 DB 取历史塞回请求")
    db1: list[ChatMessage] = []
    print("    turn1 →", turn(db1, "我是 VIP 客户张伟", persist_history=True))
    print("    turn2 →", turn(db1, "帮我查下订单", persist_history=True))

    print("\n② 翻车：忘了把历史塞回去（容器重启 / 截断 / 漏塞）")
    db2: list[ChatMessage] = []
    print("    turn1 →", turn(db2, "我是 VIP 客户张伟", persist_history=False))
    print("    turn2 →", turn(db2, "帮我查下订单", persist_history=False))
    print("    → 这不是 Bug，是无状态 API 的架构决定的：不塞回历史，记忆就从未存在。")

    print("\n③ 视角转换后一切清晰：")
    print("    '会话记忆丢失'  = 后端持久化问题，不是模型问题")
    print("    '记忆容量'      = 上下文窗口 + Token 预算问题")
    print("    '跨会话长期记忆' = 存储 + 检索架构问题")


if __name__ == "__main__":
    main()
