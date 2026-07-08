"""三方案成本对比脚本 —— 对应第 35 篇「四、三种方案的成本对比」。

按月度调用量分档，对比 LiteLLM 自部署 / PortKey SaaS / 自建 三种方案的年度总成本，
并给出决策门槛（<1000万→LiteLLM，1000万-1亿→LiteLLM/PortKey，>1亿→自建）。

纯标准库：
    python3 35_gateway_implementation/cost_comparison.py
"""

from __future__ import annotations

# 文章「四」三档数据（USD）。gateway_month=月度 Gateway 成本区间，year_total=一年总成本区间。
TIERS = {
    "100万次/月(中小)": {
        "LiteLLM自部署": {"gw_month": (50, 50), "year_total": (600, 600), "verdict": "✅ 推荐"},
        "PortKey SaaS": {"gw_month": (300, 500), "year_total": (5000, 5000), "verdict": "慎用"},
        "自建": {"gw_month": (200, 500), "year_total": (50_000, 100_000), "verdict": "❌ 过度投入"},
    },
    "1000万次/月(中大型)": {
        "LiteLLM自部署": {"gw_month": (200, 500), "year_total": (5000, 5000), "verdict": "✅ 主流选择"},
        "PortKey SaaS": {"gw_month": (2000, 5000), "year_total": (30_000, 60_000), "verdict": "✅ 数据可出境"},
        "自建": {"gw_month": (1000, 2000), "year_total": (80_000, 150_000), "verdict": "看长期规划"},
    },
    "1亿次/月(大型)": {
        "LiteLLM自部署": {"gw_month": (2000, 5000), "year_total": (30_000, 60_000), "verdict": "边界"},
        "PortKey SaaS": {"gw_month": (20_000, 20_000), "year_total": (250_000, 250_000), "verdict": "⚠️ 成本过高"},
        "自建": {"gw_month": (3000, 8000), "year_total": (150_000, 150_000), "verdict": "✅ 经济合理"},
    },
}

DECISION = [
    ("< 1000 万次/月", "LiteLLM"),
    ("1000 万 - 1 亿次/月", "LiteLLM 仍可用，PortKey 看预算"),
    ("> 1 亿次/月", "自建经济上合理"),
]


def _fmt(rng: tuple[int, int]) -> str:
    lo, hi = rng
    return f"${lo:,}" if lo == hi else f"${lo:,}-{hi:,}"


def main() -> None:
    print("=== 三方案成本对比（按月度调用量分档）===\n")
    for tier, plans in TIERS.items():
        print(f"【{tier}】")
        print(f"  {'方案':16}{'月度Gateway':>18}{'年度总成本':>20}   结论")
        for plan, d in plans.items():
            print(f"  {plan:16}{_fmt(d['gw_month']):>18}{_fmt(d['year_total']):>20}   {d['verdict']}")
        print()

    print("=== 决策门槛 ===")
    for scale, rec in DECISION:
        print(f"  {scale:22} -> {rec}")

    print("\n混合方案（大企业真实形态）：LiteLLM 主路由(90% 自部署省成本) + 10% 关键流量走 PortKey(语义缓存+深度可观测)")
    print("自建门槛：月成本 >$10万 或 调用 >1亿/月 时，自建一次性 10-20 万工程投入几个月回本。")


if __name__ == "__main__":
    main()
