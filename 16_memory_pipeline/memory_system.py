"""16 章配套：约 230 行的最小可上线 Memory 系统完整实现。

对应文章《跨会话长期记忆的工程链路》第六节"最简单的可上线 Memory 系统"。

五步工程链路：抽取 → 存储 → 检索 → 注入 → 遗忘。
本文件聚焦「存储 + 检索 + 注入」三步，并提供数据库等价的内存实现；
抽取见 extraction_prompt.py，异步队列见 async_queue.py，遗忘 CronJob 见
forgetting_cron.py，用户面板 API 见 memory_panel_api.py。

离线可运行：`python3 16_memory_pipeline/memory_system.py`
不依赖 PostgreSQL / pgvector——用 agent_examples.text 的词频余弦做「Embedding 等价」，
线上把 embed() / vector_search() 换成 pgvector 即可，检索打分逻辑一行都不用改。
"""

from __future__ import annotations

import math
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent_examples.text import Counter, cosine, term_counts  # noqa: E402


# --- 存储层：memory_facts 表的内存等价 ---------------------------------------
# 对齐文章正文给出的 SQL schema（memory_facts 表的每个字段都在这里）。
#
#   CREATE TABLE memory_facts (
#       id, user_id, type, key, value, embedding, confidence,
#       importance, source_conversation_id, created_at, updated_at,
#       expires_at, is_deprecated
#   );
@dataclass
class MemoryFact:
    id: str
    user_id: str
    type: str                       # semantic / episodic
    key: str                        # 属性名，如 location / preference
    value: str                      # 事实内容
    confidence: float = 0.8         # 抽取置信度
    importance: float = 0.5         # 重要性（排序 + 遗忘用）
    source_conversation_id: Optional[str] = None  # 溯源：来自哪轮对话
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None            # 可选 TTL
    is_deprecated: bool = False                    # 事实变更时旧事实标过期
    embedding: Optional[Counter] = None            # 向量（此处用词频等价）

    @property
    def text(self) -> str:
        return f"{self.key}: {self.value}"


# 每次对话都该携带的「用户档案级」高频属性——不进 Top-K 竞争。
PROFILE_KEYS = ("name", "location", "occupation")


def embed(text: str) -> Counter:
    """线上换成真实 embedding 模型；离线用词频向量等价。"""
    return term_counts(text)


class MemoryStore:
    """memory_facts 表 + 向量索引的内存实现。"""

    def __init__(self) -> None:
        self._facts: dict[str, MemoryFact] = {}

    # --- 写入：ADD / UPDATE / NOOP（最小去重逻辑）------------------------------
    def upsert(self, fact: MemoryFact) -> str:
        if fact.embedding is None:
            fact.embedding = embed(fact.value)
        existing = self._facts.get(fact.id)
        if existing and not existing.is_deprecated:
            if existing.value == fact.value:
                # 同一事实反复出现：只抬置信度/重要性，不新增（去重）。
                existing.confidence = max(existing.confidence, fact.confidence)
                existing.importance = max(existing.importance, fact.importance)
                return "NOOP"
            # 事实变更："旧事实不删，只标过期，保留追溯"。
            existing.is_deprecated = True
            existing.updated_at = time.time()
            fact.created_at = existing.created_at
            self._facts[fact.id] = fact
            return "UPDATE"
        self._facts[fact.id] = fact
        return "ADD"

    def all_facts(self) -> list[MemoryFact]:
        return list(self._facts.values())

    # --- 向量检索：pgvector vector_search 的内存等价 --------------------------
    def vector_search(self, user_id: str, query_emb: Counter, k: int = 20) -> list[MemoryFact]:
        hits: list[tuple[float, MemoryFact]] = []
        for fact in self._facts.values():
            if fact.user_id != user_id or fact.is_deprecated:
                continue
            sim = cosine(query_emb, fact.embedding or embed(fact.value))
            fact_semantic_score = sim
            setattr(fact, "_semantic_score", fact_semantic_score)
            hits.append((sim, fact))
        hits.sort(key=lambda item: item[0], reverse=True)
        return [fact for _, fact in hits[:k]]

    def query_by_keys(self, user_id: str, keys: tuple[str, ...]) -> list[MemoryFact]:
        result = []
        for fact in self._facts.values():
            if fact.user_id == user_id and not fact.is_deprecated and fact.key in keys:
                setattr(fact, "_semantic_score", getattr(fact, "_semantic_score", 0.0))
                result.append(fact)
        return result


