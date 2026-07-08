"""产物：Reranker——召回之后的精排（对应文章 §三/§四）。

"召回和答对不是一回事。召回只是把候选资料捞上来，重排才决定哪些资料值得进 Prompt。"

标准两阶段：第一轮召回宁可多捞（recall 优先），第二轮用 reranker 精排，把真正相关的
段落排到前面。本文件用仓库 HybridSearch（第一轮，limit 放大）+ Reranker（第二轮，
短语命中 + 覆盖度加分）演示排序如何被纠正。

    python3 reranker.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_code.rag_essence import Document, HybridSearch, Reranker


CORPUS = [
    Document("d1", "The reimbursement application flow requires submitting receipts first."),
    Document("d2", "Finance pays approved reimbursements on the payment cycle in about ten business days."),
    Document("d3", "Expense categories include travel, meals, and equipment purchases."),
    Document("d4", "Managers approve reimbursement requests before finance reviews them."),
    Document("d5", "How long until reimbursement money arrives depends on the finance payment cycle."),
]


def show(title: str, results) -> None:
    print(f"    {title}")
    for rank, r in enumerate(results, 1):
        print(f"        #{rank} {r.document.id}  score={r.score:.3f}  {r.document.text[:48]}...")


def main() -> None:
    query = "how long until reimbursement money arrives"
    hybrid = HybridSearch(CORPUS)

    # 第一轮：召回多捞一点（limit=5）。
    recalled = hybrid.search(query, limit=5)
    print(f"查询: {query!r}\n")
    print("① 第一轮召回（recall 优先，多捞）")
    show("", recalled)

    # 第二轮：精排，top3 进 Prompt。
    reranked = Reranker().rerank(query, recalled, limit=3)
    print("\n② 第二轮 Rerank（精排，只有 top3 进 Prompt）")
    show("", reranked)

    top1_before = recalled[0].document.id
    top1_after = reranked[0].document.id
    print(f"\n③ 效果：召回 top1 = {top1_before}，重排后 top1 = {top1_after}")
    print("    重排把'真正回答到账时长'的段落顶到最前——这一步直接决定最终答对率。")


if __name__ == "__main__":
    main()
