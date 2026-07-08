"""Query Rewrite 模板库（离线可运行）。

第 12 篇正文里的改写 Prompt 集中沉淀成一个**可复用的模板库**——工业级 RAG 团队最大
的核心资产之一，就是这套被反复打磨的「查询改造 Prompt + 解析逻辑 + Fallback」。

本文件提供：
- ``TEMPLATES``：四类改写模板（书面化 / 第三人称 / HyDE / Multi-Query），带占位符；
- ``render``：填充模板；
- ``apply_rewrite``：端到端跑一次改写（在线优先、离线规则式兜底）。

    python3 12_query_rewrite/query_rewrite_templates.py
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _llm import rewrite  # noqa: E402


@dataclass
class PromptTemplate:
    name: str
    purpose: str
    template: str

    def render(self, **kwargs) -> str:
        return self.template.format(**kwargs)


TEMPLATES: dict[str, PromptTemplate] = {
    "formalize": PromptTemplate(
        name="formalize",
        purpose="口语化 → 企业文档书面语",
        template=(
            "请将下面的用户问题改写成更接近企业文档语言的版本。\n"
            "要求：\n- 保留所有关键信息\n- 把口语化表达换成书面化\n"
            "- 输出一句话，不要解释\n\n用户问题：\"{query}\"\n\n改写后："
        ),
    ),
    "third_person": PromptTemplate(
        name="third_person",
        purpose="第一人称视角 → 第三人称（我 → 员工）",
        template=(
            "请把下面问题里的第一人称视角换成第三人称（例如\"我\"换成\"员工\"），"
            "保持原意，只输出一句话：\n\n{query}"
        ),
    ),
    "hyde": PromptTemplate(
        name="hyde",
        purpose="HyDE：先编一段假设性答案，再用答案去检索",
        template=(
            "请基于你的知识，给下面的问题写一段简短的假设性回答。\n"
            "即使你不确定答案，也请按合理的方式编写。\n\n问题：{query}\n\n假设回答（2-3 句话）："
        ),
    ),
    "multi_query": PromptTemplate(
        name="multi_query",
        purpose="Multi-Query：一个问题 → N 种不同问法",
        template=(
            "请将下面的问题改写成 {n} 种不同的表达方式。\n"
            "要求：\n- 每种表达保留原意\n- 用词、句式、视角尽量不同\n- 输出 JSON 数组\n\n"
            "原问题：{query}\n\n不同表达："
        ),
    ),
}


def render(name: str, **kwargs) -> str:
    return TEMPLATES[name].render(**kwargs)


def apply_rewrite(query: str) -> str:
    """端到端改写（在线优先，离线规则式兜底）。"""

    return rewrite(query)


def main() -> None:
    print("=" * 72)
    print("Query Rewrite 模板库")
    print("=" * 72)
    for tpl in TEMPLATES.values():
        print(f"\n【{tpl.name}】{tpl.purpose}")
        print("-" * 60)
        print(tpl.render(query="我们公司允许远程办公吗", n=4))

    print("\n" + "=" * 72)
    print("端到端改写示例（离线规则式 / 在线 LLM 自动切换）")
    print("=" * 72)
    samples = [
        "我去年入职，今年能休几天假",
        "我们公司允许远程办公吗",
        "电池续航怎么样",
        "支持 5G 吗",
    ]
    for q in samples:
        print(f"原问题：{q}")
        print(f"改写后：{apply_rewrite(q)}\n")


if __name__ == "__main__":
    main()
