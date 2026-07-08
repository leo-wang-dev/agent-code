"""多意图拆分极简示例（离线可运行）。

复合查询（一句话含多个约束）→ 拆成原子问题 → 各自独立检索 → 求交集/业务规则融合。
对照原文的招聘例子：「找北京 3 年以上 Python、毕业于 985 的后端工程师」拆成 3 个原子
问题分别召回，再求交集。

这里用一个 people 索引演示：每个原子问题过滤出候选集合，最终取交集。离线用规则式
拆分（按顿号/逗号/关键约束词），有 LLM 时可替换为模型拆分。

    python3 12_query_rewrite/multi_intent_split.py
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@dataclass
class Person:
    name: str
    city: str
    years: int
    skill: str
    school_985: bool
    role: str


PEOPLE = [
    Person("A", "北京", 5, "Python", True, "后端工程师"),
    Person("B", "北京", 4, "Python", False, "后端工程师"),
    Person("C", "上海", 6, "Python", True, "后端工程师"),
    Person("D", "北京", 2, "Python", True, "后端工程师"),
    Person("E", "北京", 7, "Java", True, "后端工程师"),
    Person("F", "北京", 5, "Python", True, "前端工程师"),
]


def split_intents(query: str) -> list[str]:
    """极简多意图拆分：按顿号/逗号切，再抽出可判定的原子约束。离线规则式。"""

    parts = [p.strip() for p in re.split(r"[，,、；;]", query) if p.strip()]
    # 合并成语义原子（这里直接把每个片段当一个原子约束）
    return parts


def atom_to_filter(atom: str):
    """把一个原子问题编译成对 Person 的判定函数。

    一个片段可能含多个约束（如『北京 3 年以上 Python 经验』），全部按 AND 生效。
    """

    checks = []
    if "北京" in atom:
        checks.append(lambda p: p.city == "北京")
    m = re.search(r"(\d+)\s*年", atom)
    if m and ("经验" in atom or "以上" in atom):
        yrs = int(m.group(1))
        checks.append(lambda p, y=yrs: p.years >= y)
    if "Python" in atom:
        checks.append(lambda p: p.skill == "Python")
    if "985" in atom:
        checks.append(lambda p: p.school_985)
    if "后端" in atom:
        checks.append(lambda p: p.role == "后端工程师")

    def predicate(p: Person) -> bool:
        return all(check(p) for check in checks)

    return predicate


def multi_intent_retrieve(query: str):
    atoms = split_intents(query)
    # 每个原子独立召回一个候选集合
    candidate_sets = []
    for atom in atoms:
        pred = atom_to_filter(atom)
        candidate_sets.append((atom, {p.name for p in PEOPLE if pred(p)}))
    # 求交集融合
    final = set(p.name for p in PEOPLE)
    for _, s in candidate_sets:
        final &= s
    return atoms, candidate_sets, final


def main() -> None:
    query = "找北京 3 年以上 Python 经验、毕业于 985 的后端工程师"
    atoms, candidate_sets, final = multi_intent_retrieve(query)

    print("=" * 72)
    print("多意图拆分 + 交集融合")
    print("=" * 72)
    print(f"复合查询：{query}\n")
    print("拆分出的原子问题与各自召回：")
    for atom, s in candidate_sets:
        print(f"  · {atom:<24} → {sorted(s)}")
    print(f"\n求交集后的最终结果：{sorted(final)}")
    print("\n对照单一向量检索：一句话塞进去，向量会被多个约束『平均』掉，交集融合则精准。")


if __name__ == "__main__":
    main()
