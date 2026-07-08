"""18 章配套：置信度阈值 + 暂存区机制。

对应文章第五节细节 4"置信度阈值 + 暂存区机制"：

  抽取结果 confidence < 0.7 → 进暂存区
          confidence >= 0.7 → 进正式记忆库

  暂存区里的事实 → 被多次（如 3 次）类似事实再次确认 → 升级为正式记忆
               → 如果 30 天没有再次出现 → 自动清理

"这个机制能把误抽率降低 60% 以上"——大部分偶发的离谱事实会在暂存区被自然清理掉。

离线可运行：`python3 18_layered_memory/staging_area.py`
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


CONFIDENCE_THRESHOLD = 0.7    # >= 直接进正式库
PROMOTE_AFTER = 3             # 暂存区累计确认 N 次 → 升级
STAGING_TTL_DAYS = 30         # 暂存区超过 N 天没再出现 → 清理


@dataclass
class StagedFact:
    key: str
    value: str
    confirmations: int = 1
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    max_confidence: float = 0.0


@dataclass
class StagingArea:
    """暂存区：低置信事实的缓冲池，多次确认后升级，长期不确认则清理。"""

    formal: dict[str, str] = field(default_factory=dict)      # 正式记忆库 key->value
    staging: dict[str, StagedFact] = field(default_factory=dict)

    def ingest(self, key: str, value: str, confidence: float, now: float | None = None) -> str:
        """抽取到一条事实：返回本次动作 PROMOTE_DIRECT / STAGE / CONFIRM / PROMOTE。"""
        now = time.time() if now is None else now

        if confidence >= CONFIDENCE_THRESHOLD:
            self.formal[key] = value
            return "PROMOTE_DIRECT"

        staged = self.staging.get(key)
        if staged is None or staged.value != value:
            # 新的低置信事实（或值变了）→ 进暂存区
            self.staging[key] = StagedFact(key, value, confirmations=1,
                                           first_seen=now, last_seen=now, max_confidence=confidence)
            return "STAGE"

        # 类似事实再次出现 → 累计确认
        staged.confirmations += 1
        staged.last_seen = now
        staged.max_confidence = max(staged.max_confidence, confidence)
        if staged.confirmations >= PROMOTE_AFTER:
            self.formal[key] = staged.value
            del self.staging[key]
            return "PROMOTE"
        return "CONFIRM"

    def gc(self, now: float | None = None) -> int:
        """清理暂存区里 30 天没再出现的事实。返回清理条数。"""
        now = time.time() if now is None else now
        cutoff = STAGING_TTL_DAYS * 86400
        stale = [k for k, s in self.staging.items() if now - s.last_seen > cutoff]
        for k in stale:
            del self.staging[k]
        return len(stale)


def _demo() -> None:
    area = StagingArea()
    now = 1_000_000.0

    print("=== 高置信事实直接进正式库 ===")
    action = area.ingest("occupation", "产品经理", confidence=0.9, now=now)
    print(f"  occupation=产品经理 conf=0.9 → {action}")

    print("\n=== 低置信事实进暂存区，多次确认后升级 ===")
    for i in range(3):
        action = area.ingest("hobby", "喜欢摄影", confidence=0.55, now=now + i * 86400)
        print(f"  第 {i+1} 次 hobby=喜欢摄影 conf=0.55 → {action}")

    print("\n=== 偶发离谱事实：只出现一次，30 天后被清理 ===")
    area.ingest("origin", "用户是火星人", confidence=0.3, now=now)
    print(f"  暂存区当前：{list(area.staging.keys())}")
    removed = area.gc(now=now + 31 * 86400)
    print(f"  30 天后 gc 清理 {removed} 条 → 暂存区：{list(area.staging.keys())}")

    print(f"\n正式记忆库：{area.formal}")
    print("要点：置信度阈值 + 暂存区让离谱事实自然过滤，误抽率降 60%+。")


if __name__ == "__main__":
    _demo()
