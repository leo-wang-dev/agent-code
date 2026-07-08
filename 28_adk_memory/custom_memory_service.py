"""Memory Service 自定义实现示例 —— 跨会话长期记忆的显式 Service 接口。

对应文章第三节"Memory Service"。

ADK 的 MemoryService 是显式接口：开发用 InMemoryMemoryService，
生产用 VertexAiMemoryService，也可以自定义对接 Mem0 / pgvector / 自家系统。
工具里通过 tool_context.search_memory(query) 触发语义检索。

本脚本定义一个 MemoryService 抽象接口，给出两个实现：
    InMemoryMemoryService  —— 关键词/词重叠打分（确定性，无需向量库/网络）
    KeywordMemoryService   —— "自定义实现"示例（可类比对接 Mem0）
并演示工具通过 search_memory 召回历史。
"""

from __future__ import annotations

import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

try:  # google-adk 导入 try/except 保护
    from google.adk.memory import InMemoryMemoryService as _Real  # noqa: F401

    HAS_ADK = True
except ImportError:
    HAS_ADK = False


@dataclass
class MemoryRecord:
    user_id: str
    session_id: str
    text: str


class BaseMemoryService(ABC):
    """对齐 ADK MemoryService 的显式接口。"""

    @abstractmethod
    def add(self, record: MemoryRecord) -> None: ...

    @abstractmethod
    def search(self, user_id: str, query: str, top_k: int = 3) -> list[str]: ...


def _overlap_score(a: str, b: str) -> int:
    """确定性打分：字符 bigram 重叠数（代替向量相似度，无需模型）。"""
    grams_a = {a[i:i + 2] for i in range(len(a) - 1)}
    grams_b = {b[i:i + 2] for i in range(len(b) - 1)}
    return len(grams_a & grams_b)


class InMemoryMemoryService(BaseMemoryService):
    """开发/测试实现：进程内 list + 确定性词重叠检索。"""

    def __init__(self) -> None:
        self._records: list[MemoryRecord] = []

    def add(self, record: MemoryRecord) -> None:
        self._records.append(record)

    def search(self, user_id: str, query: str, top_k: int = 3) -> list[str]:
        scored = [
            (_overlap_score(query, r.text), r.text)
            for r in self._records if r.user_id == user_id
        ]
        scored = [(s, t) for s, t in scored if s > 0]
        scored.sort(key=lambda x: (-x[0], x[1]))
        return [t for _, t in scored[:top_k]]


class KeywordMemoryService(BaseMemoryService):
    """自定义实现示例（可类比对接 Mem0 / pgvector）：倒排关键词命中。"""

    def __init__(self) -> None:
        self._records: list[MemoryRecord] = []

    def add(self, record: MemoryRecord) -> None:
        self._records.append(record)

    def search(self, user_id: str, query: str, top_k: int = 3) -> list[str]:
        hits = [r.text for r in self._records
                if r.user_id == user_id and any(ch in r.text for ch in query)]
        return hits[:top_k]


# ---- 工具通过 ToolContext.search_memory 触发检索 ----
@dataclass
class ToolContext:
    user_id: str
    memory_service: BaseMemoryService

    def search_memory(self, query: str) -> list[str]:
        return self.memory_service.search(self.user_id, query)


def recall_user_history(query: str, tool_context: ToolContext) -> dict:
    return {"historical": tool_context.search_memory(query)}


def seed(service: BaseMemoryService) -> None:
    for text in [
        "用户上个月投诉物流太慢",
        "用户偏好中文回复且不喜欢营销话术",
        "用户是 VIP 会员，购买过三次",
        "用户对 ADK 的事件流很感兴趣",
    ]:
        service.add(MemoryRecord("u1", "sess_old", text))


def main() -> int:
    if not HAS_ADK:
        print("[提示] 未检测到 google-adk，使用确定性词重叠 mock 复刻 MemoryService。")
        print("       安装： pip install google-adk")
        print("-" * 60)

    for name, service in [("InMemoryMemoryService", InMemoryMemoryService()),
                          ("KeywordMemoryService(自定义)", KeywordMemoryService())]:
        seed(service)
        ctx = ToolContext("u1", service)
        print(f"== {name} ==")
        for q in ["物流", "ADK 事件流"]:
            print(f"   search_memory({q!r}) ->", recall_user_history(q, ctx)["historical"])
        print()

    print("对应第 16-18 篇 Memory 工程：抽取/遗忘由你实现，Service 只给检索+存储接口。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
