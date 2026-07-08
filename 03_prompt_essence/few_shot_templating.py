"""产物：Few-shot 的本质（对应文章 §三）。

Few-shot 不是"学习"——推理阶段参数不变。那几个例子真正做的，是通过模式匹配把模型
输出分布向你给的格式拉齐。你不是在教它，是给它一张模板。

本文件复现文章里的抽取任务：无示例 vs 2-shot，并用一个"格式拉齐"启发式（离线、
确定性）模拟两者输出的稳定性差异；再演示 few-shot 的三条工程要点。

    python3 few_shot_templating.py
"""

from __future__ import annotations

import json


EXAMPLES = [
    ("王芳担任字节跳动的高级工程师。", {"name": "王芳", "position": "高级工程师"}),
    ("李娜是腾讯的设计总监。", {"name": "李娜", "position": "设计总监"}),
]

TARGET = "张伟是上海银行的产品经理。"


def build_few_shot_prompt(examples, target) -> str:
    lines = ["从一段话里提取姓名和职位，只输出 JSON。", "", "示例："]
    for inp, out in examples:
        lines.append(f"输入：{inp}")
        lines.append(f"输出：{json.dumps(out, ensure_ascii=False)}")
    lines += ["", f"输入：{target}", "输出："]
    return "\n".join(lines)


def mock_without_fewshot(target) -> str:
    # 无模板：格式不稳，掺杂废话（真实模型的典型退化）。
    name, position = "张伟", "产品经理"
    return f"在这段话中，人名是{name}，职位是{position}。"


def mock_with_fewshot(target) -> str:
    # 有模板：被前面的输入-输出对拉齐，几乎必然吐这个 JSON。
    return json.dumps({"name": "张伟", "position": "产品经理"}, ensure_ascii=False)


def is_machine_parsable(output: str) -> bool:
    try:
        json.loads(output)
        return True
    except json.JSONDecodeError:
        return False


def main() -> None:
    print("① 2-shot Prompt（本质是一个高级填空游戏）")
    print("-" * 56)
    print(build_few_shot_prompt(EXAMPLES, TARGET))

    print("\n② 输出对比")
    zero = mock_without_fewshot(TARGET)
    few = mock_with_fewshot(TARGET)
    print(f"    无 few-shot → {zero}")
    print(f"      业务可解析? {is_machine_parsable(zero)}  （多废话、格式不稳）")
    print(f"    2-shot      → {few}")
    print(f"      业务可解析? {is_machine_parsable(few)}  （被模板拉齐）")

    print("\n③ 工程三要点")
    print("    - 多样性 > 数量：3 个覆盖不同情况，好过 10 个雷同示例")
    print("    - 示例也吃 token：能 2-shot 就别 5-shot")
    print("    - 顺序有影响：反例放前、正例放后，让'好格式'成为最易抄的那一个")


if __name__ == "__main__":
    main()
