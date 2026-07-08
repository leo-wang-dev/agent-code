"""18 章配套：4 层 Memory 完整 schema。

对应文章第二节"分层记忆架构 —— 4 层模型"。

按「访问模式」把一张 fact 表拆成 4 层，各自独立的存储介质 / 检索 / 遗忘 / 抽取：

  Layer 1 Profile    用户档案层  —— KV/关系型  · 每次直接读     · 无 TTL   · 结构化映射抽取
  Layer 2 Preference 偏好层      —— 向量库      · 语义 Top-2     · 重要性衰减 · LLM 抽取
  Layer 3 Episodic   事件层      —— 向量+时间   · 语义+时间 Top-3· TTL      · LLM 抽取(带时间戳)
  Layer 4 Working    临时上下文层 —— Redis/Session · 直接读全部  · 会话结束销毁 · 可选抽取

本文件提供 4 层的数据结构 + 一个内存版 LayeredMemory 存储（离线等价 KV/向量/session）。
联合检索见 joint_retrieval.py。

离线可运行：`python3 18_layered_memory/layered_schema.py`
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent_examples.text import Counter, term_counts  # noqa: E402


class Layer(str, Enum):
    PROFILE = "profile"       # Layer 1
    PREFERENCE = "preference"  # Layer 2
    EPISODIC = "episodic"     # Layer 3
    WORKING = "working"       # Layer 4


# 文章"一张关键决策表"——每层的治理策略，代码里作为元数据可查。
LAYER_POLICY = {
    Layer.PROFILE:    {"persist": True,  "vectorize": False, "retrieval": "direct", "always_inject": True,  "ttl": None,      "editable": True,  "extract": "structured"},
    Layer.PREFERENCE: {"persist": True,  "vectorize": True,  "retrieval": "semantic", "always_inject": False, "ttl": None,      "editable": True,  "extract": "llm"},
    Layer.EPISODIC:   {"persist": True,  "vectorize": True,  "retrieval": "semantic+time", "always_inject": False, "ttl": 90*86400, "editable": True,  "extract": "llm"},
    Layer.WORKING:    {"persist": False, "vectorize": False, "retrieval": "direct", "always_inject": True,  "ttl": "session", "editable": False, "extract": "optional"},
}


@dataclass
class ProfileRecord:
    """Layer 1：固定 schema 字段，不存自由文本。"""
    user_id: str
    name: str | None = None
    gender: str | None = None
    age_range: str | None = None
    occupation: str | None = None
    location: str | None = None
    education: str | None = None
    updated_at: float = field(default_factory=time.time)

    def as_fields(self) -> dict[str, str]:
        keys = ("name", "gender", "age_range", "occupation", "location", "education")
        return {k: getattr(self, k) for k in keys if getattr(self, k)}


@dataclass
class VectorMemory:
    """Layer 2/3：一段自由文本 + Embedding。Episodic 强制带时间戳。"""
    id: str
    user_id: str
    layer: Layer
    text: str
    importance: float = 0.5
    confidence: float = 0.8
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    expires_at: float | None = None
    embedding: Counter | None = None

    def __post_init__(self) -> None:
        if self.embedding is None:
            self.embedding = term_counts(self.text)


@dataclass
class WorkingItem:
    """Layer 4：会话级临时状态，不持久化。"""
    session_id: str
    text: str
    created_at: float = field(default_factory=time.time)


class LayeredMemory:
    """4 层存储的内存实现：KV(Profile) + 向量(Pref/Epi) + Session(Working)。"""

    def __init__(self) -> None:
        self._profiles: dict[str, ProfileRecord] = {}          # user_id -> Profile
        self._vectors: dict[str, VectorMemory] = {}            # id -> VectorMemory
        self._sessions: dict[str, list[WorkingItem]] = {}      # session_id -> items

    # --- Layer 1 Profile：KV 直接读写 + UPSERT ---
    def upsert_profile(self, user_id: str, **fields) -> ProfileRecord:
        rec = self._profiles.setdefault(user_id, ProfileRecord(user_id))
        for k, v in fields.items():
            if v:
                setattr(rec, k, v)
        rec.updated_at = time.time()
        return rec

    def get_profile(self, user_id: str) -> ProfileRecord | None:
        return self._profiles.get(user_id)

    # --- Layer 2/3 向量层：写入 + 检索由 joint_retrieval 负责 ---
    def add_vector(self, mem: VectorMemory) -> None:
        self._vectors[mem.id] = mem

    def vectors(self, user_id: str, layer: Layer) -> list[VectorMemory]:
        now = time.time()
        out = []
        for m in self._vectors.values():
            if m.user_id != user_id or m.layer != layer:
                continue
            if m.expires_at and m.expires_at < now:  # TTL 过期不返回
                continue
            out.append(m)
        return out

    # --- Layer 4 Working：session 读写，会话结束销毁 ---
    def add_working(self, item: WorkingItem) -> None:
        self._sessions.setdefault(item.session_id, []).append(item)

    def get_working(self, session_id: str) -> list[WorkingItem]:
        return self._sessions.get(session_id, [])

    def end_session(self, session_id: str) -> int:
        items = self._sessions.pop(session_id, [])
        return len(items)


def build_demo_memory() -> LayeredMemory:
    mem = LayeredMemory()
    mem.upsert_profile("u1", name="张伟", location="上海", occupation="产品经理")
    mem.add_vector(VectorMemory("u1:pref:1", "u1", Layer.PREFERENCE, "喜欢简洁、直接的回答", importance=0.7))
    mem.add_vector(VectorMemory("u1:pref:2", "u1", Layer.PREFERENCE, "关注成本敏感度", importance=0.6))
    now = time.time()
    mem.add_vector(VectorMemory("u1:epi:1", "u1", Layer.EPISODIC, "3 月 5 日咨询过产品 A 的基础功能",
                                created_at=now - 3*86400, updated_at=now - 3*86400, expires_at=now + 87*86400))
    mem.add_vector(VectorMemory("u1:epi:2", "u1", Layer.EPISODIC, "2 月 28 日提到正在评估同类产品",
                                created_at=now - 10*86400, updated_at=now - 10*86400, expires_at=now + 80*86400))
    mem.add_working(WorkingItem("s1", "本次咨询主题：产品 A 的定价方案"))
    mem.add_working(WorkingItem("s1", "用户当下状态：希望快速给出答案"))
    return mem


def _demo() -> None:
    print("4 层 Memory schema 与治理策略：")
    for layer, policy in LAYER_POLICY.items():
        print(f"  [{layer.value:10s}] persist={str(policy['persist']):5s} vectorize={str(policy['vectorize']):5s} "
              f"retrieval={policy['retrieval']:14s} always_inject={str(policy['always_inject']):5s} ttl={policy['ttl']}")

    mem = build_demo_memory()
    print("\nLayer 1 Profile（直接读）：", mem.get_profile("u1").as_fields())
    print("Layer 2 Preference：", [m.text for m in mem.vectors("u1", Layer.PREFERENCE)])
    print("Layer 3 Episodic：", [m.text for m in mem.vectors("u1", Layer.EPISODIC)])
    print("Layer 4 Working（session s1）：", [w.text for w in mem.get_working("s1")])

    n = mem.end_session("s1")
    print(f"\n会话结束销毁 Working：{n} 条，销毁后：{mem.get_working('s1')}")


if __name__ == "__main__":
    _demo()
