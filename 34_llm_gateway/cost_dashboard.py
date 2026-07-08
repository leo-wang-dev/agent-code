"""成本统计仪表盘 —— 对应第 34 篇「能力 6：成本可视化」。

从 Gateway 的调用日志聚合出：按团队/模型的成本拆解、占比、异常告警。
纯标准库、确定性 mock 数据：
    python3 34_llm_gateway/cost_dashboard.py
"""

from __future__ import annotations

from collections import defaultdict

# 模拟一段时间的 Gateway usage_log（形态对齐 self_built_gateway.USAGE_LOG）。
SAMPLE_USAGE = [
    {"gateway_key": "gw-sales-team", "owner": "sales", "model": "gpt-4o", "prompt_tokens": 1250, "completion_tokens": 380},
    {"gateway_key": "gw-sales-team", "owner": "sales", "model": "gpt-4o", "prompt_tokens": 900, "completion_tokens": 300},
    {"gateway_key": "gw-support", "owner": "support", "model": "claude", "prompt_tokens": 700, "completion_tokens": 220},
    {"gateway_key": "gw-report", "owner": "report", "model": "gemini-1.5-pro", "prompt_tokens": 5200, "completion_tokens": 1800},
    {"gateway_key": "gw-report", "owner": "report", "model": "gemini-1.5-pro", "prompt_tokens": 48000, "completion_tokens": 6000},  # 异常
]

# 各模型每 1k token 单价（USD，示意值）。
PRICE_PER_1K = {"gpt-4o": 0.005, "claude": 0.004, "gemini-1.5-pro": 0.0035, "gpt-4o-mini": 0.0004}
ALERT_TOKEN_THRESHOLD = 50_000  # 单次调用 token 超过此值 -> 异常成本告警


def cost_of(row: dict) -> float:
    tokens = row["prompt_tokens"] + row["completion_tokens"]
    return round(tokens / 1000 * PRICE_PER_1K.get(row["model"], 0.005), 6)


def build_dashboard(usage: list[dict]) -> dict:
    by_team: dict[str, float] = defaultdict(float)
    by_model: dict[str, float] = defaultdict(float)
    alerts: list[str] = []
    total = 0.0
    for row in usage:
        cost = cost_of(row)
        total += cost
        by_team[row["owner"]] += cost
        by_model[row["model"]] += cost
        if row["prompt_tokens"] + row["completion_tokens"] > ALERT_TOKEN_THRESHOLD:
            alerts.append(f"[异常成本] key={row['gateway_key']} 单次 token={row['prompt_tokens']+row['completion_tokens']}")
    return {
        "total_usd": round(total, 4),
        "by_team": {k: round(v, 4) for k, v in by_team.items()},
        "by_model": {k: round(v, 4) for k, v in by_model.items()},
        "model_share": {k: round(v / total, 2) for k, v in by_model.items()} if total else {},
        "alerts": alerts,
    }


def _bar(pct: float, width: int = 20) -> str:
    filled = int(pct * width)
    return "█" * filled + "·" * (width - filled)


def main() -> None:
    dash = build_dashboard(SAMPLE_USAGE)
    print("=== Gateway 成本仪表盘 ===\n")
    print(f"总成本：${dash['total_usd']}\n")
    print("按团队拆解：")
    for team, cost in sorted(dash["by_team"].items(), key=lambda x: -x[1]):
        print(f"  {team:10} ${cost}")
    print("\n按模型占比：")
    for model, share in sorted(dash["model_share"].items(), key=lambda x: -x[1]):
        print(f"  {model:16} {_bar(share)} {share:.0%}  (${dash['by_model'][model]})")
    print("\n异常告警：")
    for alert in dash["alerts"] or ["（无）"]:
        print("  ", alert)


if __name__ == "__main__":
    main()
