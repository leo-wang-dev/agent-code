"""产物：Hybrid Search（对应文章 §三/§四）。

工业级 RAG 很少只靠 Top-K 向量搜索。Hybrid Search 把两路召回加权融合：
  - 关键词检索：负责精确词、编号、人名、术语（用户打出的 literal token）；
  - 向量检索：负责语义相近。

本文件用仓库 HybridSearch 的 keyword_weight 旋钮跑三档，直观对比同一查询下
"纯关键词 / 纯向量 / 混合" 的排序差异：

    keyword_weight=1.0  → 纯关键词
    keyword_weight=0.0  → 纯向量（等价朴素向量检索）
    keyword_weight=0.45 → 混合

注：离线环境没有真实 embedding，向量分用词频余弦作 stand-in；真实系统换成
embedding 模型即可，融合逻辑不变。

    python3 hybrid_search.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_code.rag_essence import Document, HybridSearch


CORPUS = [
    # 精确命中：带编号 A17，用户打出术语时应被关键词路捞到。
    Document("policy_A17", "Policy A17 defines overtime compensation for night shift workers."),
    # 语义相关但字面不同：讲的也是加班报酬，但没有 A17/overtime 这些词。
    Document("overtime_syn", "Staff working late hours receive extra remuneration under company rules."),
    Document("leave", "Annual leave grants five days after one year of service."),
]


def run(weight: float, query: str):
    return HybridSearch(CORPUS, keyword_weight=weight).search(query, limit=3)


def show(title: str, results) -> None:
    ranked = "  ".join(f"{r.document.id}({r.score:.2f})" for r in results) or "(无命中)"
    print(f"    {title:<24}{ranked}")


def main() -> None:
    print("① 精确术语查询（用户打出了编号 A17）: 'A17 overtime compensation'")
    q1 = "A17 overtime compensation"
    show("纯关键词 w=1.0:", run(1.0, q1))
    show("纯向量   w=0.0:", run(0.0, q1))
    show("混合     w=0.45:", run(0.45, q1))
    print("    → 关键词路把带 A17 的 policy_A17 稳稳捞到最前，编号/术语场景关键词不可少。")

    print("\n② 语义查询（用户没打术语，只描述意图）: 'what pay do employees get for working late'")
    q2 = "what pay do employees get for working late"
    show("纯关键词 w=1.0:", run(1.0, q2))
    show("纯向量   w=0.0:", run(0.0, q2))
    show("混合     w=0.45:", run(0.45, q2))
    print("    → 这类查询靠语义路把 overtime_syn（字面不同、业务相关）捞上来。")

    print("\n③ 结论：两路各有盲区，混合取二者之长。")
    print("    但召回≠答对——谁最终进 Prompt 由第二阶段 Reranker 决定（见 reranker.py）。")


if __name__ == "__main__":
    main()
