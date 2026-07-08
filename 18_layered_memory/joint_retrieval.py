"""18 章配套：四层联合检索引擎。

对应文章第四节"四层联合检索：实际怎么协同"，原样落地 assemble_memory_context：

  Layer 1 Profile    → 直接读 KV，全部带上
  Layer 4 Working    → 读当前 session，全部带上
  Layer 2 Preference → 向量检索 Top-2
  Layer 3 Episodic   → 向量检索 Top-10 → 时间衰减重排 Top-3

Episodic 打分公式对齐文章第三节：
  score = semantic_score * 0.6 + time_decay * 0.3 + importance * 0.1

并提供 render_prompt()：把四层渲染成分块明示的 Prompt（Profile / Session / Long-term）。

离线可运行：`python3 18_layered_memory/joint_retrieval.py`
"""

from __future__ import annotations

import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent_examples.text import cosine, term_counts  # noqa: E402
from layered_schema import Layer, LayeredMemory, VectorMemory, build_demo_memory  # noqa: E402


def _semantic(query_emb, mem: VectorMemory) -> float:
    return cosine(query_emb, mem.embedding or term_counts(mem.text))


def rerank_with_time_decay(query_emb, mems: list[VectorMemory], half_life_days: float = 90,
                           top_k: int = 3, now: float | None = None) -> list[VectorMemory]:
    """Episodic 层综合打分：语义 * 0.6 + 时间衰减 * 0.3 + 重要性 * 0.1。"""
    now = now or time.time()
    scored: list[tuple[float, VectorMemory]] = []
    for m in mems:
        age_days = (now - m.updated_at) / 86400
        time_decay = math.exp(-age_days * math.log(2) / half_life_days)  # 半衰期
        semantic = _semantic(query_emb, m)
        score = semantic * 0.6 + time_decay * 0.3 + m.importance * 0.1
        scored.append((score, m))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [m for _, m in scored[:top_k]]


def assemble_memory_context(mem: LayeredMemory, user_id: str, session_id: str, query: str) -> dict:
    """四层联合检索：返回 {profile, working, preferences, episodic}。"""
    query_emb = term_counts(query)

    # Layer 1: Profile —— 直接读 KV，全部带上
    profile = mem.get_profile(user_id)

    # Layer 4: Working —— 读当前 session
    working = mem.get_working(session_id)

    # Layer 2: Preference —— 向量检索 Top-2
    prefs = mem.vectors(user_id, Layer.PREFERENCE)
    prefs = sorted(prefs, key=lambda m: _semantic(query_emb, m), reverse=True)[:2]

    # Layer 3: Episodic —— 先召回多一点（Top-10），再时间衰减重排 Top-3
    episodic = mem.vectors(user_id, Layer.EPISODIC)
    episodic = rerank_with_time_decay(query_emb, episodic, half_life_days=90, top_k=3)

    return {"profile": profile, "working": working, "preferences": prefs, "episodic": episodic}


def render_prompt(context: dict, system: str, query: str) -> str:
    """分块明示的注入格式（比平铺文本模型理解准确率高得多）。"""
    parts = [f"[System]\n{system}\n"]

    profile = context["profile"]
    if profile and profile.as_fields():
        lines = "\n".join(f"{k}：{v}" for k, v in profile.as_fields().items())
        parts.append(f"[User Profile]\n{lines}\n")

    if context["working"]:
        lines = "\n".join(f"- {w.text}" for w in context["working"])
        parts.append(f"[Current Session Context]\n{lines}\n")

    lt_lines = []
    if context["preferences"]:
        lt_lines.append("偏好：")
        lt_lines.extend(f"- {m.text}" for m in context["preferences"])
    if context["episodic"]:
        lt_lines.append("最近事件：")
        lt_lines.extend(f"- {m.text}" for m in context["episodic"])
    if lt_lines:
        parts.append("[Long-term Memory]\n" + "\n".join(lt_lines) + "\n")

    parts.append(f"[Current Query]\n用户：{query}")
    return "\n".join(parts)


def _demo() -> None:
    mem = build_demo_memory()
    query = "帮我把产品 A 的定价方案讲简洁点"

    context = assemble_memory_context(mem, "u1", "s1", query)
    print("联合检索结果：")
    print("  Profile   :", context["profile"].as_fields())
    print("  Working   :", [w.text for w in context["working"]])
    print("  Preference:", [m.text for m in context["preferences"]])
    print("  Episodic  :", [m.text for m in context["episodic"]])

    print("\n组装后的 Prompt：\n" + "=" * 50)
    print(render_prompt(context, "你是一位专业助手。", query))


if __name__ == "__main__":
    _demo()
