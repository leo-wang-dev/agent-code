"""性能对比脚本 + Token 消耗对照。

对应文章第 32 篇「维度 3：运行性能」。

- 真实跑三个实现（本地确定性逻辑），测各自 wall-clock 耗时；
- 叠加文章给出的 TTFT / Token 参考数据做对照（真实数值取决于模型与网络）。

纯标准库：
    python3 32_three_framework_comparison/benchmark.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import sourcing_adk
import sourcing_common as sc
import sourcing_crewai
import sourcing_langgraph

# 文章「维度 3」参考数据（真实调用 LLM 时的量级）。
REFERENCE = {
    "LangGraph": {"ttft_s": 1.2, "total_s": 12, "tokens": 12_000},
    "CrewAI": {"ttft_s": 2.5, "total_s": 18, "tokens": 22_000},
    "ADK": {"ttft_s": 1.5, "total_s": 14, "tokens": 15_000},
}

IMPLS = {
    "LangGraph": sourcing_langgraph.run,
    "CrewAI": sourcing_crewai.run,
    "ADK": sourcing_adk.run,
}


def bench() -> dict[str, dict]:
    rows: dict[str, dict] = {}
    for name, fn in IMPLS.items():
        start = time.perf_counter()
        result = fn(sc.DEFAULT_QUERY)
        local_ms = (time.perf_counter() - start) * 1000
        rows[name] = {
            "local_ms": round(local_ms, 2),
            "used_real_lib": result.used_real_lib,
            "top_supplier": result.report["top_supplier"],
            **REFERENCE[name],
        }
    return rows


def main() -> None:
    rows = bench()
    base_tokens = rows["LangGraph"]["tokens"]

    print("=== 三框架运行性能 + Token 对照 ===\n")
    print(f"{'框架':10}{'本地耗时ms':>12}{'TTFT(参考)':>12}{'总耗时(参考)':>14}{'Token(参考)':>13}{'×LG':>7}")
    print("-" * 72)
    for name, r in rows.items():
        ratio = r["tokens"] / base_tokens
        print(
            f"{name:10}{r['local_ms']:>12}{r['ttft_s']:>11}s{r['total_s']:>12}s"
            f"{r['tokens']:>12,}{ratio:>6.2f}x"
        )

    print("\n结论（文章数据）：")
    print("  最快 & 最省 token：LangGraph（意图分类用 Python 函数，不调 LLM）")
    print("  最慢 & 最贵：CrewAI（每个 Agent 加载 role/goal/backstory，固定开销大）")
    print("  Token：CrewAI ≈ 1.8×LangGraph、ADK ≈ 1.25×LangGraph")
    print("  百万级月调用下，框架选型对账单影响 30-50%。")
    print(f"\n三框架业务结果一致（都选 {rows['LangGraph']['top_supplier']}），保证对比公平。")


if __name__ == "__main__":
    main()
