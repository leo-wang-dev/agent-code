"""Artifact 版本化管理完整例子 —— save_artifact / load_artifact。

对应文章第四节"Artifacts —— 版本化产物管理"。

每次 save_artifact 都创建新版本，旧版本永远保留。底层文件组织：
    data/artifacts/{app}/{user}/{session}/report.md.0   <- v0
                                          report.md.1   <- v1
                                          report.md.2   <- v2(最新)

ADK 的 ArtifactService 显式接口：InMemory / File / 自定义(GCS/S3/OSS)。
本脚本实现一个 InMemoryArtifactService（确定性，无需真实文件系统/网络），
演示存多版、读最新、读指定版本，并对照 state["report"] 的差别。
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field


class InMemoryArtifactService:
    """对齐 ADK ArtifactService：每次 save 追加新版本。"""

    def __init__(self) -> None:
        # key = (app, user, session, name) -> [v0, v1, ...]
        self._store: dict[tuple, list[str]] = {}

    def _key(self, scope, name):
        return (scope["app"], scope["user"], scope["session"], name)

    def save(self, scope, name: str, content: str) -> int:
        versions = self._store.setdefault(self._key(scope, name), [])
        versions.append(content)
        return len(versions) - 1  # 版本号从 0 起

    def load(self, scope, name: str, version: int | None = None) -> str | None:
        versions = self._store.get(self._key(scope, name))
        if not versions:
            return None
        return versions[-1] if version is None else versions[version]

    def list_paths(self, scope) -> list[str]:
        paths = []
        for (app, user, session, name), versions in self._store.items():
            for v in range(len(versions)):
                paths.append(f"data/artifacts/{app}/{user}/{session}/{name}.{v}")
        return paths


@dataclass
class ToolContext:
    scope: dict
    artifact_service: InMemoryArtifactService

    def save_artifact(self, name: str, content: str) -> int:
        return self.artifact_service.save(self.scope, name, content)

    def load_artifact(self, name: str, version: int | None = None) -> str | None:
        return self.artifact_service.load(self.scope, name, version)


try:  # google-adk 导入 try/except 保护
    from google.adk.artifacts import InMemoryArtifactService as _Real  # noqa: F401

    HAS_ADK = True
except ImportError:
    HAS_ADK = False


def generate_report(tool_context: ToolContext) -> dict:
    v0 = tool_context.save_artifact("report.md", "Draft v0：初稿")
    v1 = tool_context.save_artifact("report.md", "Improved v1：补充数据")
    v2 = tool_context.save_artifact("report.md", "Final v2：定稿")
    return {"latest_version": v2, "kept": [v0, v1]}


def main() -> int:
    if not HAS_ADK:
        print("[提示] 未检测到 google-adk，使用确定性 mock ArtifactService 演示版本化。")
        print("       安装： pip install google-adk")
        print("-" * 60)

    ctx = ToolContext(
        scope={"app": "reporter", "user": "u1", "session": "s1"},
        artifact_service=InMemoryArtifactService(),
    )

    print("== 生成报告（存 3 版） ==")
    print("  ", generate_report(ctx))

    print("\n== 读取 ==")
    print("   最新版:", ctx.load_artifact("report.md"))
    print("   v0    :", ctx.load_artifact("report.md", version=0))
    print("   v1    :", ctx.load_artifact("report.md", version=1))

    print("\n== 底层文件组织（旧版永久保留） ==")
    for p in ctx.artifact_service.list_paths(ctx.scope):
        print("  ", p)

    print("\n== Artifact vs state['report'] ==")
    print("   Artifact : 大文件友好 / 自动版本化 / 可下载 / 独立存储")
    print("   state    : 只适合小块结构化数据，覆盖式无历史")
    return 0


if __name__ == "__main__":
    sys.exit(main())
