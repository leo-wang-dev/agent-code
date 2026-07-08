"""OpenHands 工具挂载完整示例 —— 给通用 Harness 挂自定义领域工具 + system prompt。

对应文章第 48 篇 三、技术上能用 Harness 做你的业务吗（美容助手例子）。

这里用一个**离线 mock Harness**演示"挂工具 + 注 prompt + 跑任务规划循环"的形态，
不联网、不依赖真实 OpenHands。生产替换为自部署 OpenHands（见 openhands_selfhost/）。

离线可跑：`python3 openhands_tools.py`
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass
class Tool:
    name: str
    description: str
    run: Callable[[dict], str]


# ---- 美容领域工具（对齐文章 custom_tools 例子）----

def _search_beauty_kb(args: dict) -> str:
    return f"[KB] 关于「{args.get('query')}」的权威资料：温和清洁 + 保湿 + 防晒是基础。"


def _ingredient_lookup(args: dict) -> str:
    return f"[成分] {args.get('name')}：有效但需建立耐受，孕期慎用。"


def _product_database(args: dict) -> str:
    return f"[产品] 匹配「{args.get('need')}」的 3 款：A(温和) / B(高效) / C(平价)。"


def _user_preference(args: dict) -> str:
    return "[偏好] 该用户：敏感肌 / 预算中等 / 偏好无香精。"


BEAUTY_TOOLS = [
    Tool("search_beauty_kb", "搜索美容知识库", _search_beauty_kb),
    Tool("ingredient_lookup", "查成分数据库", _ingredient_lookup),
    Tool("product_database", "查产品数据库", _product_database),
    Tool("user_preference", "读写用户偏好", _user_preference),
]

BEAUTY_SYSTEM_PROMPT = """你是一位资深美容顾问。回答用户问题时：
- 先 search_beauty_kb 找权威资料
- 涉及成分用 ingredient_lookup
- 推荐产品前先 user_preference
"""


@dataclass
class MockHarness:
    """离线 mock：具备"计划 → 调工具 → 汇总"的通用 Agent 容器形态。"""

    system_prompt: str
    tools: list[Tool]
    trace: list[str] = field(default_factory=list)

    def _tool(self, name: str) -> Tool:
        return next(t for t in self.tools if t.name == name)

    def run(self, task: str) -> dict:
        # 极简"规划"：按 system prompt 的顺序决定要调哪些工具
        plan = ["user_preference", "search_beauty_kb", "ingredient_lookup", "product_database"]
        self.trace.append(f"planner: 收到任务「{task}」，计划调用 {plan}")

        outputs = []
        for step in plan:
            tool = self._tool(step)
            args = {"query": task, "name": "视黄醇", "need": task}
            result = tool.run(args)
            self.trace.append(f"worker: {tool.name} → {result}")
            outputs.append(result)

        answer = "综合建议：先建立耐受，选温和产品，坚持防晒。"
        self.trace.append("reviewer: 已汇总，输出建议")
        return {"task": task, "answer": answer, "tool_outputs": outputs, "trace": self.trace}


def build_beauty_harness() -> MockHarness:
    """挂载美容工具 + 注入 system prompt（对齐文章部署形态）。

    生产替换（自部署 OpenHands）：
        from openhands.core import Agent
        agent = Agent(tools=custom_tools, system_prompt=custom_system_prompt)
    """
    return MockHarness(system_prompt=BEAUTY_SYSTEM_PROMPT, tools=BEAUTY_TOOLS)


def _demo() -> None:
    harness = build_beauty_harness()
    print("=== 挂载的工具 ===")
    for t in harness.tools:
        print(f"  - {t.name}: {t.description}")

    print("\n=== 跑一个美容咨询任务 ===")
    result = harness.run("我想开始用视黄醇，敏感肌能用吗")
    for line in result["trace"]:
        print("  " + line)
    print("\n最终建议:", result["answer"])


if __name__ == "__main__":
    _demo()
