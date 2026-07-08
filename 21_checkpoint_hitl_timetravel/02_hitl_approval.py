"""HITL 完整审批流 —— interrupt() + Command(resume=...) 报价审批。

流程：[generate_quote] → [approval_gate: 等审批] → [send_email]
凡涉及真实世界副作用（支付/删数据/对外发送/下单/部署）都必须有人审批。

工作机制：
  1. 图执行到 interrupt() 暂停，state 存进 checkpoint；
  2. 外部读到中间状态、展示给审批人；
  3. 审批人决定后 app.invoke(Command(resume=决定))，值即 interrupt() 的返回值；
  4. 图从暂停节点继续。

需要依赖：pip install langgraph
"""
from __future__ import annotations

from typing import TypedDict

try:
    from langgraph.graph import StateGraph, START, END
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.types import interrupt, Command
except ImportError:
    print("需要先安装依赖：pip install langgraph")
    print("（本示例演示 HITL interrupt 审批流，缺少 langgraph 无法运行）")
    raise SystemExit(0)


class State(TypedDict, total=False):
    customer: str
    quote: dict
    approved: bool
    status: str


def quote_workflow(state: State) -> dict:
    quote = {"amount": 88000, "items": ["设备A x2"]}
    return {"quote": quote}


def approval_gate(state: State) -> dict:
    # 暂停！把要审批的数据抛给外部
    decision = interrupt(
        {
            "type": "approval",
            "message": f"报价 ¥{state['quote']['amount']}, 是否批准？",
            "customer": state["customer"],
        }
    )
    return {"approved": decision == "approve"}


def send_email(state: State) -> dict:
    if state.get("approved"):
        return {"status": "sent"}
    return {"status": "rejected"}


def build_app():
    graph = StateGraph(State)
    graph.add_node("quote", quote_workflow)
    graph.add_node("approval", approval_gate)
    graph.add_node("send", send_email)
    graph.add_edge(START, "quote")
    graph.add_edge("quote", "approval")
    graph.add_edge("approval", "send")
    graph.add_edge("send", END)
    return graph.compile(checkpointer=MemorySaver())


def main() -> None:
    app = build_app()
    config = {"configurable": {"thread_id": "request_abc"}}

    # 1. 发起请求，跑到 interrupt 处暂停
    for event in app.stream({"customer": "大眼睛科技"}, config=config):
        if "__interrupt__" in event:
            payload = event["__interrupt__"][0].value
            print("暂停等待审批：", payload["message"], "| 客户:", payload["customer"])

    # 此时流程挂起，state 已存 checkpoint（可能几小时后才有人审批）
    print("当前中断点：", app.get_state(config).next)

    # 2. 审批人点了"批准" → resume
    result = app.invoke(Command(resume="approve"), config=config)
    print("审批通过后继续执行，最终状态 status =", result["status"])


if __name__ == "__main__":
    main()
