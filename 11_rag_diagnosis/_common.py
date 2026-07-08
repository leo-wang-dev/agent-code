"""Shared offline helpers for chapter 11 (RAG diagnosis).

All embeddings are deterministic and offline by default (term-frequency vector +
cosine, from ``agent_examples.text``).  If ``OPENAI_API_KEY`` is present *and*
the ``openai`` package is installed, ``embed_texts`` will transparently switch to
real embeddings — otherwise it falls back to the offline equivalent.  Importing
this module never performs a network call.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent_examples.text import cosine, term_counts  # noqa: E402


@dataclass
class LabeledQuery:
    """A colloquial user question with the document id that truly answers it."""

    query: str
    expected_source_id: str
    note: str = ""


def eval_corpus():
    """A small enterprise-handbook corpus reused across the chapter.

    Returns a list of ``agent_examples.rag.Document``.  Kept intentionally small
    so the recall numbers are easy to eyeball.
    """

    from agent_examples.rag import Document

    return [
        Document(
            "hr_leave",
            "第三章 假期制度。第一节 年假天数。入职满 1 年至 5 年的员工享有 5 个工作日带薪年假，"
            "5 年至 10 年享有 10 个工作日，10 年以上享有 15 个工作日。年假当年有效，不可跨年结转。",
            {"category": "hr", "title": "假期制度"},
        ),
        Document(
            "remote",
            "第四章 办公制度。公司支持远程办公，员工需提前一天在系统提交 WFH 申请，"
            "直属经理审批后生效。每周远程办公不得超过 3 天。",
            {"category": "hr", "title": "远程办公"},
        ),
        Document(
            "expense",
            "第二章 报销制度。差旅报销额度根据职级而定。总监及以上 800 元/天，经理级 500 元/天，"
            "普通员工 300 元/天。出差天数超过 5 天的，每天额度上浮 20%。",
            {"category": "finance", "title": "差旅报销"},
        ),
        Document(
            "phone",
            "产品规格。本机支持 5G SA/NSA 双模，兼容主流运营商频段。电池容量 5000mAh，"
            "支持 67W 快充，典型续航 36 小时。",
            {"category": "product", "title": "手机规格"},
        ),
        Document(
            "security",
            "安全制度。所有高危工具调用必须经过人工审批，包含转账、删除数据、修改权限和导出敏感数据。",
            {"category": "security", "title": "工具安全"},
        ),
        Document(
            "onboard",
            "第一章 入职流程。新员工报到当天完成信息登记、领取工牌、配置办公设备，"
            "并在一周内完成安全合规培训。",
            {"category": "hr", "title": "入职流程"},
        ),
        # --- 干扰文档：和口语 query 表面词重叠，但不是正确答案 ---
        # 它们的存在，正是朴素纯向量在口语 query 上『召回伪相关』的根因。
        Document(
            "activity",
            "员工活动。公司每年组织团建、假日出游、节日聚餐，丰富员工业余生活，休闲放松。",
            {"category": "hr", "title": "员工活动"},
        ),
        Document(
            "vpn",
            "网络工具。公司为在家和外出场景提供 VPN 接入，办公电脑需安装公司统一客户端。",
            {"category": "it", "title": "网络工具"},
        ),
        Document(
            "battery_recycle",
            "环保制度。废旧电池、充电设备、电子废弃物须投放到指定回收点，禁止随意丢弃。",
            {"category": "admin", "title": "环保回收"},
        ),
        Document(
            "training",
            "培训制度。新员工入职后参加岗前培训，内容包含公司文化、报销流程和差旅规范讲解。",
            {"category": "hr", "title": "培训制度"},
        ),
    ]


def eval_queries() -> list[LabeledQuery]:
    """Colloquial queries — the gap between user wording and doc wording is the
    whole point of the diagnosis chapter.  每条 query 都刻意和一个干扰文档表面
    重叠，只有做了查询改写 / 结构化切块才能把真答案顶上来。"""

    return [
        # 朴素纯向量在这 3 条上被干扰文档抢走 top-1（『在家办公』撞 vpn、『电池充电』撞 battery_recycle）
        LabeledQuery("在家办公吗", "remote", "口语撞 vpn，需改写为『远程办公 WFH 制度』"),
        LabeledQuery("办公能在家吗", "remote", "口语撞 vpn"),
        LabeledQuery("电池充电快吗", "phone", "口语撞 battery_recycle，需改写为『电池容量 快充 续航』"),
        # 这 3 条朴素也能答对，用来说明『不是全错，是一半错』
        LabeledQuery("我去年入职，今年能休几天假", "hr_leave", "『休几天假』改写为『年假天数』"),
        LabeledQuery("出差报销额度多少", "expense", "关键词已够，朴素也命中"),
        LabeledQuery("删库要审批吗", "security", "关键词已够，朴素也命中"),
    ]


def embed_texts(texts: list[str]):
    """Return a list of vectors. Offline: term-frequency Counters.

    Online (only if ``OPENAI_API_KEY`` set and ``openai`` importable): real
    embeddings. The rest of the code treats vectors opaquely via ``vec_cosine``.
    """

    if os.getenv("OPENAI_API_KEY"):
        try:
            from openai import OpenAI  # noqa: F401

            client = OpenAI()
            resp = client.embeddings.create(model="text-embedding-3-small", input=texts)
            return [item.embedding for item in resp.data]
        except Exception as exc:  # pragma: no cover - network/optional path
            print(f"[embed] 在线 embedding 不可用，回退离线词频向量：{exc}")
    return [term_counts(text) for text in texts]


def vec_cosine(a, b) -> float:
    """Cosine that works for both Counter vectors and list[float] embeddings."""

    if isinstance(a, list) and isinstance(b, list):
        dot = sum(x * y for x, y in zip(a, b))
        na = sum(x * x for x in a) ** 0.5
        nb = sum(y * y for y in b) ** 0.5
        return dot / (na * nb) if na and nb else 0.0
    return cosine(a, b)


def recall_at_k(ranked_source_ids: list[str], expected: str, k: int) -> float:
    """1.0 if the expected source id appears in the top-k, else 0.0."""

    return 1.0 if expected in ranked_source_ids[:k] else 0.0


def print_table(headers: list[str], rows: list[list[str]]) -> None:
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))
    line = "  ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
    print(line)
    print("  ".join("-" * widths[i] for i in range(len(headers))))
    for row in rows:
        print("  ".join(str(cell).ljust(widths[i]) for i, cell in enumerate(row)))
