"""成本归因仪表盘 —— 把每次 LLM 调用的 Token 按 用户 / Agent / 模型 / 类型拆分记录。

对应文章第 43 篇《Token 成本拆解 + Prompt 压缩》一、五大成本源 + 成本归因怎么做。

离线可运行：`python3 cost_attribution.py`
- 记录若干次模拟调用（每次拆 6 类 token）；
- 按 Agent、按 Token 类型聚合，打印和文章一样的归因报表。
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _tokens import cost_usd, estimate_tokens  # noqa: E402

# 一次 LLM 调用的 6 类 token 构成（文章第一节）
TOKEN_KINDS = (
    "system_prompt",
    "tool_desc",
    "history",
    "rag_context",
    "user_input",
    "output",
)


@dataclass
class CallContext:
    """一次调用的上下文——每一块都单独可估算 token。"""

    user_id: str
    agent_name: str
    model: str
    system_prompt: str = ""
    tool_descriptions: str = ""
    history: str = ""
    rag_context: str = ""
    user_input: str = ""
    output: str = ""

    def token_breakdown(self) -> dict[str, int]:
        return {
            "system_prompt": estimate_tokens(self.system_prompt),
            "tool_desc": estimate_tokens(self.tool_descriptions),
            "history": estimate_tokens(self.history),
            "rag_context": estimate_tokens(self.rag_context),
            "user_input": estimate_tokens(self.user_input),
            "output": estimate_tokens(self.output),
        }


@dataclass
class CostAttribution:
    """成本归因收集器——记录每次调用，聚合出多维报表。"""

    records: list[dict] = field(default_factory=list)

    def log_call(self, ctx: CallContext) -> dict:
        breakdown = ctx.token_breakdown()
        input_tokens = sum(breakdown[k] for k in TOKEN_KINDS if k != "output")
        output_tokens = breakdown["output"]
        record = {
            "user_id": ctx.user_id,
            "agent_name": ctx.agent_name,
            "model": ctx.model,
            "tokens": breakdown,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": round(cost_usd(ctx.model, input_tokens, output_tokens), 6),
        }
        self.records.append(record)
        return record

    def by_agent(self) -> dict[str, float]:
        agg: dict[str, float] = {}
        for r in self.records:
            agg[r["agent_name"]] = agg.get(r["agent_name"], 0.0) + r["cost_usd"]
        return dict(sorted(agg.items(), key=lambda kv: kv[1], reverse=True))

    def by_token_kind(self, agent_name: str | None = None) -> dict[str, float]:
        agg = {k: 0.0 for k in TOKEN_KINDS}
        for r in self.records:
            if agent_name and r["agent_name"] != agent_name:
                continue
            model = r["model"]
            for k in TOKEN_KINDS:
                # 输出用 output 价，其余用 input 价
                if k == "output":
                    agg[k] += cost_usd(model, 0, r["tokens"][k])
                else:
                    agg[k] += cost_usd(model, r["tokens"][k], 0)
        return agg

    def total_cost(self) -> float:
        return round(sum(r["cost_usd"] for r in self.records), 6)


def _pct(value: float, total: float) -> str:
    return f"{(value / total * 100):.0f}%" if total else "0%"


def _demo() -> None:
    attr = CostAttribution()

    # 模拟三个 Agent 的调用负载
    for _ in range(42):
        attr.log_call(CallContext(
            user_id="u_client",
            agent_name="customer_service",
            model="gpt-4o",
            system_prompt="你是企业客服助手。规则：礼貌 / 简洁 / 基于公司政策。" * 20,
            tool_descriptions="query_customer / query_order / refund / escalate" * 15,
            history="用户：我的订单到哪了？助手：正在为您查询……" * 12,
            rag_context="退货政策：30 天内无损坏可退。运费由……" * 10,
            user_input="我要退货",
            output="好的，请提供订单号，我帮您查询退货资格。" * 3,
        ))
    for _ in range(27):
        attr.log_call(CallContext(
            user_id="u_dev",
            agent_name="code_assistant",
            model="claude-3-5-sonnet",
            system_prompt="You are a coding assistant." * 18,
            tool_descriptions="read_file / write_file / run_tests" * 12,
            history="user: fix the bug\nassistant: reading the file..." * 8,
            rag_context="",
            user_input="修复这个报错",
            output="def fix():\n    return True" * 6,
        ))
    for _ in range(21):
        attr.log_call(CallContext(
            user_id="u_research",
            agent_name="research",
            model="gpt-4o-mini",
            system_prompt="你是研究助手。" * 10,
            tool_descriptions="web_search / fetch_url" * 8,
            history="",
            rag_context="论文摘要：LLMLingua 用小模型压缩 prompt……" * 20,
            user_input="总结这几篇论文",
            output="三篇论文的共同点是……" * 8,
        ))

    total = attr.total_cost()
    print("=" * 52)
    print(f"[本月成本归因]  合计 ${total:.4f}")
    print("-" * 52)
    print("按 Agent:")
    by_agent = attr.by_agent()
    for name, cost in by_agent.items():
        print(f"  {name:<18} ${cost:>8.4f} ({_pct(cost, total)})")

    print("-" * 52)
    print("按 Token 类型 (customer_service):")
    by_kind = attr.by_token_kind("customer_service")
    kind_total = sum(by_kind.values())
    for kind, cost in sorted(by_kind.items(), key=lambda kv: kv[1], reverse=True):
        print(f"  {kind:<16} ${cost:>8.4f} ({_pct(cost, kind_total)})")

    fixed = by_kind["system_prompt"] + by_kind["tool_desc"]
    print("-" * 52)
    print(f"固定开销 (System Prompt + Tool Desc) 占比: {_pct(fixed, kind_total)}")
    print("=> 优化 ROI 最高的方向就是这两块（文章结论）。")


if __name__ == "__main__":
    _demo()
