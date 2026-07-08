"""客服系统 —— CrewAI 版完整实现。

结构：CustomerServiceFlow(Flow)
  classify_intent(start) → router → 4 条 @listen 路径，每条建一个 Crew：
    kb_path       ：kb_crew（retriever_agent → synthesizer_agent，Sequential）
    order_path    ：order_crew（order_agent）
    complaint_path：complaint_crew（ticket_agent → notify_agent）+ 自拼 HITL
    chitchat_path ：chitchat_crew（chitchat_agent）
  memory=True 开启长期记忆。

特点：角色 prompt 明牌、Memory 零配置；但 HITL 要自己拼、流程可追溯性弱。

无 OPENAI_API_KEY 时：Flow 路由照常运行，Crew 对象照常构造，仅不发起真实 kickoff。

需要依赖：pip install crewai
"""
from __future__ import annotations

import os

os.environ.setdefault("OPENAI_API_KEY", "sk-demo-placeholder")
os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")
os.environ.setdefault("CREWAI_TELEMETRY_OPT_OUT", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")

HAS_REAL_KEY = os.environ["OPENAI_API_KEY"] != "sk-demo-placeholder"

try:
    from crewai import Agent, Task, Crew, Process
    from crewai.flow.flow import Flow, start, listen, router
except ImportError:
    print("需要先安装依赖：pip install crewai")
    print("（本示例为 CrewAI 版客服系统，缺少 crewai 无法运行）")
    raise SystemExit(0)


def call_classifier(text: str) -> str:
    """真实场景可用 LLM 分类；这里用关键词，等价且更省。"""
    t = text.lower()
    if "订单" in t or "物流" in t:
        return "order"
    if "投诉" in t or "举报" in t:
        return "complaint"
    if any(kw in t for kw in ["怎么", "为什么", "如何"]):
        return "kb"
    return "chitchat"


def wait_for_human_approval(result) -> bool:
    """CrewAI 没有原生 HITL —— 这里模拟"人工确认通过"。"""
    return True


class CustomerServiceFlow(Flow):
    @start()
    def classify_intent(self):
        return call_classifier(self.state["user_input"])

    @router(classify_intent)
    def route(self, intent):
        return f"{intent}_path"

    # ---------- 各 Crew 构造（角色 prompt 明牌） ----------
    def _build_kb_crew(self) -> "Crew":
        retriever = Agent(role="知识库检索员", goal="检索最相关文档", backstory="熟悉全部产品文档。", verbose=False)
        synthesizer = Agent(role="客服综合员", goal="用检索结果生成友好回复", backstory="说话专业又亲切。", verbose=False)
        t1 = Task(description="检索与问题相关的文档", expected_output="Top 文档列表", agent=retriever)
        t2 = Task(description="综合文档生成回复", expected_output="一段客服回复", agent=synthesizer, context=[t1])
        return Crew(agents=[retriever, synthesizer], tasks=[t1, t2], process=Process.sequential, memory=True, verbose=False)

    def _build_order_crew(self) -> "Crew":
        order_agent = Agent(role="订单专员", goal="查询订单并格式化", backstory="对订单系统了如指掌。", verbose=False)
        t = Task(description="查询订单状态并格式化回复", expected_output="订单状态回复", agent=order_agent)
        return Crew(agents=[order_agent], tasks=[t], process=Process.sequential, memory=True, verbose=False)

    def _build_complaint_crew(self) -> "Crew":
        ticket_agent = Agent(role="工单专员", goal="为投诉创建工单", backstory="严谨记录每一次投诉。", verbose=False)
        notify_agent = Agent(role="人工通知员", goal="通知人工客服跟进", backstory="确保投诉不遗漏。", verbose=False)
        t1 = Task(description="创建投诉工单", expected_output="工单号", agent=ticket_agent)
        t2 = Task(description="通知人工客服跟进", expected_output="通知结果", agent=notify_agent, context=[t1])
        return Crew(agents=[ticket_agent, notify_agent], tasks=[t1, t2], process=Process.sequential, memory=True, verbose=False)

    def _build_chitchat_crew(self) -> "Crew":
        chitchat_agent = Agent(role="闲聊客服", goal="礼貌得体地闲聊", backstory="亲和力拉满。", verbose=False)
        t = Task(description="礼貌回复用户闲聊", expected_output="一句友好回复", agent=chitchat_agent)
        return Crew(agents=[chitchat_agent], tasks=[t], process=Process.sequential, memory=True, verbose=False)

    def _run_or_mock(self, crew: "Crew", label: str):
        if HAS_REAL_KEY:
            return crew.kickoff(inputs={"query": self.state["user_input"]})
        return f"[{label} Crew 已构造，{len(crew.agents)} 个 Agent；设置 OPENAI_API_KEY 后 kickoff 输出真实回复]"

    # ---------- 4 条路径 ----------
    @listen("kb_path")
    def handle_kb(self):
        return self._run_or_mock(self._build_kb_crew(), "知识库")

    @listen("order_path")
    def handle_order(self):
        return self._run_or_mock(self._build_order_crew(), "订单")

    @listen("complaint_path")
    def handle_complaint(self):
        result = self._run_or_mock(self._build_complaint_crew(), "投诉")
        # CrewAI 没有原生 HITL，要自己拼挂起/恢复
        confirmation = wait_for_human_approval(result)
        return result if confirmation else "complaint cancelled"

    @listen("chitchat_path")
    def handle_chitchat(self):
        return self._run_or_mock(self._build_chitchat_crew(), "闲聊")


def main() -> None:
    if not HAS_REAL_KEY:
        print("未检测到真实 OPENAI_API_KEY：Flow 路由与 Crew 构造照常运行，仅不发起真实 kickoff。\n")
    for msg in ["我的订单到哪了", "这个功能怎么用", "我要投诉你们的服务", "在吗"]:
        flow = CustomerServiceFlow()
        result = flow.kickoff(inputs={"user_input": msg})
        print(f"{msg!r} → {result}")


if __name__ == "__main__":
    main()
