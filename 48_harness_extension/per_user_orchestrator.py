"""per-user 实例编排脚本 —— mock 容器管理器演示实例生命周期。

对应文章第 48 篇 六、Fork 路径的三大隐形成本（成本3 实例生命周期管理）+
四、Per-User 部署模式的真实代价。

用 mock 容器管理器演示：按需 spin-up、不活跃回收、故障重启、资源分档、成本核算。
生产替换为 K8s（Deployment/StatefulSet + HPA）或 Nomad 等真实编排。

离线可跑：`python3 per_user_orchestrator.py`
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum


class InstanceState(Enum):
    PENDING = "pending"
    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"


# 资源分档（对齐文章：不同用户资源需求差异 10x）
TIER_SPEC = {
    "normal": {"cpu": 1, "mem_gb": 2, "cost_month": 30},
    "vip": {"cpu": 4, "mem_gb": 8, "cost_month": 120},
}


@dataclass
class Instance:
    user_id: str
    tier: str
    state: InstanceState = InstanceState.PENDING
    last_active: float = field(default_factory=time.time)
    restarts: int = 0


class MockContainerManager:
    """离线 mock 容器编排器。生产替换为 K8s client / Nomad API。"""

    def __init__(self, inactive_days: int = 30):
        self.instances: dict[str, Instance] = {}
        self.inactive_seconds = inactive_days * 86400

    def spin_up(self, user_id: str, tier: str = "normal") -> Instance:
        """首次对话时按需拉起实例（比注册时拉起更省资源）。"""
        if user_id in self.instances:
            return self.instances[user_id]
        inst = Instance(user_id=user_id, tier=tier, state=InstanceState.RUNNING)
        self.instances[user_id] = inst
        return inst

    def touch(self, user_id: str) -> None:
        if user_id in self.instances:
            self.instances[user_id].last_active = time.time()

    def health_check_and_recover(self) -> list[str]:
        """故障实例自动重启（数据恢复由持久卷保证）。"""
        recovered = []
        for inst in self.instances.values():
            if inst.state == InstanceState.FAILED:
                inst.state = InstanceState.RUNNING
                inst.restarts += 1
                recovered.append(inst.user_id)
        return recovered

    def reap_inactive(self, now: float | None = None) -> list[str]:
        """回收不活跃实例（销毁而非常驻，省成本）。"""
        now = now or time.time()
        reaped = []
        for inst in self.instances.values():
            if inst.state == InstanceState.RUNNING and now - inst.last_active > self.inactive_seconds:
                inst.state = InstanceState.STOPPED
                reaped.append(inst.user_id)
        return reaped

    def monthly_cost(self) -> float:
        return sum(
            TIER_SPEC[i.tier]["cost_month"]
            for i in self.instances.values()
            if i.state == InstanceState.RUNNING
        )


def _demo() -> None:
    mgr = MockContainerManager(inactive_days=30)

    print("=== 按需拉起实例 ===")
    for uid, tier in [("u_normal_1", "normal"), ("u_vip_1", "vip"), ("u_normal_2", "normal")]:
        inst = mgr.spin_up(uid, tier)
        spec = TIER_SPEC[tier]
        print(f"  {uid:<12} tier={tier:<6} {inst.state.value}  "
              f"({spec['cpu']}c/{spec['mem_gb']}G ${spec['cost_month']}/月)")

    print("\n=== 故障自愈 ===")
    mgr.instances["u_normal_2"].state = InstanceState.FAILED
    recovered = mgr.health_check_and_recover()
    print(f"  已重启: {recovered}  (restarts={mgr.instances['u_normal_2'].restarts})")

    print("\n=== 不活跃回收（模拟 40 天未活跃）===")
    mgr.instances["u_normal_1"].last_active = time.time() - 40 * 86400
    reaped = mgr.reap_inactive()
    print(f"  已回收: {reaped}")

    print("\n=== 当月成本（仅 RUNNING 计费）===")
    print(f"  ${mgr.monthly_cost()}/月")
    print("  提示：per-user 单用户成本约为共享方案的 2 倍——需差异化收入覆盖（文章）。")


if __name__ == "__main__":
    _demo()
