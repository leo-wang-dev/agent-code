"""嵌套组合 —— 工业级标准结构（Delegation 内挂 Sequential/Parallel/Loop）。

对应文章第五节"嵌套组合：真实工业级用法"：

    [root_agent (Delegation)]
       ├── intent "search" -> [SequentialAgent: research_pipeline]
       ├── intent "audit"  -> [ParallelAgent: multi_check]
       └── intent "draft"  -> [LoopAgent: self_refine]

主流程用 Delegation 做意图路由，每个意图挂一个 Sequential/Parallel/Loop 子流程。
本脚本用确定性 mock 复刻这套嵌套结构，并对三类输入各跑一遍，打印控制流树。
"""

from __future__ import annotations

import sys

try:  # google-adk 导入 try/except 保护
    from google.adk.workflows import (  # noqa: F401
        SequentialAgent,
        ParallelAgent,
        LoopAgent,
    )

    HAS_ADK = True
except ImportError:
    HAS_ADK = False


def run_sequential(names: list[str], log: list) -> str:
    log.append("  └─ SequentialAgent: research_pipeline")
    for n in names:
        log.append(f"       -> {n}")
    return "研究流水线产出：综合报告"


def run_parallel(names: list[str], log: list) -> str:
    log.append("  └─ ParallelAgent: multi_check")
    for n in names:
        log.append(f"       // {n}")
    return "并行审核产出：三方评审全部通过"


def run_loop(names: list[str], log: list) -> str:
    log.append("  └─ LoopAgent: self_refine (max_iterations=3)")
    for it in range(1, 4):
        log.append(f"       轮{it}: {' -> '.join(names)}")
    return "自我改进产出：终稿（第 3 轮达标）"


# Delegation 路由表：intent -> 子流程
SUBFLOWS = {
    "search": lambda log: run_sequential(
        ["search_agent", "rerank_agent", "synthesize_agent"], log),
    "audit": lambda log: run_parallel(
        ["compliance_agent", "security_agent", "pricing_agent"], log),
    "draft": lambda log: run_loop(
        ["writer_agent", "critic_agent", "refine_agent"], log),
}


def classify(message: str) -> str:
    if any(k in message for k in ("查", "搜", "search", "资料")):
        return "search"
    if any(k in message for k in ("审核", "合规", "audit", "风险")):
        return "audit"
    return "draft"


def main() -> int:
    if not HAS_ADK:
        print("[提示] 未检测到 google-adk，使用确定性 mock 演示嵌套组合工业级模式。")
        print("       安装： pip install google-adk")
        print("-" * 60)

    inputs = [
        "帮我查一下 ADK 的资料",
        "对这份合同做合规审核",
        "帮我起草一封道歉信",
    ]
    for msg in inputs:
        intent = classify(msg)
        log: list[str] = [f"[root_agent (Delegation)] intent={intent!r}"]
        result = SUBFLOWS[intent](log)
        print(f"用户: {msg}")
        print("\n".join(log))
        print(f"  => {result}\n")

    print("结论：Delegation 做意图路由 + 每意图挂一个 Sequential/Parallel/Loop = ADK 工业级标准结构。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
