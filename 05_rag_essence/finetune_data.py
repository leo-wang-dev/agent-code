"""产物：fine-tune 数据构造示例（对应文章 §五"领域优化：领域 embedding 微调"）。

领域优化阶段常见动作之一：用自己的文档构造 (query, positive) 对，去微调领域 embedding
模型，让"业务相关但语义不近"的段落也能被召回。本文件用仓库 build_finetune_pairs 从文档
自动生成训练对，并用 write_jsonl 落成标准 JSONL 训练文件（写到临时目录，离线、不留垃圾）。

    python3 finetune_data.py
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_code.rag_essence import Document, build_finetune_pairs, write_jsonl


CORPUS = [
    Document("leave", "Employees with one to five years of service get five days of annual leave.",
             {"title": "Annual Leave Policy"}),
    Document("reimburse", "Submit receipts, the manager approves, then finance reviews the claim.",
             {"title": "Reimbursement Flow"}),
    Document("vpn", "Install the client and sign in with SSO credentials to reach the internal VPN.",
             {"title": "VPN Access"}),
]


def main() -> None:
    pairs = build_finetune_pairs(CORPUS)

    print("① 从文档自动构造 (query, positive) 训练对")
    for p in pairs:
        print(f"    query   : {p['query']}")
        print(f"    positive: {p['positive']}   (doc={p['document_id']})")

    # 落成标准 JSONL（每行一个训练样本），写到临时目录避免污染仓库。
    out = Path(tempfile.gettempdir()) / "rag_finetune_pairs.jsonl"
    write_jsonl(out, pairs)
    print(f"\n② 已写出 JSONL 训练文件: {out}")
    print("    文件内容（可直接喂给 sentence-transformers 之类的训练脚本）:")
    for line in out.read_text(encoding="utf-8").splitlines():
        print(f"        {line}")

    # 顺带校验 JSONL 每行都是合法 JSON。
    rows = [json.loads(l) for l in out.read_text(encoding="utf-8").splitlines()]
    print(f"\n③ 校验：{len(rows)} 行，全部为合法 JSON。")
    print("    实战里 positive 来自真实点击/人工标注，负样本可用难负例（hard negative）挖掘。")


if __name__ == "__main__":
    main()
