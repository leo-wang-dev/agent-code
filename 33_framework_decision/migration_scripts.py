"""三种迁移路径的工程示例脚本。

对应文章第 33 篇「四、选错框架后的迁移策略」：
  迁移 1  CrewAI → LangGraph            难度中，工程量 40-60%
  迁移 2  LangGraph → ADK               难度中偏高，工程量 50-70%
  迁移 3  任意框架 → 加 DeepAgents 子任务  难度低，工程量 5-10%

这里不真正跨框架搬运代码（那依赖具体项目），而是给出：
  - 每条迁移的「映射表」（源概念 -> 目标概念）；
  - 一个可运行的自动化「迁移清单生成器」，输出待办 + 工程量估算。

纯标准库：
    python3 33_framework_decision/migration_scripts.py
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Migration:
    name: str
    trigger: str
    difficulty: str
    effort_pct: str
    concept_map: list[tuple[str, str]]
    checklist: list[str]


MIGRATIONS = {
    "crewai_to_langgraph": Migration(
        name="CrewAI → LangGraph",
        trigger="业务复杂度上升 / 需要 HITL / 需要节点级持久化",
        difficulty="中等",
        effort_pct="40-60%",
        concept_map=[
            ("Task.description", "Node 的 system prompt + instruction"),
            ("Sequential 流程", "add_edge 串联"),
            ("Hierarchical", "自写 orchestrator 节点(条件路由)"),
            ("CrewAI Memory", "State + Checkpoint 设计"),
        ],
        checklist=[
            "把每个 Task 翻译成一个图节点",
            "Sequential 用 add_edge 串起来",
            "Hierarchical 改写成 orchestrator 条件路由节点",
            "设计 State TypedDict + 选 Checkpointer(Sqlite/Postgres)",
            "在高危节点插 interrupt() 做 HITL",
        ],
    ),
    "langgraph_to_adk": Migration(
        name="LangGraph → ADK",
        trigger="团队扩大 / 需要工业级评测 / 需要全局 Plugin / 接 GCP",
        difficulty="中等偏高",
        effort_pct="50-70%",
        concept_map=[
            ("State + Node", "Agent + Workflow"),
            ("Checkpoint", "Event Sourcing"),
            ("工具函数", "用 ToolContext 重写"),
            ("横切逻辑", "Plugin 链"),
            ("(无)", "新增 Evaluation 套件"),
        ],
        checklist=[
            "State/Node 拆成 Agent + Workflow(Sequential/Loop/Parallel)",
            "Checkpoint 概念转 Event Sourcing",
            "工具函数改造以使用 ToolContext",
            "加 Plugin 链(日志/安全/成本)做横切",
            "补 Evaluation 用例满足合规",
        ],
    ),
    "add_deepagents_subtask": Migration(
        name="任意框架 → 加 DeepAgents 子任务",
        trigger="发现某些子任务是长任务(步骤多、Context 管理难)",
        difficulty="低",
        effort_pct="5-10%",
        concept_map=[
            ("痛点节点(易跑偏)", "create_deep_agent(...) 调用"),
            ("其余主流程", "不动"),
        ],
        checklist=[
            "定位步骤多/易跑偏的痛点节点",
            "把该节点实现替换成 create_deep_agent(...)",
            "配置该子任务的工具 + system prompt",
            "主流程其他部分保持不变",
        ],
    ),
}


def generate_plan(migration_key: str) -> str:
    m = MIGRATIONS[migration_key]
    lines = [
        f"# 迁移方案：{m.name}",
        f"触发条件：{m.trigger}",
        f"难度：{m.difficulty}    预估工程量：原代码量的 {m.effort_pct}",
        "",
        "## 概念映射",
    ]
    lines += [f"  {src:22} ->  {dst}" for src, dst in m.concept_map]
    lines += ["", "## 迁移清单"]
    lines += [f"  [ ] {i+1}. {item}" for i, item in enumerate(m.checklist)]
    return "\n".join(lines)


def main() -> None:
    for key in MIGRATIONS:
        print(generate_plan(key))
        print("\n" + "-" * 60 + "\n")
    print("迁移哲学：迁移成本随复杂度增长，初期选型尽量准；不确定时倾向 LangGraph")
    print("（复杂度上限最高，且能覆盖大部分 CrewAI 场景；反向迁移成本远高于正向）。")
    print("解耦原则：工具=普通函数+类型标注，业务=纯函数，框架 API 只在最外层薄层 -> 迁移成本降 60-80%")


if __name__ == "__main__":
    main()
