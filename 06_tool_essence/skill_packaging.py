"""产物：Skill 封装（对应文章 §四 "Skill 比 Tool 高一层"）。

Tool 是动词（查天气、发邮件），Skill 是一件完整工作（写周报、处理退款、生成投放报告）。
Skill = 把一组 Tool + 一段引导 Prompt + 一些资源文件，打包成一个能力单元，降低模型
每次临场组合工具的概率。

判据：单步动作 → Tool；稳定流程 / 多工具组合 / 固定资源模板 → 抽成 Skill。

本文件用仓库 Skill + default_registry 定义一个"退款处理"Skill，并 build_context 出模型
拿到的完整上下文（指令 + 该 Skill 允许用的工具 schema + 资源）。

    python3 skill_packaging.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_code.tool_essence import Skill, default_registry


def main() -> None:
    registry = default_registry()

    # 一件完整工作："处理退款"，它绑定了固定流程、工具子集和模板资源。
    refund_skill = Skill(
        name="handle_refund",
        instructions=(
            "处理客户退款的固定流程：\n"
            "1. 先用 calculate 核对可退金额（订单金额 - 已用部分）；\n"
            "2. 再用 create_refund 提交退款，必须带 idempotency_key 防重复；\n"
            "3. 高危写操作需人工审批后才执行。"
        ),
        tools=("calculate", "create_refund"),   # 只暴露这件工作需要的工具子集
        resources={"refund_policy": "7 天内未拆封可全额退款；运费不退。"},
    )

    context = refund_skill.build_context(registry)

    print(f"Skill: {context['skill']}\n")
    print("① 引导 Prompt（把稳定流程固化下来）")
    for line in context["instructions"].splitlines():
        print(f"    {line}")

    print("\n② 该 Skill 暴露的工具子集（不是全量工具，收窄组合空间）")
    for schema in context["tool_schemas"]:
        fn = schema["function"]
        print(f"    - {fn['name']}: {fn['description']}")

    print("\n③ 绑定的资源")
    for k, v in context["resources"].items():
        print(f"    {k} = {v}")

    print("\nTool 是动词，Skill 是一件完整工作。稳定流程就该抽成 Skill，")
    print("而不是每次都让模型临场把散工具拼成一套流程（成功率低）。")
    # 完整上下文也可整体序列化交给模型：
    _ = json.dumps(context, ensure_ascii=False)


if __name__ == "__main__":
    main()
