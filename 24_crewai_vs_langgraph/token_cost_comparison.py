"""Token 成本对照 —— LangGraph vs CrewAI（纯 stdlib，零依赖）。

成本差异来源：
  - CrewAI 每个 Agent 启动都注入 role+goal+backstory（每段 50-200 token），
    单次 kickoff 常多花 500-1000 token；每个 Agent 是一次 LLM 调用。
  - LangGraph 简单意图纯 Python 走通（0 token），复杂意图只在必要节点调 LLM。

数字为建模估算（对齐文章口径），用于直观展示量级差异；真实值随 prompt/模型变化。

无需任何第三方依赖，直接 python3 运行。
"""
from __future__ import annotations

# 单价（示例：每百万 token 美元，输入口径），真实以供应商价目为准
PRICE_PER_1M = 2.5

# 每种意图的建模 token 用量（prompt+completion 合计）
# CrewAI：每 Agent 角色注入 ~600 + 任务 ~300；LangGraph：仅必要节点
TOKENS = {
    #             LangGraph   CrewAI
    "order":     {"lg": 0,    "cr": 900},    # LG 纯 Python；CrewAI 1 agent
    "chitchat":  {"lg": 300,  "cr": 900},    # LG 1 次轻量 LLM；CrewAI 1 agent
    "kb":        {"lg": 1800, "cr": 3200},   # LG retrieve/rerank/synthesize；CrewAI 2 agent
    "complaint": {"lg": 200,  "cr": 1800},   # LG 主要是工具+HITL；CrewAI 2 agent
}

# 一天的意图分布（次数）
DAILY_MIX = {"order": 4000, "chitchat": 3000, "kb": 2000, "complaint": 1000}


def fmt_usd(tokens: int) -> str:
    return f"${tokens / 1_000_000 * PRICE_PER_1M:,.2f}"


def main() -> None:
    print(f"单价假设：${PRICE_PER_1M}/1M token；日请求量：{sum(DAILY_MIX.values()):,} 次\n")
    print(f"{'意图':<10}{'次数':>8}{'LG token':>12}{'CrewAI token':>14}{'省比':>8}")
    print("-" * 54)

    lg_total = cr_total = 0
    for intent, count in DAILY_MIX.items():
        lg = TOKENS[intent]["lg"] * count
        cr = TOKENS[intent]["cr"] * count
        lg_total += lg
        cr_total += cr
        save = (cr - lg) / cr * 100 if cr else 0
        print(f"{intent:<10}{count:>8,}{lg:>12,}{cr:>14,}{save:>7.0f}%")

    print("-" * 54)
    print(f"{'合计':<10}{sum(DAILY_MIX.values()):>8,}{lg_total:>12,}{cr_total:>14,}"
          f"{(cr_total - lg_total) / cr_total * 100:>7.0f}%")
    print()
    print(f"日成本：LangGraph {fmt_usd(lg_total)}  vs  CrewAI {fmt_usd(cr_total)}")
    print(f"月成本(×30)：LangGraph {fmt_usd(lg_total*30)}  vs  CrewAI {fmt_usd(cr_total*30)}")
    agg = (cr_total - lg_total) / cr_total * 100
    print(f"\n结论：本工作负载下 LangGraph 整体 token 比 CrewAI 少约 {agg:.0f}%。")
    print("     LLM 重的意图(kb)约省 44%，正落在文章'省 30-50%'区间；")
    print("     简单意图(order/chitchat)因 LangGraph 纯 Python 零 token 省得更多，")
    print("     所以聚合比例随流量结构上浮——订单/闲聊占比越高，省得越多。")
    print("原因：简单意图 LangGraph 纯 Python 零 token，CrewAI 每个 Agent 仍注入完整角色 prompt。")


if __name__ == "__main__":
    main()
