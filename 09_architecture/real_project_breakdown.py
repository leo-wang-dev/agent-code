"""真实项目拆解示例：把一个客服 Agent 按 7 层落到具体设计。

对应文章第 09 篇「六、收束」——Agent 是一个 7 层系统，
前 5 层决定能不能跑，后 2 层决定敢不敢上线。

以「企业客服 Agent」为例，逐层给出真实工程决策，
复用 src/agent_code/seven_layer.py 的 sample_customer_service_breakdown / LAYERS。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_code.seven_layer import LAYERS, sample_customer_service_breakdown


def main() -> None:
    breakdown = sample_customer_service_breakdown()
    print("真实项目拆解：企业客服 Agent，按 L1-L7 落地\n")
    for layer in LAYERS:
        design = breakdown.get(layer.id, "（该层本项目暂缺，需补齐）")
        print(f"  {layer.id} {layer.name}")
        print(f"      设计: {design}\n")

    print("检验：能数清每个能力属于哪一层，出问题时才不会瞎猜。")


if __name__ == "__main__":
    main()
