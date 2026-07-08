"""框架映射表：每个框架/工具主要落在哪一层。

对应文章第 09 篇「四、框架应该放在哪一层」。

避免一个常见误区：「我用了 LangChain，所以我有完整 Agent 系统了。」
没有——大多数框架只覆盖 L1-L4，L6 安全与 L7 评估仍要自己建设。
复用 src/agent_code/seven_layer.py 的 FRAMEWORK_MAPPING / LAYERS。
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_code.seven_layer import FRAMEWORK_MAPPING, LAYERS


def main() -> None:
    layer_names = {layer.id: layer.name for layer in LAYERS}

    print("=== 框架 -> 所在层 ===")
    for framework, layers in FRAMEWORK_MAPPING.items():
        pretty = ", ".join(f"{lid} {layer_names[lid]}" for lid in layers)
        print(f"  {framework:24s} -> {pretty}")

    print("\n=== 反向：每层有哪些框架覆盖 ===")
    coverage: dict[str, list[str]] = defaultdict(list)
    for framework, layers in FRAMEWORK_MAPPING.items():
        for lid in layers:
            coverage[lid].append(framework)
    for layer in LAYERS:
        frameworks = coverage.get(layer.id, [])
        note = ", ".join(frameworks) if frameworks else "（示例映射未覆盖，需自建）"
        print(f"  {layer.id} {layer.name}: {note}")

    print("\n提醒：L6 安全治理 / L7 评估反馈 常被框架略过，是玩具级和工业级的分水岭。")


if __name__ == "__main__":
    main()
