"""异常成本告警 demo。

对应文章第七节"用途 3：成本异常的早期发现"。某个虚拟 Key 1 小时消耗了平时
一周的 Token —— 告警必须在 5 分钟内触发（可能是 Prompt Injection / Bug 死循环 /
Key 被盗）。及时拉闸能避免几万到几十万损失。

检测思路（零依赖）：
  1. 绝对阈值：单位时间成本超硬上限直接告警；
  2. 基线倍数：当前速率 vs 该 Key 历史基线，超 N 倍告警（捕捉相对异常）；
  3. 长会话监控：单会话轮数异常（100+ 轮）单列告警。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class KeyUsage:
    key_id: str
    cost_last_hour: float          # 最近 1 小时花费（美元）
    baseline_hourly: float         # 历史每小时基线
    max_session_turns: int         # 该 Key 下最长会话轮数


# 告警规则参数
ABS_HOURLY_LIMIT = 50.0    # 单 Key 每小时硬上限（美元）
BASELINE_MULTIPLIER = 10.0  # 超基线 10 倍视为异常
LONG_SESSION_TURNS = 100    # 超长会话轮数阈值


def check_key(usage: KeyUsage) -> list[str]:
    alerts: list[str] = []
    if usage.cost_last_hour > ABS_HOURLY_LIMIT:
        alerts.append(
            f"绝对超限：${usage.cost_last_hour:.1f}/h > 硬上限 ${ABS_HOURLY_LIMIT:.0f}/h"
        )
    if usage.baseline_hourly > 0 and usage.cost_last_hour > usage.baseline_hourly * BASELINE_MULTIPLIER:
        ratio = usage.cost_last_hour / usage.baseline_hourly
        alerts.append(
            f"基线异常：当前 ${usage.cost_last_hour:.1f}/h 是基线 ${usage.baseline_hourly:.2f} 的 {ratio:.0f} 倍"
        )
    if usage.max_session_turns >= LONG_SESSION_TURNS:
        alerts.append(
            f"超长会话：单会话 {usage.max_session_turns} 轮（可能死循环 / 探测攻击）"
        )
    return alerts


def scan(usages: list[KeyUsage]) -> None:
    print("=" * 60)
    print("异常成本告警扫描（目标：5 分钟内触发）")
    print("=" * 60)
    any_alert = False
    for u in usages:
        alerts = check_key(u)
        if alerts:
            any_alert = True
            print(f"\n🚨 Key={u.key_id}")
            for a in alerts:
                print(f"    - {a}")
            print(f"    → 建议动作：立即限流 / 临时禁用该 Key + 人工核查（Injection? Bug? 盗用?）")
        else:
            print(f"[正常] Key={u.key_id}  ${u.cost_last_hour:.2f}/h")
    if not any_alert:
        print("\n无异常。")


def main() -> None:
    usages = [
        KeyUsage("hc-prod-web", cost_last_hour=6.2, baseline_hourly=5.0, max_session_turns=12),
        KeyUsage("hc-vkey-A17", cost_last_hour=180.0, baseline_hourly=3.5, max_session_turns=140),
        KeyUsage("hc-batch-job", cost_last_hour=42.0, baseline_hourly=40.0, max_session_turns=8),
    ]
    scan(usages)


if __name__ == "__main__":
    main()
