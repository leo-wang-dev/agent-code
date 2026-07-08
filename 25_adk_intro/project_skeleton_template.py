"""ADK 标准项目骨架模板生成器。

对应文章第三节"ADK 的工程骨架 —— 一个推荐的项目结构"。

用法：
    python3 project_skeleton_template.py            # 只打印骨架树（dry-run）
    python3 project_skeleton_template.py ./my_adk_app   # 在指定目录生成骨架

不依赖 google-adk：这是一个纯脚手架工具，帮你把文章推荐的目录结构落地。
生成的每个包目录带 __init__.py，入口文件带最小可读注释。
"""

from __future__ import annotations

import sys
from pathlib import Path

# 文章推荐的四层目录结构：编排 / 认知 / 行动 / 记忆 + 工程支撑目录
SKELETON: dict[str, str] = {
    "apps/__init__.py": "",
    "apps/main.py": (
        '"""Runner 启动点。"""\n\n'
        "# from google.adk.runners import Runner\n"
        "# from .app import app\n"
    ),
    "apps/app.py": (
        '"""App 配置：组装 root_agent。"""\n\n'
        "# from google.adk.app import App\n"
        "# from agents.researcher import researcher\n"
        "# app = App(name='demo', root_agent=researcher)\n"
    ),
    "agents/__init__.py": "",
    "agents/researcher.py": "# 认知层：LlmAgent 定义\n",
    "agents/writer.py": "# 认知层：引用 {research_notes} 数据总线\n",
    "agents/reviewer.py": "# 认知层：审校 Agent\n",
    "tools/__init__.py": "",
    "tools/search_tool.py": "# 行动层：普通函数 + 类型标注，ADK 自动生成 Schema\n",
    "tools/file_tool.py": "# 行动层：文件工具\n",
    "tools/api_tool.py": "# 行动层：外部 API 工具\n",
    "workflows/__init__.py": "",
    "workflows/sequential_pipeline.py": "# 编排层：SequentialAgent\n",
    "workflows/parallel_research.py": "# 编排层：ParallelAgent\n",
    "workflows/delegation.py": "# 编排层：Delegation 动态路由\n",
    "skills/__init__.py": "# 知识包（第 28 篇）\n",
    "callbacks/__init__.py": "# 可观测性回调（第 27 篇）\n",
    "plugins/__init__.py": "# 全局横切扩展（第 29 篇）\n",
    "data/.gitkeep": "",
    "docs/architecture.md": "# 架构图与流程说明\n",
    "tests/__init__.py": "# 评测（第 29 篇）\n",
}

# 目录职责对照，用于打印说明
LAYERS = [
    ("apps/", "入口层", "Runner 启动点 + App 配置"),
    ("agents/", "认知层", "LlmAgent：思考和决策"),
    ("tools/", "行动层", "普通函数：调用外部世界"),
    ("workflows/", "编排层", "Sequential/Parallel/Loop/Delegation"),
    ("skills/", "知识包", "Phase 5 引入（第 28 篇）"),
    ("callbacks/", "可观测性", "日志/安全（第 27 篇）"),
    ("plugins/", "全局扩展", "横切策略（第 29 篇）"),
    ("data/", "模拟数据", "配置 / mock 数据"),
    ("docs/", "文档", "架构图与流程说明"),
    ("tests/", "评测", "第 29 篇"),
]


def print_tree() -> None:
    print("ADK 标准项目骨架（文章推荐结构）：\n")
    print("project/")
    for path, layer, desc in LAYERS:
        print(f"├── {path:<14} ← {layer}：{desc}")
    print("\n三大工程价值：职责清晰 / 复用性强 / 演进路径明确。")


def scaffold(root: Path) -> int:
    if root.exists() and any(root.iterdir()):
        print(f"[跳过] 目标目录 {root} 非空，未做任何写入（避免覆盖已有文件）。")
        return 0
    for rel, content in SKELETON.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    print(f"[完成] 已在 {root} 生成 {len(SKELETON)} 个文件的 ADK 骨架。")
    return 0


def main(argv: list[str]) -> int:
    print_tree()
    if len(argv) >= 2:
        root = Path(argv[1]).resolve()
        print(f"\n即将在 {root} 生成骨架…")
        return scaffold(root)
    print("\n（dry-run：未传目标目录，仅打印。传一个路径即可生成，例如："
          " python3 project_skeleton_template.py ./my_adk_app）")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
