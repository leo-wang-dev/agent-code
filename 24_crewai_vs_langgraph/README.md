# 24 CrewAI vs LangGraph：同一个客服系统两种实现

配套文章：《CrewAI vs LangGraph：同一个客服系统两种实现》

同一个中等复杂度客服 Agent（4 种意图：知识库/订单/投诉/闲聊，其中投诉需 HITL），
分别用 CrewAI 和 LangGraph 各写一遍，再做性能、Token 成本对照，给出 6 维度选型决策器。

## 安装依赖

```bash
pip install langgraph crewai
```

- 缺少依赖时脚本打印安装提示并以退出码 0 退出，不崩溃。
- `token_cost_comparison.py` 和 `decision_advisor.py` **纯 stdlib、零依赖**，任何环境直接运行。
- 涉及 CrewAI 的脚本在无 `OPENAI_API_KEY` 时用占位 key 构造对象、跑通 Flow 路由，仅不发起真实 `kickoff()`；LangGraph 脚本全程 mock 逻辑，无需密钥即可端到端运行（含 HITL）。

## 文件对照表

| 文件 | 对应产物 | 说明 | 依赖 |
|------|----------|------|------|
| `langgraph_customer_service.py` | 客服系统 LangGraph 版 | StateGraph + KB 子图 + 投诉子图(interrupt HITL) + Checkpoint | langgraph |
| `crewai_customer_service.py` | 客服系统 CrewAI 版 | Flow 路由 + 4 个 Crew + memory + 自拼 HITL | crewai |
| `benchmark_performance.py` | 性能对比脚本 | 实测框架开销 + 建模 LLM 调用数 | langgraph+crewai |
| `token_cost_comparison.py` | Token 成本对照 | 按意图分布建模两框架 token/费用 | 无（stdlib） |
| `decision_advisor.py` | 6 维度选型决策器 | 纯 stdlib CLI，加权打分给推荐 | 无（stdlib） |
| `hybrid_langgraph_crewai.py` | 混合使用示例 | LangGraph 主图 + content 节点内嵌 CrewAI Crew | langgraph+crewai |
| `demo.py` | 章节统一入口 | 委托 `series_projects.chapter_runner` | — |

## 运行

```bash
python3 token_cost_comparison.py          # 零依赖
python3 decision_advisor.py               # 零依赖，跑内置画像
python3 decision_advisor.py --interactive # 逐题自测你的项目
python3 decision_advisor.py --flow complex --hitl yes --persist yes \
        --sideeffect yes --team large --cost high   # 直接给 6 维答案
python3 langgraph_customer_service.py      # 含 HITL 全流程
python3 benchmark_performance.py           # 两框架对比
python3 hybrid_langgraph_crewai.py         # 混用
```

## 6 个选型维度

`decision_advisor.py` 的 6 个维度（正分偏 LangGraph、负分偏 CrewAI）：

1. `flow` 流程复杂度：简单可枚举→CrewAI；复杂分支/循环/嵌套→LangGraph
2. `hitl` 是否必须人工审批：需要→LangGraph（原生 interrupt）
3. `persist` 是否需要节点级持久化/故障恢复/审计：需要→LangGraph
4. `sideeffect` 是否涉及金钱/数据操作/合规：涉及→LangGraph
5. `team` 团队与上线速度：小团队/缺 Agent 工程师/要快→CrewAI
6. `cost` 延迟/Token 成本敏感度：高度敏感→LangGraph

## 核心认知

- 两框架都能做中等复杂度客服；CrewAI 代码略少、新人上手快、角色 prompt 明牌、Memory 零配置；LangGraph 路由确定性强、HITL 原生、Checkpoint 可追溯、Token 成本低。
- CrewAI 的弱项正是 LangGraph 的强项：HITL、节点级持久化/审计、复杂条件分支。
- 选型经验：不确定时选 LangGraph——复杂度上限更高，能覆盖 80% 的 CrewAI 场景；"从 CrewAI 重构到 LangGraph"常见，反向极少。
- 工业级真实做法是混用：LangGraph 管主流程/状态/持久化/HITL，CrewAI 管子任务里的多 Agent 协作。
