"""故障点速查表：出问题时先定位层级，而不是先猜原因。

对应文章第 09 篇「五、出问题时怎么按层排查」。

没有架构图，所有排查都是瞎猜。这里把「症状 → 该看哪一层 → 先查什么」
做成可查询的速查表。复用 src/agent_code/seven_layer.py 的
printable_fault_table / diagnose。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_code.seven_layer import diagnose, printable_fault_table


SYMPTOMS = [
    "接口 rate limit 429 超时",
    "回答引用了 wrong answer 的资料",
    "模型选了 wrong tool",
    "循环 infinite loop 停不下来",
    "流式 stream cut 中断",
    "用户看到了 private data",
    "prompt changed 后效果说不清",
]


def main() -> None:
    print("=== 故障点速查表（按层）===")
    print(printable_fault_table())

    print("\n=== 症状 -> 首查层级 ===")
    for symptom in SYMPTOMS:
        matches = diagnose(symptom)
        for match in matches:
            print(f"  「{symptom}」 -> {match['layer']} {match['name']}: {match['action']}")


if __name__ == "__main__":
    main()
