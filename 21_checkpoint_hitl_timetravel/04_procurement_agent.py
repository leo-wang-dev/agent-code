"""端到端项目：采购 Agent + 审批流程 + 流程审计。

场景：员工提交采购需求，系统匹配供应商、生成报价单，
金额 ≥ 5 万必须经理审批。三件事各司其职：
  - Checkpoint：服务挂了凭 thread_id 恢复；
  - HITL：金额超 5w 自动暂停等审批；
  - Time Travel：事后拉出完整 checkpoint 链做流程审计。

流程：
  receive_request → parse_requirements → match_suppliers → generate_quote
      → check_amount ─(<5w)→ auto_send → END
                     └(≥5w)→ approval(interrupt) → send_quote → END

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
    print("（本示例为采购 Agent 端到端项目，缺少 langgraph 无法运行）")
    raise SystemExit(0)


APPROVAL_THRESHOLD = 50000


class State(TypedDict, total=False):
    request: str
    requirements: list
    suppliers: list
    quote: dict
    approved: bool
    status: str


def receive_request(state: State) -> dict:
    return {"request": state["request"]}


def parse_requirements(state: State) -> dict:  # 真实场景 LLM 解析
    return {"requirements": ["笔记本电脑 x10", "显示器 x10"]}


def match_suppliers(state: State) -> dict:  # 工具调用
    return {"suppliers": ["联想", "戴尔", "惠普"]}


def generate_quote(state: State) -> dict:  # 真实场景 LLM 生成
    amount = 68000  # 触发审批
    return {"quote": {"amount": amount, "supplier": state["suppliers"][0]}}


def auto_send(state: State) -> dict:
    return {"status": "auto_sent", "approved": True}


def approval(state: State) -> dict:
    decision = interrupt(
        {
            "message": f"采购金额 ¥{state['quote']['amount']} 超过 5 万，请经理审批",
            "supplier": state["quote"]["supplier"],
        }
    )
    return {"approved": decision == "approve"}


def send_quote(state: State) -> dict:
    return {"status": "sent" if state.get("approved") else "rejected"}


def check_amount(state: State) -> str:
    return "approval" if state["quote"]["amount"] >= APPROVAL_THRESHOLD else "auto_send"


def build_app():
    graph = StateGraph(State)
    graph.add_node("receive", receive_request)
    graph.add_node("parse", parse_requirements)
    graph.add_node("match", match_suppliers)
    graph.add_node("quote", generate_quote)
    graph.add_node("auto_send", auto_send)
    graph.add_node("approval", approval)
    graph.add_node("send", send_quote)

    graph.add_edge(START, "receive")
    graph.add_edge("receive", "parse")
    graph.add_edge("parse", "match")
    graph.add_edge("match", "quote")
    graph.add_conditional_edges("quote", check_amount, {"auto_send": "auto_send", "approval": "approval"})
    graph.add_edge("auto_send", END)
    graph.add_edge("approval", "send")
    graph.add_edge("send", END)
    return graph.compile(checkpointer=MemorySaver())


def main() -> None:
    app = build_app()
    config = {"configurable": {"thread_id": "procure_2026_001"}}

    print("=== 1. 员工提交采购需求 ===")
    for event in app.stream({"request": "为研发部采购 10 套办公设备"}, config=config):
        if "__interrupt__" in event:
            print("  [HITL] 暂停等审批：", event["__interrupt__"][0].value["message"])

    print("\n=== 2. 经理审批通过，流程继续 ===")
    result = app.invoke(Command(resume="approve"), config=config)
    print("  最终状态 status =", result["status"])

    print("\n=== 3. 流程审计（Time Travel 拉出完整 checkpoint 链） ===")
    for cp in reversed(list(app.get_state_history(config))):
        step = cp.metadata.get("step")
        written = cp.metadata.get("writes") or {}
        print(f"  step={step}  节点={list(written.keys())}  next={cp.next}")


if __name__ == "__main__":
    main()
