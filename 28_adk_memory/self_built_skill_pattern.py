"""在 ADK 之上自建 Skill 模式的完整示例（社区模式，非 ADK 原生）。

对应文章第一节"Skills 模式 —— 在 ADK 之上自建的知识包"。

⚠️ 重要边界：ADK 官方核心 API 里没有 "Skill" 一等公民。Skill 是工程师用
ADK 原生能力（InstructionProvider 动态指令 + 动态 tools 列表）自己搭出来的
"工具 + 指令 + 知识"打包模式。本脚本自定义 Skill dataclass + 注册表，
并复刻其真正价值 —— 渐进加载（progressive loading）省 token。

真实 ADK 里 InstructionProvider 是原生的：instruction 可以传一个 Callable
    def make_instruction(ctx) -> str: ...
    agent = LlmAgent(instruction=make_instruction)
本脚本用确定性 mock ctx 复刻这套动态指令 + 按激活技能加载工具。
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field

try:  # google-adk 导入 try/except 保护
    from google.adk.agents import LlmAgent  # noqa: F401

    HAS_ADK = True
except ImportError:
    HAS_ADK = False


# ---- 自定义（非 ADK 原生）Skill 数据结构 ----
@dataclass
class Skill:
    name: str          # 元数据：标识
    description: str    # 元数据：短描述（用于路由）
    instruction: str    # 指令层：完整操作指南
    tools: list = field(default_factory=list)  # 工具层：关联工具


# ---- 工具们 ----
def search_web(q: str) -> str:
    return f"搜到 {q} 的资料"


def summarize_text(t: str) -> str:
    return "已总结"


def draft_answer(t: str) -> str:
    return "已起草回答"


REGISTRY = {
    "research": Skill("research", "联网调研并归纳",
                      "你是调研专家：先 search_web 再 summarize_text。",
                      [search_web, summarize_text]),
    "qa": Skill("qa", "基于资料回答问题",
                "你是答疑专家：用 draft_answer 组织回答。",
                [draft_answer]),
}


@dataclass
class Ctx:
    state: dict = field(default_factory=dict)


def activate_skill(name: str, ctx: Ctx) -> dict:
    active = ctx.state.setdefault("active_skills", [])
    if name not in active:
        active.append(name)
    return {"activated": name}


# ---- ADK 原生 InstructionProvider：Callable 驱动的动态 instruction ----
def make_instruction(ctx: Ctx) -> str:
    active = ctx.state.get("active_skills", [])
    if not active:
        catalog = "、".join(f"{s.name}({s.description})" for s in REGISTRY.values())
        return f"请先激活技能。可用技能：{catalog}"
    skill = REGISTRY[active[0]]
    return f"你已激活 {skill.name}：{skill.instruction}"


# ---- 渐进加载：get_tools 随激活状态变化 ----
def get_tools(ctx: Ctx) -> list:
    tools = [activate_skill]  # 第一轮只有"激活技能"这一个
    for name in ctx.state.get("active_skills", []):
        tools.extend(REGISTRY[name].tools)
    return tools


def _tool_names(tools: list) -> list[str]:
    return [getattr(t, "__name__", str(t)) for t in tools]


def _schema_tokens(tools: list) -> int:
    return len(tools) * 200  # 粗估：每个工具 schema ~200 tokens


def main() -> int:
    if not HAS_ADK:
        print("[提示] 未检测到 google-adk。Skill 本就是自建模式（非 ADK 原生），")
        print("       此处用确定性 mock 复刻；InstructionProvider 是 ADK 原生能力。")
        print("       安装真实框架： pip install google-adk")
        print("-" * 60)

    ctx = Ctx()

    print("== 第 1 轮（未激活任何技能） ==")
    print("   instruction:", make_instruction(ctx))
    t1 = get_tools(ctx)
    print("   可用工具:", _tool_names(t1), f"(~{_schema_tokens(t1)} tokens)")

    print("\n   LLM 判断需要 research 技能 -> activate_skill('research')")
    activate_skill("research", ctx)

    print("\n== 第 2 轮（激活 research 后，同一对话内） ==")
    print("   instruction:", make_instruction(ctx))
    t2 = get_tools(ctx)
    print("   可用工具:", _tool_names(t2), f"(~{_schema_tokens(t2)} tokens)")

    full = _schema_tokens([activate_skill, search_web, summarize_text, draft_answer])
    print(f"\n== Token 对比 ==")
    print(f"   传统全量发送: ~{full} tokens/轮")
    print(f"   渐进加载首轮: ~{_schema_tokens(t1)} tokens（只发激活入口）")
    print("   结论：工具多(>10)时渐进加载显著省 token；工具少则别自建，反增复杂度。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
