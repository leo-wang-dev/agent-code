# 08 多 Agent 的本质 — 配套代码

对应文章《多 Agent 的本质：把大问题拆给一群小工人》。

多 Agent 系统 = 多个单 Agent + 明确的协作协议。本目录把文章承诺的每个具名
产物落成可离线运行的文件（Agent 用确定性函数替身，无需 API key）。

## 产物对照表

| 文章承诺 | 文件 | 说明 |
| --- | --- | --- |
| Pipeline | `pipeline.py` | 检索→提纲→写作→审稿的固定流程流转 |
| Orchestrator-Worker | `orchestrator_worker.py` | 总控按意图路由分派、汇总，生产最稳 |
| Peer-to-Peer | `peer_to_peer.py` | 对等讨论 + 外层 max_rounds/收敛强制收束 |
| 共享状态 vs 消息传递 | `state_vs_message.py` | 两条协作路并排对照 |
| 事实校验 | `fact_verifier.py` | 汇总前带来源核验，阻断幻觉传播 |
| Token 预算 | `token_budget.py` | 全局共享预算池，非每 Agent 各管各的 |
| 协调风暴检测器 | `coordination_storm_detector.py` | 统计回询次数，识别协调成本失控 |
| 汇总入口 | `run_demo.py` | 原有委托 `src/agent_code` 的组合 demo |

## 运行

```bash
python3 08_multi_agent/pipeline.py
python3 08_multi_agent/orchestrator_worker.py
python3 08_multi_agent/peer_to_peer.py
python3 08_multi_agent/state_vs_message.py
python3 08_multi_agent/fact_verifier.py
python3 08_multi_agent/token_budget.py
python3 08_multi_agent/coordination_storm_detector.py
python3 08_multi_agent/run_demo.py
```

## 复用关系

底层能力在 `src/agent_code/multi_agent.py`（`Pipeline` / `OrchestratorWorker` /
`PeerToPeer` / `SharedState` / `MessageBus` / `FactVerifier` /
`MultiAgentTokenBudget` / `CoordinationStormDetector`）。本目录的文件是面向文章
具名产物的、可单独运行的教学封装。
