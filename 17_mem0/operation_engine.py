"""17 章配套：Memory Operation Engine 行为分析。

对应文章第二节"Mem0 的核心机制：Memory Operation Engine"。

每抽到一条新事实，不直接 INSERT——而是让引擎在 4 种操作中决策：
  ADD    —— 全新事实，库里没有
  UPDATE —— 和库里某条相关，但内容有变化（旧的应被更新，旧值进历史）
  DELETE —— 否定库里某条已存在的（如"我已经不在 A 公司了"）
  NOOP   —— 库里已有且无变化（什么都不做，去重）

离线默认用确定性规则引擎（否定词 / 槽位冲突 / 完全相同）复现 Mem0 的决策行为；
有 OPENAI_API_KEY 时可换成 LLM 决策（这里保留规则版，便于稳定复现文章的四个例子）。

离线可运行：`python3 17_mem0/operation_engine.py`
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent_examples.text import cosine, term_counts  # noqa: E402


# 否定语义信号（文章特别提到中文否定判断比英文弱，这里显式列举）
_NEGATION = ["不再", "不养", "送人", "已经不", "不在", "离职", "no longer", "not "]


@dataclass
class StoredFact:
    id: str
    text: str
    slot: str                       # 归一化槽位，如 location / pet / employer
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    deprecated: bool = False
    history: list[str] = field(default_factory=list)  # 版本化：UPDATE 时保留旧值


@dataclass
class Decision:
    operation: str                  # ADD / UPDATE / DELETE / NOOP
    target_id: str | None = None
    reason: str = ""


def _has_negation(text: str) -> bool:
    return any(sig in text for sig in _NEGATION)


def _similar(a: str, b: str) -> float:
    return cosine(term_counts(a), term_counts(b))


class OperationEngine:
    """LLM 驱动的 Operation 决策的确定性规则等价。"""

    def __init__(self, sim_threshold: float = 0.3) -> None:
        self.facts: dict[str, StoredFact] = {}
        self.sim_threshold = sim_threshold
        self.op_counter: dict[str, int] = {"ADD": 0, "UPDATE": 0, "DELETE": 0, "NOOP": 0}

    def _related(self, new_text: str, slot: str) -> StoredFact | None:
        """向量检索召回最相关的旧事实（同槽位优先）。"""
        best: tuple[float, StoredFact] | None = None
        for fact in self.facts.values():
            if fact.deprecated:
                continue
            sim = _similar(new_text, fact.text)
            if fact.slot == slot:
                sim += 0.4  # 同槽位加权，模拟 Mem0 抽取阶段的预关联
            if sim >= self.sim_threshold and (best is None or sim > best[0]):
                best = (sim, fact)
        return best[1] if best else None

    def decide(self, new_text: str, slot: str) -> Decision:
        related = self._related(new_text, slot)
        if related is None:
            return Decision("ADD", reason="库里无相关记忆")
        if _has_negation(new_text):
            return Decision("DELETE", related.id, "新事实在否定已存在事实")
        if related.text == new_text:
            return Decision("NOOP", related.id, "完全相同，去重")
        if related.slot == slot:
            return Decision("UPDATE", related.id, "同槽位内容变化，更新且旧值进历史")
        return Decision("ADD", reason="相关但非同一事实")

    def apply(self, fact_id: str, new_text: str, slot: str) -> Decision:
        decision = self.decide(new_text, slot)
        self.op_counter[decision.operation] += 1
        now = time.time()
        if decision.operation == "ADD":
            self.facts[fact_id] = StoredFact(fact_id, new_text, slot)
        elif decision.operation == "UPDATE":
            target = self.facts[decision.target_id]
            target.history.append(target.text)   # 版本化保留旧值
            target.text = new_text
            target.updated_at = now
        elif decision.operation == "DELETE":
            self.facts[decision.target_id].deprecated = True
        # NOOP: 什么都不做
        return decision

    def active_facts(self) -> list[StoredFact]:
        return [f for f in self.facts.values() if not f.deprecated]


def _demo() -> None:
    engine = OperationEngine()

    # 复现文章的四个对话
    script = [
        ("f1", "user lives in Shanghai", "location", "对话1：首次提到"),
        ("f2", "user lives in Shenzhen", "location", "对话2：一个月后搬家"),
        ("f3", "user no longer has a cat 之前那只送人了", "pet", "对话3：否定养猫"),
        ("f4", "user lives in Shenzhen", "location", "对话4：反复提同一事实"),
    ]
    # 先塞一条养猫事实，供对话3 否定
    engine.apply("cat", "user has a cat", "pet")

    print("Operation Engine 行为分析：")
    for fid, text, slot, note in script:
        d = engine.apply(fid, text, slot)
        target = f" → {d.target_id}" if d.target_id else ""
        print(f"  {note}")
        print(f"    抽取：{text}")
        print(f"    决策：{d.operation}{target}（{d.reason}）")

    print(f"\nOperation 分布（监控指标）：{engine.op_counter}")
    print("活跃事实：")
    for f in engine.active_facts():
        hist = f"  历史={f.history}" if f.history else ""
        print(f"  [{f.slot}] {f.text}{hist}")


if __name__ == "__main__":
    _demo()
