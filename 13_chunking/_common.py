"""Chapter 13 shared offline helpers.

确定性离线 embedding：句子向量 = 词频 Counter，相似度 = 余弦（来自
``agent_examples.text``）。有 ``OPENAI_API_KEY`` + ``openai`` 时可换真 embedding，
但本章所有脚本默认离线、可复现，导入不发起网络请求。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent_examples.text import cosine, term_counts  # noqa: E402


def embed(text: str):
    """离线：词频向量。"""

    return term_counts(text)


def embed_similarity(a: str, b: str) -> float:
    """两段文本的余弦相似度（离线词频向量）。"""

    if os.getenv("OPENAI_API_KEY"):
        try:
            from openai import OpenAI

            client = OpenAI()
            va, vb = [d.embedding for d in client.embeddings.create(
                model="text-embedding-3-small", input=[a, b]).data]
            dot = sum(x * y for x, y in zip(va, vb))
            na = sum(x * x for x in va) ** 0.5
            nb = sum(y * y for y in vb) ** 0.5
            return dot / (na * nb) if na and nb else 0.0
        except Exception as exc:  # pragma: no cover
            print(f"[embed] 在线 embedding 不可用，回退离线：{exc}")
    return cosine(term_counts(a), term_counts(b))


SAMPLE_HANDBOOK = (
    "第三章 假期制度。第一节 年假天数。入职满 1 年至 5 年的员工享有 5 个工作日带薪年假。"
    "5 年至 10 年享有 10 个工作日。10 年以上享有 15 个工作日。年假当年有效，不可跨年结转。"
    "第二节 病假。员工患病需请假的，凭医院证明可申请病假。病假期间工资按 80% 发放。"
    "连续病假超过 30 天的，转入医疗期管理。产品线上线下渠道均支持年假申请。"
    "本机支持 5G 双模，电池容量 5000mAh，支持 67W 快充，典型续航 36 小时。"
)


def print_table(headers, rows):
    widths = [len(str(h)) for h in headers]
    for r in rows:
        for i, c in enumerate(r):
            widths[i] = max(widths[i], len(str(c)))
    print("  ".join(str(h).ljust(widths[i]) for i, h in enumerate(headers)))
    print("  ".join("-" * widths[i] for i in range(len(headers))))
    for r in rows:
        print("  ".join(str(c).ljust(widths[i]) for i, c in enumerate(r)))