# --- 检索层：综合打分（原样落地文章正文的 retrieve_memory）--------------------
@dataclass
class ScoredFact:
    fact: MemoryFact
    score: float


def retrieve_memory(store: MemoryStore, user_id: str, query: str, k: int = 5) -> list[ScoredFact]:
    """召回策略 = 语义检索 + 时间衰减 + 重要性加权 + 类型过滤。

    打分公式对齐文章：score = semantic*0.6 + time_decay*0.2 + importance*0.2
    """
    # 1. 语义检索（向量库）——召回多一点，等会重排
    query_emb = embed(query)
    semantic_facts = store.vector_search(user_id, query_emb, k=20)

    # 2. 结构化属性（关系型）——高频属性始终一起带上，不和零散事实争 Top-K
    structural_facts = store.query_by_keys(user_id, PROFILE_KEYS)

    # 3. 综合打分（语义相似度 × 时间衰减 × 重要性）
    now = time.time()
    scored: list[ScoredFact] = []
    seen: set[str] = set()
    for fact in semantic_facts + structural_facts:
        if fact.id in seen:
            continue
        seen.add(fact.id)
        age_days = (now - fact.updated_at) / 86400
        time_decay = math.exp(-age_days / 90)  # 90 天半衰期
        semantic = getattr(fact, "_semantic_score", 0.0)
        score = semantic * 0.6 + time_decay * 0.2 + fact.importance * 0.2
        scored.append(ScoredFact(fact, score))

    # 4. Top-K（3~5 条，太多稀释主上下文）
    scored.sort(key=lambda item: item.score, reverse=True)
    return scored[:k]


# --- 注入层：分块明示，长期事实与短时对话分离 --------------------------------
def build_memory_block(scored: list[ScoredFact]) -> str:
    """把召回的记忆渲染成自然语言段落，放在 System Prompt 之后、对话历史之前。"""
    if not scored:
        return ""
    lines = ["[Long-term Memory] 关于这位用户："]
    for item in scored:
        lines.append(f"  - {item.fact.text}")
    return "\n".join(lines)


def assemble_prompt(system: str, memory_block: str, history: list[str], query: str) -> str:
    parts = [f"[System] {system}"]
    if memory_block:
        parts.append(memory_block)
    if history:
        parts.append("[Recent Conversation]")
        parts.extend(f"  {line}" for line in history)
    parts.append(f"[User] {query}")
    return "\n".join(parts)


def build_demo_store() -> MemoryStore:
    """用规则式抽取（见 extraction_prompt.py）灌一批 demo 事实。"""
    from extraction_prompt import extract_facts

    store = MemoryStore()
    conversation = [
        ("c1", "我家在上海，刚搬到浦东。"),
        ("c2", "我是产品经理，喜欢简洁的回答。"),
        ("c3", "我最近出差去成都了。"),
        ("c4", "顺便说下我口味比较重，喜欢辣。"),
    ]
    for conv_id, utterance in conversation:
        for fact in extract_facts("u1", utterance, source_conversation_id=conv_id):
            store.upsert(fact)
    return store


def _demo() -> None:
    store = build_demo_store()
    print(f"库中事实数：{len(store.all_facts())}")

    query = "帮我写个简洁的产品方案"
    scored = retrieve_memory(store, "u1", query, k=3)
    print(f"\n查询：{query}")
    print("召回 Top-3（含综合打分）：")
    for item in scored:
        print(f"  {item.score:6.3f}  [{item.fact.type}] {item.fact.text}")

    memory_block = build_memory_block(scored)
    prompt = assemble_prompt(
        system="你是一个客服助手。",
        memory_block=memory_block,
        history=["user: 上次那个方案怎么样了？", "assistant: 已经在推进中。"],
        query=query,
    )
    print("\n组装后的 Prompt：\n" + "-" * 48)
    print(prompt)


if __name__ == "__main__":
    _demo()
