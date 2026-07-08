"""超长任务端到端 demo —— 三大模式协同跑「深度研究」。

对应文章第 31 篇「四、三大模式协同应对长任务」。

任务：研究可再生能源的成本、环保影响、采用率，然后综合分析。
流程：TODO 规划(治漂移) -> 子 Agent 并行(治冲突) -> 上下文卸载(治溢出) -> 综合。

纯标准库，确定性可复现：
    python3 31_context_engineering/long_task_end_to_end.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from three_patterns import SubAgent, SubAgentIsolation, TodoBoard, VirtualFileSystem  # noqa: E402


def _make_research_subagent(topic: str, filename: str) -> SubAgent:
    def runner(description: str, shared: VirtualFileSystem) -> str:
        # 子 Agent 内部：多次「搜索」，每次 8000 字原文卸载到文件，只留摘要。
        for i in range(6):  # 模拟 5-10 次搜索
            big = f"{topic} 搜索结果第{i}段：" + ("原始数据" * 1000)
            shared.offload_tool_result(f"{topic}_raw_{i}.md", big, f"{topic} 第{i}段已卸载")
        summary = f"# {topic} 综合\n{topic}方面结论：数据向好、趋势明确"
        shared.write_file(filename, summary)
        return f"已完成{topic}研究，详见 {filename}"

    return SubAgent(name=f"research-{topic}", runner=runner)


def run() -> dict[str, object]:
    fs = VirtualFileSystem()
    board = TodoBoard()
    iso = SubAgentIsolation(fs)

    # Step 1：TODO 规划（治漂移）
    board.write_todos(["研究成本", "研究环保影响", "研究采用率", "综合分析"])

    # Step 2 + 3：子 Agent 并行 + 各自内部上下文卸载（治冲突 + 治溢出）
    plan = [("成本", "costs_summary.md"), ("环保", "impact_summary.md"), ("采用率", "adoption_summary.md")]
    for idx, (topic, fname) in enumerate(plan):
        iso.register(_make_research_subagent(topic, fname))
        iso.task(f"research-{topic}", f"Research renewable energy {topic}")
        board.complete(idx)

    # Step 4：综合分析（按需读摘要文件，不是全塞上下文）
    board.complete(3)
    synthesis_inputs = [fs.read_file(fname) for _, fname in plan]
    final_report = "# 可再生能源综合报告\n\n" + "\n\n".join(synthesis_inputs)
    fs.write_file("final_report.md", final_report)

    # 工程量化：主 Agent 上下文只看到摘要，原文全在文件里。
    total_files = fs.ls()
    raw_files = [f for f in total_files if "_raw_" in f]
    main_context_chars = sum(len(fs.read_file(fname)) for _, fname in plan)  # 主 Agent 实际读入
    offloaded_chars = sum(len(fs.read_file(f)) for f in raw_files)  # 被卸载、未进主上下文

    return {
        "todos": board.read_todos(),
        "files_total": len(total_files),
        "raw_files_offloaded": len(raw_files),
        "main_context_chars": main_context_chars,
        "offloaded_chars": offloaded_chars,
        "isolation_log": iso.isolation_log,
        "final_report_head": final_report[:80],
    }


def main() -> None:
    result = run()
    print("=== 超长任务端到端（三大模式协同）===")
    print(result["todos"])
    print(f"\n虚拟文件系统共 {result['files_total']} 个文件，其中 {result['raw_files_offloaded']} 个是被卸载的原文")
    print(f"主 Agent 实际读入上下文：约 {result['main_context_chars']} 字")
    print(f"被卸载、从未进入主上下文：约 {result['offloaded_chars']} 字")
    saved = result["offloaded_chars"] / max(1, result["main_context_chars"] + result["offloaded_chars"])
    print(f"上下文卸载率：{saved:.0%}（这些原文若全塞 messages，主上下文会溢出）")
    print("\n三个子 Agent 完全隔离运行：")
    for line in result["isolation_log"]:
        print("  -", line)
    print("\n最终报告开头：", result["final_report_head"])


if __name__ == "__main__":
    main()
