"""产物：朴素 RAG（对应文章 §一/§三）。

RAG 的本质不是"让模型变聪明"，是"让模型别瞎猜"：回答前先翻资料，把最相关的几段塞进
Prompt。本文件用仓库 chunk_text + NaiveRAGRetriever 跑通最小链路：切块 → Top-K 向量
检索 → 拼成"只依据下列资料作答"的 Prompt。

同时演示朴素向量检索的天花板（§三）：只找"语义相似"，不保证"业务相关"。

    python3 naive_rag.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_code.rag_essence import Document, NaiveRAGRetriever, chunk_text


# 一小段公司制度库（英文，便于词向量演示；对应文章里的年假/报销例子）。
CORPUS = [
    Document("leave", "Employees with one to five years of service get five days of annual leave."),
    Document("reimburse_flow", "The reimbursement application flow: submit receipts, manager approves, finance reviews."),
    Document("finance_cycle", "Finance pays out approved reimbursements on the payment cycle, about ten business days."),
    Document("it_vpn", "To access the internal VPN, install the client and use your SSO credentials."),
]


def main() -> None:
    print("① 切块（chunk_text）：长文本先切成可检索的小块")
    long_text = " ".join(f"policy sentence number {i}" for i in range(200))
    chunks = chunk_text(long_text, chunk_size=40, overlap=8)
    print(f"    200 词文本 → {len(chunks)} 块（chunk_size=40, overlap=8）")

    retriever = NaiveRAGRetriever(CORPUS)

    print("\n② 朴素 RAG：检索 → 拼 Prompt（让模型只依据资料作答）")
    result = retriever.answer("How many annual leave days after one year?")
    print(f"    命中文档: {result['contexts']}")
    print("    组装出的 Prompt:")
    for line in str(result["prompt"]).splitlines():
        print(f"        {line}")

    print("\n③ 天花板：向量只找'语义相似'，不保证'业务相关'（§三）")
    query = "how long until reimbursement money arrives"
    hits = retriever.search(query)
    print(f"    query = {query!r}")
    for h in hits:
        print(f"        {h.document.id:<14} score={h.score:.3f}")
    print("    问题：真正相关的是 finance_cycle（付款周期），但纯词向量常把")
    print("    reimburse_flow（申请流程）排前面——语义近 ≠ 业务相关。→ 需要 Hybrid + Rerank。")


if __name__ == "__main__":
    main()
