"""混合使用：LangGraph 主图 + 节点内嵌 CrewAI Crew —— 工业级真实做法。

LangGraph 负责主流程控制/状态管理/持久化/HITL/可追溯性（它强）；
CrewAI 负责特定子任务里的多 Agent 协作（研究员→写手→编辑，它强）。

主图结构：
  classify(Python) → route
    ├── kb        (LangGraph 子图逻辑，纯 Python mock)
    ├── content   (Node：内部包装 CrewAI Crew：研究员→写手→编辑)
    └── chitchat  (Python)

content 节点用真实 CrewAI 对象；有 OPENAI_API_KEY 时 kickoff 真跑，否则返回 mock。

需要依赖：pip install langgraph crewai
"""
from __future__ import annotations

import os
from typing import TypedDict

os.environ.setdefault("OPENAI_API_KEY", "sk-demo-placeholder")
os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")
os.environ.setdefault("CREWAI_TELEMETRY_OPT_OUT", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")

HAS_REAL_KEY = os.environ["OPENAI_API_KEY"] != "sk-demo-placeholder"

try:
    from langgraph.graph import StateGraph, START, END
except ImportError:
    print("需要先安装依赖：pip install langgraph crewai")
    print("（本示例为 LangGraph+CrewAI 混用，缺少 langgraph 无法运行）")
    raise SystemExit(0)

try:
    from crewai import Agent, Task, Crew, Process
    HAS_CREWAI = True
except ImportError:
    HAS_CREWAI = False


class State(TypedDict, total=False):
    query: str
    intent: str
    result: str


def classify(state: State) -> dict:
    q = state["query"]
    if "写" in q or "文章" in q or "报告" in q:
        return {"intent": "content"}
    if any(k in q for k in ["怎么", "为什么", "如何"]):
        return {"intent": "kb"}
    return {"intent": "chitchat"}


def kb_node(state: State) -> dict:
    return {"result": "[LangGraph 子图] 检索+重排+生成的知识库回复"}


def chitchat_node(state: State) -> dict:
    return {"result": "[LangGraph] 您好，有什么可以帮您？"}


def content_node(state: State) -> dict:
    """LangGraph 节点内部包装一个 CrewAI Crew（研究员→写手→编辑）。"""
    if not HAS_CREWAI:
        return {"result": "[未安装 crewai] 该节点应内嵌研究员→写手→编辑的 Crew"}

    researcher = Agent(role="研究员", goal="调研主题素材", backstory="资深研究员", verbose=False)
    writer = Agent(role="写手", goal="据素材写初稿", backstory="资深撰稿人", verbose=False)
    editor = Agent(role="编辑", goal="润色定稿", backstory="严格主编", verbose=False)
    t1 = Task(description=f"调研：{state['query']}", expected_output="素材要点", agent=researcher)
    t2 = Task(description="据素材写初稿", expected_output="初稿", agent=writer, context=[t1])
    t3 = Task(description="润色成终稿", expected_output="终稿", agent=editor, context=[t2])
    crew = Crew(agents=[researcher, writer, editor], tasks=[t1, t2, t3],
                process=Process.sequential, verbose=False)

    if HAS_REAL_KEY:
        return {"result": f"[CrewAI Crew] {crew.kickoff(inputs={'query': state['query']})}"}
    return {"result": "[CrewAI Crew 已构造：研究员→写手→编辑；设 OPENAI_API_KEY 后产出终稿]"}


def build_app():
    graph = StateGraph(State)
    graph.add_node("classify", classify)
    graph.add_node("kb", kb_node)
    graph.add_node("content", content_node)  # ← 内部是 CrewAI Crew
    graph.add_node("chitchat", chitchat_node)
    graph.add_edge(START, "classify")
    graph.add_conditional_edges("classify", lambda s: s["intent"],
                                {"kb": "kb", "content": "content", "chitchat": "chitchat"})
    for p in ("kb", "content", "chitchat"):
        graph.add_edge(p, END)
    return graph.compile()


def main() -> None:
    if not HAS_REAL_KEY:
        print("未检测到真实 OPENAI_API_KEY：主图与 Crew 照常构造，content 节点返回 mock。\n")
    app = build_app()
    for q in ["帮我写一篇新能源市场分析文章", "这个功能怎么用", "在吗"]:
        result = app.invoke({"query": q})
        print(f"[{result['intent']:8}] {q!r}")
        print(f"           → {result['result']}")


if __name__ == "__main__":
    main()
