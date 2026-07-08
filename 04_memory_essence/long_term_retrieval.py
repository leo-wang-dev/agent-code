"""产物：长时记忆——跨会话的"记得你是谁"（对应文章 §四）。

不能靠"把所有历史都塞进来"（窗口装不下 / 成本爆炸 / 噪声压垮信号），所以必须检索式：

  写入路径：用户说了一句 → 判断是否值得记 → 语义抽取事实 → 存向量 + 结构化字段
  读取路径：新消息 → 语义检索最相关的 N 条 → 注入 messages → 发 LLM

看着眼熟——这跟 RAG 一模一样，只是检索对象从"文档"换成"用户历史行为抽取出的事实"。

本文件用仓库 extract_candidate_facts（写入判断+抽取）+ VectorMemory（词频余弦检索）
跑通两条路径，并按用户隔离。事实用英文以便命中演示。

    python3 long_term_retrieval.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_code.memory_essence import VectorMemory, extract_candidate_facts


# 用户在不同会话里说过的话（有的值得记，有的是废话）。
UTTERANCES = [
    "Hello there!",                                  # 废话，不值得记
    "I prefer concise Python examples.",             # 值得记：偏好
    "By the way, my dog is named Momo.",             # 值得记：事实
    "I work as a backend engineer at a fintech.",    # 值得记：职业
    "What time is it?",                              # 废话
    "I live in Shanghai.",                           # 值得记：地点
]


def main() -> None:
    store = VectorMemory()

    print("① 写入路径：判断是否值得记 + 抽取事实")
    for text in UTTERANCES:
        facts = extract_candidate_facts(text)
        if facts:
            for fact in facts:
                store.add_fact("u1", fact)
                print(f"    记 → {fact}")
        else:
            print(f"    丢 → {text!r}（没有可记的事实）")

    print("\n② 读取路径：用本轮消息语义检索最相关的记忆")
    for query in ["Recommend a Python library", "Where should I ship the package?"]:
        hits = store.search("u1", query, limit=2)
        print(f"    query={query!r}")
        for h in hits:
            print(f"        ↳ {h}")

    print("\n③ 多租户隔离：u2 检索不到 u1 的记忆")
    store.add_fact("u2", "I prefer Rust over Python.")
    print(f"    u2 查 'Python' → {store.search('u2', 'Python preference')}")

    print("\n长时记忆的工程底座 = RAG，只是检索对象是'事实'不是'文档'。")
    print("Mem0 的价值 = 把 抽取→存储→检索→注入→遗忘 这条流水线连同一堆坑一起产品化。")


if __name__ == "__main__":
    main()
