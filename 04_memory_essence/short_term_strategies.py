"""产物：短时记忆的三种形态（对应文章 §二）。

一次会话内的多轮上下文，全靠客户端把历史塞回请求，唯一的敌人是 Token 窗口：

  完整历史  信息零损耗，成本/延迟随轮数线性增长（第10轮可能是第1轮的5倍+）
  滑动窗口  成本可控，早期信息彻底丢 → "我叫张伟"→ 第10轮问"贵姓"的经典翻车
  摘要压缩  成本可控 + 尽量保信息，但多一次 LLM 调用、有损、强依赖摘要 Prompt

本文件用仓库 BufferMemory / WindowMemory / SummaryMemory 把三者并排跑，复现"滑动窗口
忘了名字"的翻车现场，并打印各自的上下文 token 规模。

    python3 short_term_strategies.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_code.llm_call import estimate_message_tokens
from agent_code.memory_essence import BufferMemory, SummaryMemory, WindowMemory


# 一段 10 轮对话，用户在第 1 轮说了名字，第 10 轮又问 Agent 记不记得。
TURNS = [
    ("我叫张伟。", "你好张伟。"),
    ("今天天气不错。", "是的，很适合出门。"),
    ("帮我推荐一本书。", "推荐《人月神话》。"),
    ("再推荐一部电影。", "推荐《盗梦空间》。"),
    ("讲个冷笑话。", "为什么程序员分不清万圣节和圣诞节？"),
    ("因为 Oct 31 == Dec 25。", "哈哈你懂的。"),
    ("帮我算 3 的 5 次方。", "243。"),
    ("北京到上海多远？", "约 1300 公里。"),
    ("谢谢。", "不客气。"),
    ("你还记得我叫什么吗？", "（取决于记忆策略）"),
]


def load(mem: BufferMemory) -> BufferMemory:
    for user, assistant in TURNS[:-1]:
        mem.add("user", user)
        mem.add("assistant", assistant)
    mem.add("user", TURNS[-1][0])
    return mem


def remembers_name(mem: BufferMemory) -> bool:
    text = " ".join(m.content for m in mem.context())
    summary = getattr(mem, "summary", "")
    return "张伟" in text or "张伟" in summary


def main() -> None:
    strategies = {
        "完整历史 BufferMemory": load(BufferMemory()),
        "滑动窗口 WindowMemory(4)": load(WindowMemory(window_size=4)),
        "摘要压缩 SummaryMemory": load(SummaryMemory(keep_last=2)),
    }
    notes = {
        "完整历史 BufferMemory": "全量保留，信息零损耗（但成本随轮数线性涨）",
        "滑动窗口 WindowMemory(4)": "只留最近4条，早期彻底丢 → 第10轮问'贵姓'翻车",
        "摘要压缩 SummaryMemory": "有损压缩，早期事实可能被省略（金额/姓名丢失重灾区）",
    }
    print(f"{'策略':<26}{'注入消息数':>10}{'≈tokens':>10}  记得'张伟'?")
    print("-" * 62)
    for name, mem in strategies.items():
        ctx = mem.context()
        keeps = remembers_name(mem)
        flag = ("是 " if keeps else "否 ") + notes[name]
        print(f"{name:<26}{len(ctx):>10}{estimate_message_tokens(ctx):>10}  {flag}")

    print("\n真实生产很少单用——标准做法是分层混合（见 layered_memory.py）：")
    print("  [核心事实摘要] + [早期滚动摘要] + [最近K轮原文] + [本轮输入]")
    print("  极重要事实永不淘汰，中等重要压缩保留，近几轮完整保留，废话直接丢。")


if __name__ == "__main__":
    main()
