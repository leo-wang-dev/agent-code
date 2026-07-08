"""产物：CoT 不是万能药（对应文章 §五）。

Chain-of-Thought 在数学 / 多步推理 / 逻辑判断上确实提准，但有两个被掩盖的代价：
  代价一：token 成本翻倍——completion_tokens 轻松 ×2~3，月账单直接乘 2；
  代价二：简单任务上反而有害——模型"想太多"，编推理把自己说服跑偏，准确率不升反降。

本文件用仓库 estimate_cot_cost 量化"代价一"，并用一组任务演示"该不该上 CoT"的取舍。

    python3 cot_tradeoff.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_code.prompt_essence import estimate_cot_cost


# (任务, 问题, 直接答案, CoT 推理过程, 该不该上 CoT)
CASES = [
    (
        "多步数学（推理任务）",
        "一件商品原价 200，先打 8 折再减 20，最后多少？",
        "140",
        "原价 200，8 折是 200×0.8=160，再减 20 得 140，所以最终价格是 140 元。",
        True,
    ),
    (
        "情感分类（简单任务）",
        "判断这句话情感：这家店服务态度太差了。",
        "负面",
        "首先分析用词，'太差了'带有明显负面色彩，通常表达不满，因此判断为负面情感。",
        False,
    ),
    (
        "字段抽取（简单任务）",
        "从'张伟是产品经理'里抽取姓名。",
        "张伟",
        "这句话的主语是张伟，谓语说明他的职位，所以要抽取的姓名字段应当是张伟。",
        False,
    ),
]


def main() -> None:
    print("① 代价一：token 成本（CoT 让 completion 翻倍）")
    print(f"    {'任务':<20}{'直接':>6}{'CoT':>6}{'多花':>6}{'倍数':>7}")
    for name, q, a, reasoning, _ in CASES:
        c = estimate_cot_cost(q, a, reasoning)
        ratio = c["cot_tokens"] / max(1, c["direct_tokens"])
        print(f"    {name:<20}{c['direct_tokens']:>6}{c['cot_tokens']:>6}{c['extra_tokens']:>6}{ratio:>6.1f}x")

    print("\n② 代价二：简单任务该不该上 CoT")
    for name, q, a, reasoning, should in CASES:
        verdict = "值得上 CoT" if should else "不要上 CoT（会想太多、可能跑偏）"
        print(f"    {name:<20} → {verdict}")

    print("\n③ 取舍原则")
    print("    - 复杂/多步：上 CoT，但把思考塞进 tool_calls 内部字段，不暴露给用户")
    print("    - 简单分类/抽取/翻译：直接结构化输出，不加 CoT")
    print("    - 成本敏感：小模型 + 不加 CoT，而不是大模型 + CoT")


if __name__ == "__main__":
    main()
