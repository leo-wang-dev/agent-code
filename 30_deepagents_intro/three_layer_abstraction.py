"""三层抽象对比代码 —— Runtime / Framework / Harness。

对应文章第 30 篇「一、Agent 生态的三层抽象」「六、和其他框架的位置对比」。

纯标准库，直接跑：
    python3 30_deepagents_intro/three_layer_abstraction.py

核心论点：三层的本质区别是「控制流谁来负责」。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Layer:
    name: str
    you_do: str          # 你需要做什么
    control_flow: str    # 控制流谁负责
    examples: list[str]


LAYERS = [
    Layer("Runtime", "定义图节点和边", "由你写代码定义", ["LangGraph", "Temporal", "Inngest"]),
    Layer("Framework", "提供积木，你自己拼装", "由你写代码控制", ["LangChain", "CrewAI", "PydanticAI"]),
    Layer("Harness", "添加你的工具和 Prompt", "既定的，框架决定", ["Claude Code", "Aider", "Goose", "DeepAgents"]),
]

# 把主流项目钉到三层模型上（文章「六」的定位表）。
POSITIONING = [
    ("Harness (SDK)", ["DeepAgents", "OpenHands"]),
    ("Harness (产品)", ["Claude Code", "Cursor", "Aider", "Goose"]),
    ("Framework + Runtime", ["CrewAI", "Google ADK"]),
    ("Framework", ["LangChain", "PydanticAI"]),
    ("Runtime", ["LangGraph", "Temporal", "Inngest"]),
]

# 工程类比（文章「三个抽象层级的工程类比」）。
ANALOGIES = {
    "厨房": {"Runtime": "火、刀、锅、案板", "Framework": "+ 各种食材和工具", "Harness": "+ 一道完整的菜谱"},
    "编程": {"Runtime": "操作系统", "Framework": "+ 标准库 + Web 框架", "Harness": "+ 一个完整的 CMS 产品"},
    "装修": {"Runtime": "电路、水管、墙体", "Framework": "+ 装修材料和工具", "Harness": "+ 一套精装修方案"},
}


def classify(project_traits: dict[str, bool]) -> str:
    """根据「控制流你写多少」判断一个项目落在哪一层。"""

    if project_traits.get("gives_complete_agent"):
        return "Harness"
    if project_traits.get("provides_building_blocks"):
        return "Framework"
    if project_traits.get("only_execution_engine"):
        return "Runtime"
    return "未知"


def main() -> None:
    print("=== 三层抽象：控制流谁来负责 ===")
    for layer in LAYERS:
        print(f"[{layer.name:9}] 你做：{layer.you_do:16} | 控制流：{layer.control_flow}")
        print(f"{'':13}代表：{'、'.join(layer.examples)}")

    print("\n=== 主流项目定位 ===")
    for tier, projects in POSITIONING:
        print(f"{tier:22}: {'、'.join(projects)}")

    print("\n=== 工程类比 ===")
    for scene, mapping in ANALOGIES.items():
        parts = "  ".join(f"{k}={v}" for k, v in mapping.items())
        print(f"{scene}: {parts}")

    print("\n=== 选型自测：这三个不在同一层，问『选哪个』本身就错了 ===")
    samples = {
        "DeepAgents": {"gives_complete_agent": True},
        "LangChain": {"provides_building_blocks": True},
        "LangGraph": {"only_execution_engine": True},
    }
    for name, traits in samples.items():
        print(f"  {name:12} -> {classify(traits)} 层")


if __name__ == "__main__":
    main()
