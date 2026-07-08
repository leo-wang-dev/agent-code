"""Pipeline 拓扑：任务按固定流程流转。

对应文章第 08 篇「三、三种经典拓扑 · Pipeline」。

检索 → 提纲 → 写作 → 审稿，阶段明确、流程稳定的业务最适合。
复用 src/agent_code/multi_agent.py 的 Pipeline，每个阶段是一个单 Agent（函数替身）。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_code.multi_agent import Pipeline


def build_article_pipeline() -> Pipeline:
    stages = [
        ("researcher", lambda text: f"[资料] 关于「{text}」收集到 3 条来源"),
        ("outliner", lambda text: f"[提纲] 基于({text}) 生成 3 段结构"),
        ("writer", lambda text: f"[初稿] 依据({text}) 写成 800 字"),
        ("reviewer", lambda text: f"[终稿] 审校通过：{text}"),
    ]
    return Pipeline(stages)


def main() -> None:
    pipeline = build_article_pipeline()
    trace = pipeline.run("多 Agent 协作")
    print("Pipeline 逐阶段输出:")
    for name, output in trace.items():
        print(f"  {name}: {output}")


if __name__ == "__main__":
    main()
