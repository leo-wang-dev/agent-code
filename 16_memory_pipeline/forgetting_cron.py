"""16 章配套：遗忘 CronJob（约 50 行的每日遗忘任务）。

对应文章第三节⑤"遗忘 Forgetting"：没有遗忘机制的记忆系统会变成垃圾场。

四种遗忘机制：
  ① TTL 过期      —— expires_at 到期 → 归档（此处标 deprecated）
  ② 重要性衰减    —— 长期未触发的事实 importance 自动降低 → 召回下沉
  ③ 用户主动撤回  —— 见 memory_panel_api.py 的 delete
  ④ 事实变更      —— 见 memory_system.upsert 的 UPDATE 分支

本文件实现 ① 和 ②，即「每天凌晨跑一次的遗忘任务」。

离线可运行：`python3 16_memory_pipeline/forgetting_cron.py`
线上：把 run_forgetting_pass() 挂到 cron / APScheduler / K8s CronJob，每日 03:00 触发。
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from memory_system import MemoryFact, MemoryStore  # noqa: E402


@dataclass
class ForgettingReport:
    expired: int = 0            # TTL 过期归档数
    decayed: int = 0           # 重要性衰减条数
    archived_low: int = 0      # importance 跌破地板被归档数


def run_forgetting_pass(
    store: MemoryStore,
    now: float | None = None,
    decay_per_day: float = 0.01,     # 每天未触发衰减 1% 重要性
    importance_floor: float = 0.05,  # 低于此值视为「实际被遗忘」，归档
) -> ForgettingReport:
    """一次遗忘扫描。返回本次处理统计。"""
    now = now or time.time()
    report = ForgettingReport()

    for fact in store.all_facts():
        if fact.is_deprecated:
            continue

        # ① TTL 过期（主要作用于情节记忆）
        if fact.expires_at is not None and fact.expires_at < now:
            fact.is_deprecated = True
            report.expired += 1
            continue

        # ② 重要性衰减：按「距上次更新的天数」线性削减重要性
        age_days = max(0.0, (now - fact.updated_at) / 86400)
        if age_days >= 1:
            before = fact.importance
            fact.importance = max(0.0, fact.importance - decay_per_day * age_days)
            if fact.importance < before:
                report.decayed += 1
            # 语义记忆默认永久，但重要性跌破地板则实际归档
            if fact.importance < importance_floor:
                fact.is_deprecated = True
                report.archived_low += 1

    return report


def _demo() -> None:
    store = MemoryStore()
    now = time.time()

    # 造三条事实：一条已过期、一条很久没更新、一条新鲜
    store.upsert(MemoryFact("u1:travel:1", "u1", "episodic", "travel_event",
                            "上月出差成都", importance=0.4,
                            updated_at=now - 5 * 86400, expires_at=now - 86400))
    store.upsert(MemoryFact("u1:old", "u1", "semantic", "hobby",
                            "曾经喜欢集邮", importance=0.06,
                            updated_at=now - 3 * 86400))
    store.upsert(MemoryFact("u1:name", "u1", "semantic", "name",
                            "张伟", importance=0.9, updated_at=now))

    print("遗忘前：")
    for f in store.all_facts():
        print(f"  [{'deprecated' if f.is_deprecated else 'active    '}] {f.key}={f.value} imp={f.importance:.3f}")

    report = run_forgetting_pass(store, now=now)

    print(f"\n本次遗忘：TTL 过期 {report.expired} 条 / 重要性衰减 {report.decayed} 条 / 低重要性归档 {report.archived_low} 条")
    print("\n遗忘后：")
    for f in store.all_facts():
        print(f"  [{'deprecated' if f.is_deprecated else 'active    '}] {f.key}={f.value} imp={f.importance:.3f}")


if __name__ == "__main__":
    _demo()
