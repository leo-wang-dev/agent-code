"""17 章配套：Mem0 SDK 完整接入示例。

对应文章第一/五节 + 配套代码承诺"Mem0 SDK 完整接入示例"。

- 有 mem0 依赖 + OPENAI_API_KEY 时，走真实 `from mem0 import Memory`（线上形态）；
- 缺依赖时，用 Mem0OfflineClient 复刻 Mem0 的核心 API 语义（离线默认）：
    add(messages, user_id, agent_id=None, run_id=None)
    search(query, user_id, agent_id=None, run_id=None)
    get_all(user_id, ...) / delete / delete_all
  内部用 operation_engine.OperationEngine 做 ADD/UPDATE/DELETE/NOOP 决策，
  用三层 ID（user/agent/run）做多租户隔离（见 three_tier_id.py）。

Mem0 不是 RAG、不是向量库包装、不是业务数据库——它是 Operation Engine + 版本化存储。

离线可运行：`python3 17_mem0/mem0_integration.py`
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent_examples.text import cosine, term_counts  # noqa: E402
from operation_engine import OperationEngine  # noqa: E402


# 极简规则抽取：从一句用户话得到 (fact_text, slot)。线上由 Mem0 内部 LLM 完成。
_EXTRACT_RULES = [
    ("上海", ("user lives in Shanghai", "location")),
    ("深圳", ("user lives in Shenzhen", "location")),
    ("北京", ("user lives in Beijing", "location")),
    ("产品经理", ("user is a product manager", "occupation")),
    ("简洁", ("user prefers concise answers", "preference")),
    ("养猫", ("user has a cat", "pet")),
    ("猫", ("user has a cat", "pet")),
    ("送人", ("user no longer has a cat 送人了", "pet")),
]


def extract(messages: list[dict]) -> list[tuple[str, str]]:
    text = " ".join(m.get("content", "") for m in messages if m.get("role") == "user")
    facts: list[tuple[str, str]] = []
    seen_slots: set[str] = set()
    for keyword, (fact_text, slot) in _EXTRACT_RULES:
        if keyword in text:
            # 同一句里"送人"优先于"猫"，避免同槽位重复抽
            if slot in seen_slots and slot == "pet":
                facts = [f for f in facts if f[1] != "pet"]
            facts.append((fact_text, slot))
            seen_slots.add(slot)
    return facts


def _scope_key(user_id: str, agent_id: str | None, run_id: str | None) -> str:
    return f"{user_id}|{agent_id or '*'}|{run_id or '*'}"


@dataclass
class Mem0OfflineClient:
    """Mem0 Memory 客户端的离线等价（无依赖、确定性）。"""

    def __post_init__(self) -> None:
        # 每个 (user, agent, run) 作用域一个独立 OperationEngine，实现三层隔离
        self._engines: dict[str, OperationEngine] = {}
        self.backend = "offline"

    def _engine(self, scope: str) -> OperationEngine:
        return self._engines.setdefault(scope, OperationEngine())

    def add(self, messages, user_id: str, agent_id: str | None = None, run_id: str | None = None) -> list[dict]:
        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]
        scope = _scope_key(user_id, agent_id, run_id)
        engine = self._engine(scope)
        results = []
        for i, (fact_text, slot) in enumerate(extract(messages)):
            fid = f"{scope}:{slot}:{i}"
            decision = engine.apply(fid, fact_text, slot)
            results.append({"memory": fact_text, "event": decision.operation, "slot": slot})
        return results

    def search(self, query: str, user_id: str, agent_id: str | None = None,
               run_id: str | None = None, limit: int = 5) -> list[dict]:
        scope = _scope_key(user_id, agent_id, run_id)
        engine = self._engines.get(scope)
        if engine is None:
            return []
        q = term_counts(query)
        hits = []
        for fact in engine.active_facts():
            hits.append((cosine(q, term_counts(fact.text)), fact))
        hits.sort(key=lambda x: x[0], reverse=True)
        return [{"memory": f.text, "score": round(s, 3), "slot": f.slot} for s, f in hits[:limit]]

    def get_all(self, user_id: str, agent_id: str | None = None, run_id: str | None = None) -> list[dict]:
        scope = _scope_key(user_id, agent_id, run_id)
        engine = self._engines.get(scope)
        if engine is None:
            return []
        return [{"memory": f.text, "slot": f.slot, "history": f.history} for f in engine.active_facts()]

    def delete_all(self, user_id: str, agent_id: str | None = None, run_id: str | None = None) -> int:
        scope = _scope_key(user_id, agent_id, run_id)
        engine = self._engines.get(scope)
        if engine is None:
            return 0
        n = len(engine.active_facts())
        for f in engine.facts.values():
            f.deprecated = True
        return n


def get_client():
    """有 mem0 + OPENAI_API_KEY 走真实 SDK；否则离线等价。"""
    if os.environ.get("OPENAI_API_KEY"):
        try:
            from mem0 import Memory

            print("[mem0] 使用真实 Mem0 SDK")
            return Memory.from_config({})  # 线上按需传 vector_store / llm 配置
        except Exception as exc:
            print(f"[mem0] 真实 SDK 不可用（{exc}），降级离线等价。安装：pip install mem0ai")
    else:
        print("[mem0] 未配置 OPENAI_API_KEY，使用离线等价客户端。")
    return Mem0OfflineClient()


def _demo() -> None:
    client = get_client()

    print("\n=== add：事实随对话演进（Operation Engine 决策）===")
    for utterance in ["我是上海人。", "我搬到深圳了。", "顺便我养了只猫。", "其实我不养猫了，之前那只送人了。"]:
        events = client.add(utterance, user_id="u123")
        for e in events:
            print(f"  '{utterance}' → {e['event']:6s} {e['memory']}")

    print("\n=== search：当前有效记忆 ===")
    for hit in client.search("你还记得我住哪吗", user_id="u123"):
        print(f"  {hit['score']}  {hit['memory']}")

    print("\n=== get_all：含版本历史 ===")
    for item in client.get_all("u123"):
        hist = f"  历史={item['history']}" if item["history"] else ""
        print(f"  [{item['slot']}] {item['memory']}{hist}")


if __name__ == "__main__":
    _demo()
