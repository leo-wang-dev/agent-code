"""三层防御协同的端到端项目 —— 完整输出端防御体系。

对应文章第四节。把 Guardrails / 宪法链 / HITL 三层组合：

  [Agent 生成回答]
      ↓
  [Guardrails 程序化过滤]  毫秒级、确定性强 → PII/关键词/格式
      ↓ 通过
  [宪法链审视]             秒级、LLM 判断 → 隐式承诺/不当推荐等复杂语义
      ↓ 通过
  [判断是否高危操作]
      ├ 否 → 直接返回用户
      └ 是 → HITL 审批 → 批准执行 / 拒绝并解释

三层角色分工：Guardrails(快/中强) → 宪法链(慢/高强) → HITL(最慢/最强/人决策)。

零依赖，复用本章 guardrails_ai_demo / constitutional_chain / hitl_workflow。
"""
from __future__ import annotations

from dataclasses import dataclass

import guardrails_ai_demo as guardrails
import constitutional_chain as constitution
from hitl_workflow import request_hitl, resolve, agent_after_approval

HIGH_RISK_ACTIONS = {"refund", "delete", "modify"}
# 高风险领域才启用宪法链（一般问答不启用，避免过度工程）
CONSTITUTIONAL_DOMAINS = {"客服", "医疗", "法律", "金融"}


@dataclass
class AgentTurn:
    user_query: str
    domain: str
    raw_response: str
    pending_action: str | None = None  # refund/delete/modify 或 None
    action_amount: float = 0.0
    customer_id: str = ""


def handle_guard_violation(response: str, result: guardrails.GuardResult) -> tuple[str, bool]:
    """critical 违规直接拦截；一般违规尝试修正。返回 (响应, 是否放行)。"""
    if any(v.severity == "critical" for v in result.violations):
        return "抱歉，我的回答可能不合规。请换个方式描述您的需求。", False
    # 非 critical：此处 mock 修正（真实环境让 Agent 带额外指令重生成）
    return response, True


def requires_constitutional_review(domain: str) -> bool:
    return domain in CONSTITUTIONAL_DOMAINS


def run(turn: AgentTurn, approver_decision: str = "approve") -> dict:
    trace = []
    response = turn.raw_response

    # 1. Guardrails 程序化过滤
    gr = guardrails.validate(response)
    trace.append(("guardrails", "pass" if gr.passed else "violation"))
    if not gr.passed:
        response, ok = handle_guard_violation(response, gr)
        if not ok:
            return {"final": response, "stopped_at": "guardrails", "trace": trace}

    # 2. 宪法链审视（仅高风险领域）
    if requires_constitutional_review(turn.domain):
        cc = constitution.constitutional_chain(response)
        trace.append(("constitution", cc["verdict"]))
        if cc["verdict"] == "BLOCK":
            return {"final": cc["final"], "stopped_at": "constitution", "trace": trace}
        response = cc["final"]
    else:
        trace.append(("constitution", "skipped(非高风险领域)"))

    # 3. HITL（高危操作）
    if turn.pending_action in HIGH_RISK_ACTIONS:
        req = request_hitl(
            action=turn.pending_action, amount=turn.action_amount,
            customer_id=turn.customer_id,
            reasoning="Agent 判断满足操作条件",
            user_text=turn.user_query, impact="见审批卡片",
            snapshot_token=f"snap:{turn.customer_id}:{turn.pending_action}",
        )
        resolved = resolve(req, approver_decision, approver="mgr_li", reason="不符合政策")
        trace.append(("hitl", resolved.status.value))
        return {"final": agent_after_approval(resolved), "stopped_at": "hitl", "trace": trace}

    trace.append(("return", "direct"))
    return {"final": response, "stopped_at": None, "trace": trace}


def main() -> None:
    print("=" * 60)
    print("三层防御协同 端到端演示")
    print("=" * 60)

    cases = [
        AgentTurn("推荐个洁面", "客服", "为您推荐这款温和氨基酸洁面，适合日常使用。"),
        AgentTurn("联系上个客户", "客服", "上一位客户电话是 13800138000，您可直接联系。"),
        AgentTurn("我要退款2999", "金融", "已确认符合退货政策，为您办理退款。",
                  pending_action="refund", action_amount=2999.0, customer_id="cust_88"),
    ]
    for turn in cases:
        result = run(turn)
        print(f"\n[query] {turn.user_query}  (领域={turn.domain})")
        print(f"  链路: {result['trace']}")
        print(f"  终止层: {result['stopped_at'] or '直接返回'}")
        print(f"  最终: {result['final']}")


if __name__ == "__main__":
    main()
