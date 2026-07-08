"""工具描述压缩工具 —— 精减冗长的工具/参数描述，并演示 Skills 渐进加载。

对应文章第 43 篇 四、工具描述压缩。

离线可运行：`python3 tool_description_compression.py`
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _tokens import estimate_tokens  # noqa: E402


@dataclass
class ToolSpec:
    name: str
    description: str
    params: dict[str, dict] = field(default_factory=dict)

    def to_prompt(self) -> str:
        lines = [f"{self.name}: {self.description}"]
        for pname, pmeta in self.params.items():
            lines.append(f"  - {pname} ({pmeta.get('type', 'string')}): {pmeta.get('description', '')}")
        return "\n".join(lines)

    def tokens(self) -> int:
        return estimate_tokens(self.to_prompt())


# 常见的啰嗦引导语——真实项目里 90% 的工具描述都以这类句式开头。
_VERBOSE_PATTERNS = [
    r"This tool (queries|returns|is used to|allows you to)\s*",
    r"Use this when.*?\.",
    r"Make sure to handle.*?\.",
    r"The tool takes\s*",
    r"The system will return an error if.*?\.",
    r"typically range.*?\.",
]


def compress_description(text: str, max_chars: int = 80) -> str:
    """把冗长英文描述压成核心信息（保留首句主干 + 截断）。"""
    compact = text
    for pat in _VERBOSE_PATTERNS:
        compact = re.sub(pat, "", compact, flags=re.IGNORECASE | re.DOTALL)
    compact = re.sub(r"\s+", " ", compact).strip()
    if len(compact) > max_chars:
        compact = compact[:max_chars].rstrip() + "…"
    return compact


def compress_tool(tool: ToolSpec) -> ToolSpec:
    new_params = {}
    for pname, pmeta in tool.params.items():
        new_params[pname] = {
            "type": pmeta.get("type", "string"),
            "description": compress_description(pmeta.get("description", ""), max_chars=24),
        }
    return ToolSpec(
        name=tool.name,
        description=compress_description(tool.description, max_chars=60),
        params=new_params,
    )


# ---- Skills 渐进加载：只在需要时才发对应工具组 ----

@dataclass
class SkillGroup:
    skill: str
    tools: list[ToolSpec]


def progressive_loading_tokens(groups: list[SkillGroup], active_skill: str) -> dict:
    """对比：一次发全部 vs 渐进加载（只发激活技能）。"""
    all_tools = [t for g in groups for t in g.tools]
    full = sum(t.tokens() for t in all_tools)

    # 第 1 轮：只发"技能选择器"（每个技能一行）
    selector = sum(estimate_tokens(f"{g.skill}: 激活后加载对应工具") for g in groups)
    # 第 2 轮：激活技能后才发它的工具
    active_tools = next((g.tools for g in groups if g.skill == active_skill), [])
    active = sum(t.tokens() for t in active_tools)

    progressive = selector + active
    return {
        "full_load_tokens": full,
        "progressive_tokens": progressive,
        "saved_ratio": 1 - progressive / full if full else 0.0,
    }


def _sample_tools() -> list[ToolSpec]:
    return [
        ToolSpec(
            "query_customer",
            "This tool queries customer information from the database. Use this when "
            "the user asks about a specific customer. The tool takes a customer_id "
            "parameter and returns the customer's details including name, email, phone, "
            "address, registration date, and order history. Make sure to handle the "
            "case when customer is not found.",
            {
                "customer_id": {
                    "type": "integer",
                    "description": "The unique identifier of the customer. This should "
                    "be a positive integer. The system will return an error if the "
                    "customer does not exist. Customer IDs typically range from 1 to 999999.",
                }
            },
        ),
        ToolSpec(
            "create_refund",
            "This tool is used to create a refund for an order. Use this when the user "
            "requests a refund and the order is eligible.",
            {"order_id": {"type": "integer", "description": "The order id to refund."}},
        ),
    ]


def _demo() -> None:
    print("=" * 60)
    print("一、工具描述压缩对照")
    print("=" * 60)
    total_before = total_after = 0
    for tool in _sample_tools():
        compressed = compress_tool(tool)
        b, a = tool.tokens(), compressed.tokens()
        total_before += b
        total_after += a
        print(f"\n[{tool.name}]  {b} → {a} tokens  省 {1 - a / b:.0%}")
        print("  压缩后描述:", compressed.description)
    print(f"\n合计: {total_before} → {total_after} tokens  省 {1 - total_after / total_before:.0%}")

    print("\n" + "=" * 60)
    print("二、Skills 渐进加载（30 个工具分 3 组）")
    print("=" * 60)
    groups = [
        SkillGroup("客服技能", _sample_tools() * 5),
        SkillGroup("订单技能", _sample_tools() * 5),
        SkillGroup("售后技能", _sample_tools() * 5),
    ]
    stats = progressive_loading_tokens(groups, active_skill="客服技能")
    print(f"一次发全部 : {stats['full_load_tokens']} tokens")
    print(f"渐进加载   : {stats['progressive_tokens']} tokens")
    print(f"节省       : {stats['saved_ratio']:.0%}")


if __name__ == "__main__":
    _demo()
