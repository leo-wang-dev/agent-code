"""数据分层归档自动化脚本。

对应文章第六节"数据分层归档"。LLM 系统数据量极大（百万 DAU 可日产 TB 级 trace），
全部热存储成本会爆炸。工业级做法按访问频率分层：

  热数据层  最近 7 天      SSD/高速对象存储   完整度 100%
  温数据层  7-90 天        标准对象存储(S3/OSS) 完整度 100%
  冷数据层  90 天-1 年     归档存储(Glacier)   可只留聚合+抽样原文

S3/OSS 原生支持生命周期管理。本脚本模拟"按 trace 年龄决定存储层 + 冷层降采样"
的迁移决策，零依赖可运行；生产接对象存储 lifecycle API。
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime, timedelta

HOT_DAYS = 7
WARM_DAYS = 90
COLD_SAMPLE_RATE = 0.1  # 冷层只保留 10% 原文抽样 + 全量聚合


@dataclass
class TraceRecord:
    trace_id: str
    created: datetime
    size_kb: float


def storage_tier(age_days: int) -> str:
    if age_days <= HOT_DAYS:
        return "STANDARD"        # 热：SSD/高速对象存储
    if age_days <= WARM_DAYS:
        return "STANDARD_IA"     # 温：标准低频
    return "GLACIER"             # 冷：归档


def plan_archive(records: list[TraceRecord], now: datetime, rng: random.Random) -> dict:
    """给出每条记录的目标存储层，冷层做降采样，返回迁移计划与成本估算。"""
    plan = {"STANDARD": [], "STANDARD_IA": [], "GLACIER": [], "GLACIER_DROPPED": []}
    for r in records:
        age = (now - r.created).days
        tier = storage_tier(age)
        if tier == "GLACIER" and rng.random() > COLD_SAMPLE_RATE:
            # 冷层：原文只抽样保留，其余仅留聚合（此处标记为已丢弃原文）
            plan["GLACIER_DROPPED"].append(r.trace_id)
        else:
            plan[tier].append(r.trace_id)
    return plan


# 各层每 GB·月估算成本（美元，示意值）
TIER_COST_PER_GB = {"STANDARD": 0.023, "STANDARD_IA": 0.0125, "GLACIER": 0.004}


def main() -> None:
    rng = random.Random(42)
    now = datetime(2026, 7, 7)
    # 造一批不同年龄的 trace
    records = [
        TraceRecord(f"t{i}", now - timedelta(days=age), size_kb=rng.uniform(2, 20))
        for i, age in enumerate(
            [1, 3, 5, 10, 30, 45, 89, 100, 200, 300, 360] * 3
        )
    ]

    print("=" * 60)
    print("数据分层归档计划")
    print("=" * 60)
    plan = plan_archive(records, now, rng)
    for tier in ["STANDARD", "STANDARD_IA", "GLACIER"]:
        print(f"  {tier:<14} 保留 {len(plan[tier]):>3} 条  (${TIER_COST_PER_GB[tier]}/GB·月)")
    print(f"  冷层降采样丢弃原文（仅留聚合）    {len(plan['GLACIER_DROPPED'])} 条")

    total = sum(len(v) for v in plan.values())
    kept = total - len(plan["GLACIER_DROPPED"])
    print(f"\n共 {total} 条 → 保留原文 {kept} 条，降采样节省冷层存储 {len(plan['GLACIER_DROPPED'])} 条")
    print("生产：把该决策映射为 S3/OSS 生命周期规则，数据自动迁移，无需手动搬运。")


if __name__ == "__main__":
    main()
