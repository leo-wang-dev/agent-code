"""客服系统 —— LangGraph 版完整实现。

4 种意图各走不同路径：
  - kb       ：知识库问答，内部走 RAG 子图（retrieve → rerank → synthesize）
  - order    ：订单查询，调订单 API + 格式化
  - complaint：投诉处理，创建工单 + interrupt() 人工审批（HITL）+ 通知人工
  - chitchat ：闲聊，纯回复
特点：路由用纯 Python（快、省 token）、HITL 原生 interrupt、Checkpoint 可追溯。

节点均为 mock 逻辑（无需 OPENAI_API_KEY）；投诉路径演示真实的 interrupt + resume。

需要依赖：pip install langgraph
"""
from __future__ import annotations

import operator
from typing import Annotated, TypedDict

try:
    from langgraph.graph import StateGraph, START, END
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.types import interrupt, Command
except ImportError:
    print("需要先安装依赖：pip install langgraph")
    print("（本示例为 LangGraph 版客服系统，缺少 langgraph 无法运行）")
    raise SystemExit(0)


class CustomerServiceState(TypedDict, total=False):
    user_input: str
    intent: str
    kb_results: list
    top_k: list
    order_result: dict
    complaint_ticket_id: str
    approved: bool
    final_response: str
    messages: Annotated[list, operator.add]


# ---------- 意图分类：纯 Python，比 LLM 快 100 倍 ----------
def classify_intent(state: CustomerServiceState) -> dict:
    text = state["user_input"].lower()
    if "订单" in text or "物流" in text:
        return {"intent": "order"}
    if "投诉" in text or "举报" in text:
        return {"intent": "complaint"}
    if any(kw in text for kw in ["怎么", "为什么", "如何"]):
        return {"intent": "kb"}
    return {"intent": "chitchat"}


def route(state: CustomerServiceState) -> str:
    return state["intent"]


# ---------- KB 子图：retrieve → rerank → synthesize ----------
def kb_retrieve(state: CustomerServiceState) -> dict:
    return {"kb_results": ["文档A", "文档B", "文档C", "文档D"]}


def kb_rerank(state: CustomerServiceState) -> dict:
    return {"top_k": state["kb_results"][:2]}


def kb_synthesize(state: CustomerServiceState) -> dict:
    return {"final_response": f"根据 {state['top_k']} 综合回复：请按文档步骤操作。"}


def build_kb_subgraph():
    g = StateGraph(CustomerServiceState)
    g.add_node("retrieve", kb_retrieve)
    g.add_node("rerank", kb_rerank)
    g.add_node("synthesize", kb_synthesize)
    g.add_edge(START, "retrieve")
    g.add_edge("retrieve", "rerank")
    g.add_edge("rerank", "synthesize")
    g.add_edge("synthesize", END)
    return g.compile()


# ---------- order 路径 ----------
def handle_order(state: CustomerServiceState) -> dict:
    order = {"id": "SO20260707", "status": "运输中", "eta": "明天"}
    return {"order_result": order,
            "final_response": f"订单 {order['id']} 当前 {order['status']}，预计 {order['eta']} 送达。"}


# ---------- complaint 子图：创建工单 → HITL 审批 → 通知人工 ----------
def create_ticket(state: CustomerServiceState) -> dict:
    return {"complaint_ticket_id": "TK-8848"}


def approval_gate(state: CustomerServiceState) -> dict:
    decision = interrupt({
        "type": "complaint_approval",
        "ticket": state["complaint_ticket_id"],
        "user": state["user_input"],
    })
    return {"approved": decision == "approve"}


def notify_human(state: CustomerServiceState) -> dict:
    if state.get("approved"):
        return {"final_response": f"投诉工单 {state['complaint_ticket_id']} 已转人工，客服会尽快联系您。"}
    return {"final_response": "投诉已取消。"}


def build_complaint_subgraph():
    g = StateGraph(CustomerServiceState)
    g.add_node("create_ticket", create_ticket)
    g.add_node("approval", approval_gate)
    g.add_node("notify", notify_human)
    g.add_edge(START, "create_ticket")
    g.add_edge("create_ticket", "approval")
    g.add_edge("approval", "notify")
    g.add_edge("notify", END)
    return g.compile()


# ---------- chitchat 路径 ----------
def handle_chitchat(state: CustomerServiceState) -> dict:
    return {"final_response": "您好呀，有什么可以帮您？"}


def build_app():
    graph = StateGraph(CustomerServiceState)
    graph.add_node("classify", classify_intent)
    graph.add_node("kb", build_kb_subgraph())            # 子图作为节点
    graph.add_node("order", handle_order)
    graph.add_node("complaint", build_complaint_subgraph())  # 子图作为节点（含 HITL）
    graph.add_node("chitchat", handle_chitchat)

    graph.add_edge(START, "classify")
    graph.add_conditional_edges("classify", route, {
        "kb": "kb", "order": "order", "complaint": "complaint", "chitchat": "chitchat",
    })
    for path in ("kb", "order", "complaint", "chitchat"):
        graph.add_edge(path, END)
    # 生产用 PostgresSaver；demo 用 MemorySaver
    return graph.compile(checkpointer=MemorySaver())


def main() -> None:
    app = build_app()

    # 非投诉意图：一次跑通
    for i, msg in enumerate(["我的订单到哪了", "这个功能怎么用", "在吗"], start=1):
        config = {"configurable": {"thread_id": f"user_{i}"}}
        result = app.invoke({"user_input": msg}, config=config)
        print(f"[{result['intent']:8}] {msg!r} → {result['final_response']}")

    # 投诉意图：演示 HITL（interrupt → 人工审批 → resume）
    config = {"configurable": {"thread_id": "user_complaint"}}
    for event in app.stream({"user_input": "我要投诉你们的服务"}, config=config):
        if "__interrupt__" in event:
            print(f"[complaint] 触发 HITL 审批：{event['__interrupt__'][0].value['ticket']}")
    result = app.invoke(Command(resume="approve"), config=config)
    print(f"[complaint] 审批通过 → {result['final_response']}")


if __name__ == "__main__":
    main()
