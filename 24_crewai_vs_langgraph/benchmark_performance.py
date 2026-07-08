"""性能对比脚本 —— 同一客服工作负载下 LangGraph vs CrewAI。

两个维度：
  1. 实测框架开销（wall-clock）：直接跑本目录两个真实实现（mock/无 key 模式），
     衡量"图执行 vs Flow+Crew 构造"的纯框架开销。
  2. 建模 LLM 调用数（真实成本驱动）：LangGraph 简单意图 0 次 LLM（纯 Python 路由），
     CrewAI 每个 Agent 一次 LLM 调用——这是延迟/成本差异的根源。

真实带 key 运行时，延迟主要由 LLM 调用数决定，与本脚本建模的 llm_calls 一致。

需要依赖：pip install langgraph crewai
"""
from __future__ import annotations

import importlib
import time

WORKLOAD = ["我的订单到哪了", "这个功能怎么用", "在吗", "我的物流呢", "为什么充不了值"]

# 每种意图，两个框架的 LLM 调用数（建模，来自文章实测口径）
LLM_CALLS = {
    #            LangGraph          CrewAI
    "order":    {"langgraph": 0, "crewai": 1},   # LG 纯 Python；Crew 1 个 agent
    "chitchat": {"langgraph": 0, "crewai": 1},
    "kb":       {"langgraph": 2, "crewai": 2},   # LG 只在 rerank/synthesize；Crew 2 agent
    "complaint":{"langgraph": 0, "crewai": 2},
}


def classify(text: str) -> str:
    t = text.lower()
    if "订单" in t or "物流" in t:
        return "order"
    if "投诉" in t or "举报" in t:
        return "complaint"
    if any(k in t for k in ["怎么", "为什么", "如何"]):
        return "kb"
    return "chitchat"


def bench_langgraph() -> float:
    try:
        lg = importlib.import_module("langgraph_customer_service")
    except SystemExit:
        return -1.0
    app = lg.build_app()
    t0 = time.perf_counter()
    for i, msg in enumerate(WORKLOAD):
        if classify(msg) == "complaint":
            continue  # 投诉走 HITL，不计入吞吐对比
        app.invoke({"user_input": msg}, config={"configurable": {"thread_id": f"bench_lg_{i}"}})
    return time.perf_counter() - t0


def bench_crewai() -> float:
    try:
        cs = importlib.import_module("crewai_customer_service")
    except SystemExit:
        return -1.0
    t0 = time.perf_counter()
    for msg in WORKLOAD:
        if classify(msg) == "complaint":
            continue
        flow = cs.CustomerServiceFlow()
        flow.kickoff(inputs={"user_input": msg})
    return time.perf_counter() - t0


def model_llm_calls() -> None:
    print("\n建模 LLM 调用数（真实成本/延迟驱动）：")
    lg_total = cr_total = 0
    for msg in WORKLOAD:
        intent = classify(msg)
        lg = LLM_CALLS[intent]["langgraph"]
        cr = LLM_CALLS[intent]["crewai"]
        lg_total += lg
        cr_total += cr
        print(f"  {msg!r:14} intent={intent:9} LangGraph={lg} 次  CrewAI={cr} 次")
    print(f"  合计：LangGraph {lg_total} 次 LLM  vs  CrewAI {cr_total} 次 LLM")
    if cr_total:
        save = (cr_total - lg_total) / cr_total * 100
        print(f"  → LangGraph 少约 {save:.0f}% LLM 调用（与文章'省 30-50% token'一致）")


def main() -> None:
    print("=== 实测框架开销（mock/无 key，仅框架本身） ===")
    lg_t = bench_langgraph()
    cr_t = bench_crewai()
    n = len([m for m in WORKLOAD if classify(m) != "complaint"])
    if lg_t >= 0:
        print(f"  LangGraph：{n} 次请求 {lg_t*1000:.1f} ms（{lg_t/n*1000:.2f} ms/req）")
    else:
        print("  LangGraph：未安装 langgraph，跳过")
    if cr_t >= 0:
        print(f"  CrewAI   ：{n} 次请求 {cr_t*1000:.1f} ms（{cr_t/n*1000:.2f} ms/req，含 Flow+Crew 构造）")
    else:
        print("  CrewAI   ：未安装 crewai，跳过")

    model_llm_calls()


if __name__ == "__main__":
    main()
