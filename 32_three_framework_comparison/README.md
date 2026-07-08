# 32_three_framework_comparison —— LangGraph vs CrewAI vs ADK 三框架横评

配套第 32 篇。同一个企业级采购助手（六步流程）在三个框架各实现一遍，逐维度量化对比。

## 文章产物 → 文件对照表

| 文章承诺 | 文件 | 说明 |
|---------|------|------|
| 同一采购助手 · LangGraph 实现 | `sourcing_langgraph.py` | 显式 State + 节点 + interrupt HITL；缺 langgraph 回退自研 StateGraph |
| 同一采购助手 · CrewAI 实现 | `sourcing_crewai.py` | 角色驱动 Agent/Task/Crew + 自拼 HITL；缺 crewai 回退自研 Crew |
| 同一采购助手 · ADK 实现 | `sourcing_adk.py` | Delegation + LoopAgent 级联 + Plugin + Event Sourcing；缺 google-adk 回退原语 |
| 共享业务定义（保证对比公平） | `sourcing_common.py` | 六步流程 + 数据 + 统一返回结构；采购目录复用系列，缺外部路径用内置副本 |
| 性能对比脚本 + Token 消耗对照 | `benchmark.py` | 本地实测耗时 + 文章 TTFT/Token 参考数据对照 |
| 8 维度评分自动化测试套件 | `scoring_suite.py` | unittest：加权平均、强项分布不重叠、三框架结论一致 |
| 章节连续项目入口 | `demo.py` | `SourcingAgentProject` 第 32 阶段（未改动） |

## 六步业务流程（三框架共享）

意图分类 → 需求收集 → 三级级联搜索（目录→供应商库→web）→ 重排合并 → 报价报告 Artifact → 大额转经理审批(HITL)

## 8 维度评分（文章加权口径）

| | LangGraph | CrewAI | ADK |
|---|---|---|---|
| 加权平均 | ≈4.1 | ≈2.8 | ≈4.1 |
| 强项 | 性能/持久化/HITL/调试 | 代码量/上手速度 | 可观测/可扩展/持久化 |

关键结论：三框架强项分布几乎不重叠，总分接近有误导性 —— 按项目最痛的点选型。

## 运行

```bash
python3 32_three_framework_comparison/sourcing_langgraph.py
python3 32_three_framework_comparison/sourcing_crewai.py
python3 32_three_framework_comparison/sourcing_adk.py
python3 32_three_framework_comparison/benchmark.py
python3 32_three_framework_comparison/scoring_suite.py   # 含 unittest 断言
python3 32_three_framework_comparison/demo.py            # 连续项目阶段入口
```

依赖可选：`pip install langgraph crewai google-adk`。缺任一都自动回退纯 Python 等价实现，exit 0，不联网。
