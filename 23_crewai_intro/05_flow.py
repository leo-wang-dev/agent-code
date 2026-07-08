"""Flow 完整实现示例 —— 当 Crew 不够用时的逃生口。

Sequential / Hierarchical 都表达不了"条件分支"。CrewAI 的 Flow 是显式流程控制层：
  @start()  流程入口
  @router() 根据返回值路由到不同路径
  @listen() 监听某条路径并处理（路径里再调具体的 Crew 干活）

Flow 的路由是纯 Python 控制流，可脱离 LLM 直接运行。这里 @start 用本地分类器替代
call_llm、各 @listen 返回 mock（真实场景里 return crew.kickoff(...)），无需密钥即可跑通。

需要依赖：pip install crewai
"""
from __future__ import annotations

import os

os.environ.setdefault("OPENAI_API_KEY", "sk-demo-placeholder")
os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")
os.environ.setdefault("CREWAI_TELEMETRY_OPT_OUT", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")

try:
    from crewai.flow.flow import Flow, start, listen, router
except ImportError:
    print("需要先安装依赖：pip install crewai")
    print("（本示例演示 Flow 条件分支，缺少 crewai 无法运行）")
    raise SystemExit(0)


def classify_query(query: str) -> str:
    """真实场景是 call_llm 分类意图，这里用本地规则替代。"""
    if "查" in query or "search" in query.lower():
        return "search"
    if "报价" in query or "价格" in query:
        return "quote"
    return "chitchat"


class CustomerServiceFlow(Flow):
    @start()
    def classify_intent(self):
        intent = classify_query(self.state["query"])
        print(f"  [start] 意图分类：{self.state['query']!r} → {intent}")
        return intent

    @router(classify_intent)
    def route(self, intent):
        if intent == "search":
            return "search_path"
        elif intent == "quote":
            return "quote_path"
        return "chitchat_path"

    @listen("search_path")
    def handle_search(self):
        # 真实场景：crew = build_search_crew(); return crew.kickoff(inputs=...)
        return "已走搜索 Crew 处理并返回结果"

    @listen("quote_path")
    def handle_quote(self):
        return "已走报价 Crew 处理并返回结果"

    @listen("chitchat_path")
    def handle_chitchat(self):
        return "已走闲聊 Crew 处理并返回结果"


def run(query: str) -> None:
    flow = CustomerServiceFlow()
    result = flow.kickoff(inputs={"query": query})
    print(f"  Flow 最终结果：{result}\n")


def main() -> None:
    print("CrewAI Flow 条件分支演示（Flow 正在向 LangGraph 的代码控制流收敛）：\n")
    for q in ["帮我查一下订单", "这台多少钱报价一下", "在吗"]:
        run(q)


if __name__ == "__main__":
    main()
