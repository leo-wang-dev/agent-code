"""HITL（Human-in-the-Loop）完整工程实现。

对应文章第一节。高危操作（退款/删除/修改）在执行前暂停，等人工审批。
参考 LangGraph 的 interrupt()——暂停 + 状态保存，审批后恢复执行。

四个工程要点：
  1. 审批 UI 要给充分上下文（操作/数据/金额/推理依据/用户原话/影响范围）；
  2. 审批超时策略：默认拒绝 / 升级 / 告警 —— 永远不因超时自动批准（铁律）；
  3. 否决理由反馈给 Agent，调整后续行为；
  4. 身份保持：HITL 暂停期间用快照令牌，审批通过后恢复。

零依赖，用同步状态机模拟 interrupt/resume（无真实阻塞）。
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum


class ApprovalStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    TIMEOUT = "timeout"


@dataclass
class ApprovalRequest:
    action: str            # refund / delete / modify
    amount: float
    customer_id: str
    agent_reasoning: str   # Agent 为什么要做
    user_original: str     # 触发的用户原话
    impact: str            # 估算影响范围
    snapshot_token: str    # 身份快照（原用户 ID + 操作哈希），审批后恢复用
    created_at: float = field(default_factory=time.time)
    status: ApprovalStatus = ApprovalStatus.PENDING
    decided_by: str | None = None
    reason: str = ""


# 超时策略：默认拒绝（保守）
TIMEOUT_SECONDS = 1800  # 30 分钟
TIMEOUT_POLICY = "reject"  # reject / escalate / alert —— 绝不是 approve


def build_approval_card(req: ApprovalRequest) -> str:
    """给审批人的上下文卡片（要点 2）。"""
    return (
        f"【待审批操作】{req.action}\n"
        f"  金额/对象 : ¥{req.amount} / 客户 {req.customer_id}\n"
        f"  Agent 依据: {req.agent_reasoning}\n"
        f"  用户原话  : {req.user_original}\n"
        f"  影响范围  : {req.impact}\n"
        f"  操作: [一键批准] [一键拒绝] [修改后批准]"
    )


def request_hitl(action: str, amount: float, customer_id: str,
                 reasoning: str, user_text: str, impact: str,
                 snapshot_token: str) -> ApprovalRequest:
    req = ApprovalRequest(action, amount, customer_id, reasoning, user_text, impact, snapshot_token)
    return req


def resolve(req: ApprovalRequest, decision: str, approver: str, reason: str = "",
            now: float | None = None) -> ApprovalRequest:
    """审批人决策（approve/reject）；也处理超时。"""
    now = now if now is not None else time.time()
    if now - req.created_at > TIMEOUT_SECONDS:
        req.status = ApprovalStatus.TIMEOUT
        req.reason = f"审批超时，按策略 {TIMEOUT_POLICY} 处理（绝不自动批准）"
        return req
    if decision == "approve":
        req.status = ApprovalStatus.APPROVED
        req.decided_by = approver
    else:
        req.status = ApprovalStatus.REJECTED
        req.decided_by = approver
        req.reason = reason
    return req


def agent_after_approval(req: ApprovalRequest) -> str:
    """审批结果反馈给 Agent，决定后续行为（要点 1、4）。"""
    if req.status == ApprovalStatus.APPROVED:
        # 用 snapshot_token 恢复原用户身份执行
        return f"操作已获 {req.decided_by} 批准，使用快照令牌恢复执行 {req.action}。"
    if req.status == ApprovalStatus.REJECTED:
        return f"操作未通过审批。原因：{req.reason}。请补充信息后重新提交。"
    return "操作未获批准（超时按拒绝处理）。请稍后重试或联系值班。"


def main() -> None:
    print("=" * 60)
    print("HITL 审批工作流演示")
    print("=" * 60)

    req = request_hitl(
        action="refund", amount=2999.0, customer_id="cust_88",
        reasoning="用户提供了有效的质量问题凭证，符合 7 天退货政策",
        user_text="产品用了两天就坏了，我要退款",
        impact="单笔退款 ¥2999，影响 1 名客户",
        snapshot_token="snap:cust_88:refund:ab12cd",
    )
    print("\n" + build_approval_card(req))

    print("\n场景 A：审批人批准")
    r1 = resolve(req, "approve", approver="mgr_li")
    print("  ", agent_after_approval(r1))

    print("\n场景 B：审批人拒绝并给理由")
    req2 = request_hitl("delete", 0, "cust_90", "用户要求删除账户",
                        "删掉我的账号", "不可逆，删除全部数据", "snap:cust_90:delete:ff01")
    r2 = resolve(req2, "reject", approver="mgr_li", reason="需先完成身份二次验证")
    print("  ", agent_after_approval(r2))

    print("\n场景 C：审批超时（铁律：绝不自动批准）")
    req3 = request_hitl("modify", 0, "cust_91", "改绑手机号", "换个手机号", "中风险", "snap:...")
    req3.created_at = time.time() - TIMEOUT_SECONDS - 10  # 模拟超时
    r3 = resolve(req3, "approve", approver="system")
    print("  ", agent_after_approval(r3))


if __name__ == "__main__":
    main()
