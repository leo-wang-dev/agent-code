"""Service 注入对比 —— InMemory（开发） vs Database/File（生产）。

对应文章第二节"Runner —— 运行时"里的显式 Service 注入设计。

Runner 显式注入三类 Service：
    session_service   会话持久化   InMemory / Database
    artifact_service  产物管理     InMemory / File / GCS
    memory_service    长期记忆搜索  InMemory / Vertex AI Memory

Service 化的意义：开发时用 InMemory，生产时换 Database/Cloud —— 零代码改动。

真实 ADK 写法：
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService, DatabaseSessionService
    runner = Runner(
        app=app,
        session_service=DatabaseSessionService(db_url="sqlite+aiosqlite:///x.db"),
        artifact_service=FileArtifactService(root_dir="./artifacts"),
        memory_service=InMemoryMemoryService(),
    )

本脚本用确定性 mock 复刻"同一套 Service 接口、两套实现（dev/prod）"，
演示 Runner 组装代码完全不变，只换注入的实现。
"""

from __future__ import annotations

import sys
from typing import Protocol

try:  # google-adk 导入 try/except 保护
    from google.adk.runners import Runner  # noqa: F401

    HAS_ADK = True
except ImportError:
    HAS_ADK = False


# ---- 统一接口（Protocol）：dev / prod 两套实现都遵守它 ----
class SessionService(Protocol):
    def save(self, session_id: str, event: str) -> None: ...
    def backend(self) -> str: ...


class InMemorySessionService:
    """开发实现：进程内存，重启即失。"""

    def __init__(self) -> None:
        self._data: dict[str, list[str]] = {}

    def save(self, session_id: str, event: str) -> None:
        self._data.setdefault(session_id, []).append(event)

    def backend(self) -> str:
        return "内存（dict）—— 重启丢失，仅供开发"


class DatabaseSessionService:
    """生产实现：落库持久化（此处 mock 成 SQL 语句流，不真连库）。"""

    def __init__(self, db_url: str) -> None:
        self.db_url = db_url
        self.sql_log: list[str] = []

    def save(self, session_id: str, event: str) -> None:
        self.sql_log.append(
            f"INSERT INTO events(session_id, payload) VALUES ('{session_id}', '{event}')"
        )

    def backend(self) -> str:
        return f"数据库（{self.db_url}）—— 持久化，生产可用"


class InMemoryArtifactService:
    def backend(self) -> str:
        return "内存 artifact"


class FileArtifactService:
    def __init__(self, root_dir: str) -> None:
        self.root_dir = root_dir

    def backend(self) -> str:
        return f"文件系统 artifact（{self.root_dir}）"


class Runner:  # mock：与 ADK Runner 同名，显式注入 Service
    def __init__(self, app_name, session_service, artifact_service) -> None:
        self.app_name = app_name
        self.session_service = session_service
        self.artifact_service = artifact_service

    def run_once(self, session_id: str, message: str) -> None:
        self.session_service.save(session_id, f"user:{message}")
        self.session_service.save(session_id, "agent:已处理")


def describe(label: str, runner: "Runner") -> None:
    print(f"== {label} ==")
    print(f"  session_service : {runner.session_service.backend()}")
    print(f"  artifact_service: {runner.artifact_service.backend()}")
    runner.run_once("s1", "你好")


def main() -> int:
    if not HAS_ADK:
        print("[提示] 未检测到 google-adk，使用确定性 mock 演示 Service 注入对比。")
        print("       安装： pip install google-adk")
        print("-" * 60)

    # 关键：Runner 组装代码在 dev/prod 完全一致，只换注入的 Service 实现
    dev_runner = Runner(
        app_name="demo",
        session_service=InMemorySessionService(),
        artifact_service=InMemoryArtifactService(),
    )
    describe("开发环境（InMemory）", dev_runner)

    prod_runner = Runner(
        app_name="demo",
        session_service=DatabaseSessionService(db_url="sqlite+aiosqlite:///sessions.db"),
        artifact_service=FileArtifactService(root_dir="./artifacts"),
    )
    describe("\n生产环境（Database/File）", prod_runner)

    print("\n== 生产 session_service 实际产生的持久化操作 ==")
    for sql in prod_runner.session_service.sql_log:  # type: ignore[attr-defined]
        print(f"  {sql}")

    print("\n结论：切换开发/生产 = 只改注入的 Service 实现，Runner/Agent/Tool 代码零改动。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
