"""6 种典型项目类型的标准选型方案。

对应文章第 33 篇「二、6 种典型项目的标准选型方案」。

把每种项目的特征喂进决策树 CLI，验证「文章给的推荐」= 「决策树跑出来的推荐」。
纯标准库：
    python3 33_framework_decision/project_recommendations.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from decision_tree_cli import decide  # noqa: E402

# 6 种项目：特征 + 文章推荐 + 架构示意 + 理由。
PROJECTS = [
    {
        "type": "客服 / 工单系统",
        "traits": {"high_risk": "no", "core": "orchestration", "complex_state": "yes"},
        "recommend": "LangGraph",
        "arch": "classify → KB子图/订单子图/投诉子图(含HITL)/闲聊",
        "why": "多意图 conditional_edges 可控；人工升级=interrupt() 原生；会话持久化 Checkpoint",
    },
    {
        "type": "内容生产团队",
        "traits": {"high_risk": "no", "core": "collaboration", "stage": "demo"},
        "recommend": "CrewAI",
        "arch": "Sequential: 研究员→大纲师→写手→编辑→校对",
        "why": "角色协作天然契合；上手快立即出活；无高危操作不需 HITL",
    },
    {
        "type": "数据分析 Agent(Text-to-SQL)",
        "traits": {"high_risk": "yes", "flow": "determinate", "gcp": "no"},
        "recommend": "LangGraph",
        "arch": "parse→generate_sql→validate→execute→chart，invalid 时 refine_sql 循环",
        "why": "SQL 生成→执行→修复是循环模式；大查询要持久化；改数据 SQL 需 HITL",
    },
    {
        "type": "代码助手(Code Agent)",
        "traits": {"high_risk": "yes", "flow": "open", "gcp": "no"},
        "recommend": "LangGraph + DeepAgents 子任务",
        "arch": "LangGraph 骨架 + deep_agent 做多文件理解 + interrupt human_review",
        "why": "主流程用 LangGraph；长任务深度理解用 DeepAgents 虚拟文件系统；改代码必 HITL",
    },
    {
        "type": "企业 OA / 流程自动化",
        "traits": {"high_risk": "yes", "flow": "determinate", "gcp": "yes"},
        "recommend": "ADK",
        "arch": "Plugins(审计/合规/成本) + Workflow: 提交→并行验证→审批(HITL)→执行",
        "why": "Workflow 覆盖场景；Plugin 加审计安全；Evaluation 满足合规",
    },
    {
        "type": "研究 / 调研 Agent(深度报告)",
        "traits": {"high_risk": "no", "core": "collaboration", "stage": "production"},
        "recommend": "DeepAgents(Harness) + 可选 ADK 外层",
        "arch": "ADK(评测+Plugin) └ 主Agent 调 DeepAgents └ task() 委托多研究子Agent",
        "why": "长任务=Context Engineering 主场；三大模式契合；有评测需求外套 ADK",
    },
]


def main() -> None:
    print("=== 6 种典型项目标准选型方案 ===\n")
    names = ("LangGraph", "CrewAI", "ADK", "DeepAgents")
    for p in PROJECTS:
        derived, _ = decide(p["traits"])
        # 决策树推导与文章推荐共享至少一个框架名即视为同族（子任务/外层后缀可不同）。
        derived_set = {n for n in names if n in derived}
        rec_set = {n for n in names if n in p["recommend"]}
        match = bool(derived_set & rec_set)
        flag = "✓一致" if match else f"⚠决策树={derived}"
        print(f"[{p['type']}]")
        print(f"  推荐：{p['recommend']}  （决策树推导：{derived} {flag}）")
        print(f"  架构：{p['arch']}")
        print(f"  理由：{p['why']}\n")


if __name__ == "__main__":
    main()
