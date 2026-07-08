"""Bad Case 自动采样系统。

对应文章第二节"Bad Case 闭环"。工业级不靠人工"记得提交 case"，靠系统按规则
自动采样上报——采样后进入 Bad Case 池，由 QA 定期审：真 bad case 入评测集、
误报丢弃、新故障模式升级为重点关注类别。

铁律：任何线上故障定位完成后，必须留下一条评测用例（棘轮效应，质量只能往上）。

零依赖，可运行。真实环境把 `SAMPLE_RULES` 接到你的埋点/反馈数据源即可。
"""
from __future__ import annotations

import json
import os
import random
from dataclasses import asdict, dataclass, field
from datetime import datetime


@dataclass
class Interaction:
    session_id: str
    user_query: str
    response: str
    user_rated_thumbs_down: bool = False
    user_repeated_question: bool = False
    agent_admitted_uncertainty: bool = False
    tool_call_failed: bool = False
    high_value_user: bool = False


@dataclass
class SampledCase:
    session_id: str
    user_query: str
    response: str
    triggered_rules: list[str]
    sampled_at: str
    status: str = "pending_review"  # pending_review / accepted / rejected
    priority: str = "normal"


# ---------------------------------------------------------------------------
# 采样规则（对应文章埋点里的 rules 列表）
# ---------------------------------------------------------------------------
def _response_too_short(it: Interaction) -> bool:
    return len(it.response.strip()) < 10


SAMPLE_RULES = {
    "user_rated_thumbs_down": lambda it: it.user_rated_thumbs_down,
    "user_repeated_question": lambda it: it.user_repeated_question,
    "agent_admitted_uncertainty": lambda it: it.agent_admitted_uncertainty,
    "tool_call_failed": lambda it: it.tool_call_failed,
    "response_too_short": _response_too_short,
    # VIP 会话提高采样比例（此处用概率模拟）
    "high_value_user_session": lambda it: it.high_value_user and random.random() < 0.5,
}


def sample_for_review(it: Interaction) -> SampledCase | None:
    """按规则判断是否采样。命中任一规则即进入 Bad Case 池。"""
    triggered = [name for name, rule in SAMPLE_RULES.items() if rule(it)]
    if not triggered:
        return None
    # VIP 命中或点踩 → 高优先级
    priority = "high" if (it.high_value_user or it.user_rated_thumbs_down) else "normal"
    return SampledCase(
        session_id=it.session_id,
        user_query=it.user_query,
        response=it.response,
        triggered_rules=triggered,
        sampled_at=datetime.now().isoformat(timespec="seconds"),
        priority=priority,
    )


class BadCasePool:
    """Bad Case 池：采样落盘，供 QA 审核。"""

    def __init__(self, path: str) -> None:
        self.path = path
        self.cases: list[SampledCase] = []

    def add(self, case: SampledCase) -> None:
        self.cases.append(case)

    def flush(self) -> None:
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump([asdict(c) for c in self.cases], fh, ensure_ascii=False, indent=2)

    def summary(self) -> dict:
        by_rule: dict[str, int] = {}
        for c in self.cases:
            for r in c.triggered_rules:
                by_rule[r] = by_rule.get(r, 0) + 1
        return {
            "total": len(self.cases),
            "high_priority": sum(1 for c in self.cases if c.priority == "high"),
            "by_rule": dict(sorted(by_rule.items(), key=lambda x: -x[1])),
        }


# ---------------------------------------------------------------------------
# demo：模拟一批线上交互，跑一遍采样
# ---------------------------------------------------------------------------
def _demo_interactions() -> list[Interaction]:
    return [
        Interaction("s1", "订单怎么还没到", "已为您查询，预计明天送达。"),  # 正常，不采样
        Interaction("s2", "发票丢了能退吗", "不能。", user_rated_thumbs_down=True),  # 回答过短+点踩
        Interaction("s3", "在吗在吗", "嗯", user_repeated_question=True),
        Interaction("s4", "这个能便宜点吗", "我不太确定这个问题。", agent_admitted_uncertainty=True, high_value_user=True),
        Interaction("s5", "帮我下单", "系统错误", tool_call_failed=True),
    ]


def main() -> None:
    random.seed(42)  # 确定性输出
    here = os.path.dirname(os.path.abspath(__file__))
    pool = BadCasePool(os.path.join(here, "bad_case_pool.json"))

    print("=" * 56)
    print("Bad Case 自动采样")
    print("=" * 56)
    for it in _demo_interactions():
        sampled = sample_for_review(it)
        if sampled:
            pool.add(sampled)
            print(f"[采样] {it.session_id}  规则={sampled.triggered_rules}  优先级={sampled.priority}")
        else:
            print(f"[跳过] {it.session_id}  未命中规则")

    pool.flush()
    print("\n池子统计：")
    print(json.dumps(pool.summary(), ensure_ascii=False, indent=2))
    print(f"\n已落盘：{pool.path}（供 QA 审核 → 真 bad case 转评测用例）")


if __name__ == "__main__":
    main()
