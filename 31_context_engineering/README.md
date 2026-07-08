# 31_context_engineering —— DeepAgents 三大 Context Engineering 模式

配套第 31 篇。三大模式（TODO 复述 / 虚拟文件系统 / 子 Agent 隔离）分别治长任务的三种病。

## 文章产物 → 文件对照表

| 文章承诺 | 文件 | 说明 |
|---------|------|------|
| 三大模式完整手搓实现 | `three_patterns.py` | `TodoBoard`(治漂移)/`VirtualFileSystem`+`file_reducer`(治溢出)/`SubAgentIsolation`(治冲突) |
| DeepAgents SDK 版本对照 | `sdk_comparison.py` | 手搓 ↔ Middleware 对照表；缺 `deepagents` 打印指引 |
| 超长任务端到端 demo（三大模式协同） | `long_task_end_to_end.py` | 可再生能源深度研究：规划→并行子Agent→上下文卸载→综合 |
| Context Engineering 性能对比脚本 | `performance_comparison.py` | 50 次工具调用下主上下文 token 无/有三大模式对比 |
| 章节连续项目入口 | `demo.py` | `SourcingAgentProject` 第 31 阶段（未改动） |

## 三大模式 ↔ 三种病

| 模式 | 治的病 | 机制 |
|------|--------|------|
| TODO 规划 + 复述 | Context Rot（漂移） | 全量覆盖 + 定期复述到上下文末尾 |
| 虚拟文件系统 | Context Overflow（溢出） | 上下文卸载：原文进文件，messages 只留摘要 |
| 子 Agent 隔离 | Context Clash（冲突） | messages 隔离、files 共享、todos 不传 |

## 运行

```bash
python3 31_context_engineering/three_patterns.py          # 无依赖
python3 31_context_engineering/long_task_end_to_end.py    # 无依赖
python3 31_context_engineering/performance_comparison.py  # 无依赖
python3 31_context_engineering/sdk_comparison.py          # 缺 deepagents 打印指引
python3 31_context_engineering/demo.py                    # 连续项目阶段入口
```

依赖可选：`pip install deepagents`。缺依赖时全部 exit 0，不联网。
