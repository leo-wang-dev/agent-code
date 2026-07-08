# 《工业级 AI Agent 开发实战》配套代码 · 学习指南

这是公众号系列《工业级 AI Agent 开发实战》的**公开配套代码**。文章正文为付费内容，本仓库只放可运行的代码。

**代码和文章一一对应**：一篇文章 = 一个目录（如第 13 篇 Chunking → `13_chunking/`）。目录里每个文件对应文章里讲的一个知识点，打开该目录的 `README` 就能看到「哪个文件对应文章哪一段、怎么运行」。

---

## 三句话说明怎么用

1. **一篇文章一个目录**，目录名带篇号。先看目录里的 `README` 对照表。
2. **离线可跑，不需要 API Key、不用花钱**。没配 key 时自动用内置的确定性 mock 演示逻辑；配了 key（`OPENAI_API_KEY`）就走真实模型。
3. **学习方式**：读一段文章 → 跑对应文件 → 看输出 → 改几个参数再跑。代码是拿来「跑通 + 改着玩」的，不是拿来背的。

---

## 快速开始

```bash
# 基础篇 02-10：每章一个 run_demo.py
python3 02_llm_call_essence/run_demo.py

# 进阶及之后 11-48：每章有 demo.py 总入口
python3 13_chunking/demo.py

# 也能单独跑某一个知识点文件（文件名见各章 README 对照表）
python3 13_chunking/chunking_strategies.py     # 只跑「6 种切块策略」这一个点

# 一次跑完全部示例
python3 run_all_demos.py

# 全量测试
python3 -m pytest tests/test_all_demos.py
```

> 需要真实模型效果时：`export OPENAI_API_KEY=sk-...` 再运行即可，代码会自动切换到真实调用。
> 框架章（LangGraph / CrewAI / ADK 等）若提示 `pip install xxx`，装上就真跑，不装也能看降级演示、不影响学原理。

---

## 目录地图（用户问哪章，看哪段）

### 第一部分 · 原理篇（02–10）：不用框架，把概念跑穿

| 篇 | 目录 | 讲什么 |
|----|------|--------|
| 02 | `02_llm_call_essence` | 一次 LLM 调用发生了什么：手搓 HTTP、流式 SSE、温度采样、token 预算 |
| 03 | `03_prompt_essence` | 四类上下文、System Prompt 优先级、Few-shot、结构化输出、CoT 取舍、Prompt 当代码管理 |
| 04 | `04_memory_essence` | LLM 为何无状态、短时记忆压缩、token 预算规划、长时检索、生产踩坑 |
| 05 | `05_rag_essence` | 朴素 RAG / Hybrid Search / Reranker / RAG 评估 / 微调数据构造 |
| 06 | `06_tool_essence` | 两轮 Function Calling、并行工具、极简 MCP Server、Skill 封装、幂等中间件、错误翻译 |
| 07 | `07_agent_loop` | ReAct、Plan-and-Execute + 四种防跑飞守卫（终止/同义循环/token 预算/Executor 重写） |
| 08 | `08_multi_agent` | Pipeline、Orchestrator-Worker、点对点、共享状态 vs 消息、事实校验、协调风暴检测 |
| 09 | `09_architecture` | 七层架构图谱 + 故障速查表 + 框架映射表 + 真实项目拆解 |
| 10 | `10_handwritten_agent` | **200 行纯 Python 零框架手搓工业级雏形 Agent**（基础版 + 流式持久化 plus 版） |

> 学法：先跑第 10 章（前 9 章的总集成，最值得亲手敲），再回头看 02–09，你会明白框架帮你省了什么、又偷偷漏了什么。

### 第二部分 · 进阶篇（11–33）

**RAG 进阶（11–15）** — 把 RAG 从「能用」调到「好用」
`11_rag_diagnosis`（召回率为何只有 50%）· `12_query_rewrite`（查询重写/HyDE/多意图）· `13_chunking`（6 种切块策略）· `14_rerank_hybrid`（CrossEncoder 重排 + Hybrid）· `15_graphrag`（GraphRAG）

**Memory 进阶（16–18）**
`16_memory_pipeline`（长期记忆五步链路）· `17_mem0`（Mem0 深拆）· `18_layered_memory`（分层记忆 + 异步事实抽取）

**框架三件套（19–33）**
- LangGraph：`19_langgraph_intro` `20_react_plan_execute` `21_checkpoint_hitl_timetravel` `22_orchestrator_worker`
- CrewAI：`23_crewai_intro` · `24_crewai_vs_langgraph`（同一客服系统两框架各写一遍 + 性能实测对比）
- Google ADK：`25_adk_intro` `26_adk_workflows` `27_adk_tools` `28_adk_memory` `29_adk_eval_plugins`
- DeepAgents / Harness：`30_deepagents_intro`（180 行手搓 Harness）· `31_context_engineering`
- 横评与选型：`32_three_framework_comparison`（同一采购助手三框架对比）· `33_framework_decision`（**选型决策树 CLI**，输入项目特征直接给推荐）

### 第三部分 · 工程化篇（34–48）：从「能跑」到「敢上线」

- Gateway：`34_llm_gateway` `35_gateway_implementation`（自建 Gateway 骨架 FastAPI+Redis+PG、虚拟 Key）
- 评测 + 可观测：`36_eval_frameworks` `37_eval_pipeline`（Bad Case 闭环 + CI）· `38_observability_tools` `39_otel_self_hosted`
- 安全：`40_prompt_injection_defense`（5 层防御 + RedTeam）· `41_rbac_jwt`（JWT + RBAC 多租户）· `42_output_defense`（HITL + 宪法链 + Guardrails）
- 成本 + 性能：`43_cost_optimization`（Prompt 压缩）· `44_cache_routing`（语义缓存 + 降级路由）· `45_performance_optimization`（并发 + 流式 + 异步工具）
- 全栈落地：`46_backend_foundation`（完整 FastAPI 后端：16 表 schema + JWT + 多租户 + SSE）· `47_full_stack_llmops`（Vue3 + ECharts 监控大盘 + docker-compose 部署）
- Harness 扩展：`48_harness_extension`（OpenHands 自部署、DeepAgents Middleware、per-user 编排）

> 46–47 是能直接拿去改成自己产品骨架的完整前后端。

> 第 49–50 篇是面试番外，无新代码——建议对照重跑 02–48 篇找手感。

### 第五部分 · 真实系统解剖（51–60）：把 Claude Code 封装成 7×24 数字员工

`51_zylos/` — 不是教学代码，而是**逐模块精读一套真实开源的 Agent 基础设施**：tmux 封装 Claude Code / Codex + SQLite 消息总线 + 个人微信接入 + 记忆 + 自愈 + 上下文轮换。文章讲到哪行代码，都能在源码里按文件 + 行号找到；`51_zylos/labs/` 是每篇的动手实验清单，`51_zylos/README.md` 是篇目↔源码对照。

---

## 常见问题

**代码怎么和文章对应？** 一篇文章一个目录（篇号命名），目录里每个文件对应一个知识点，先看该目录 README 对照表。

**要 API Key 吗？要花钱吗？** 不用。全部离线可跑；想看真实模型效果再配 `OPENAI_API_KEY`。

**报 `pip install xxx`？** 框架章在提示你装对应框架；装上真跑，不装看降级演示，不影响学原理。

**编辑器（Pyright / VSCode）报一堆导入红线？** 静态检查的误报——代码运行时会自己把路径加进去，`python3` 跑是通的，不用管。

**怎么学最高效？** 读一段文章 → 跑对应文件 → 看输出 → 改参数再跑。别背代码。第 10 章的 200 行手写 Agent 最值得亲手敲一遍。

---

## 仓库结构说明

- `NN_xxx/`：各篇章节目录，含具名知识点文件 + `README`（对照表）+ 章节入口 `demo.py` / `run_demo.py`
- `src/agent_code/`：02–10 基础篇的共享实现
- `series_projects/`：11–48 的连续项目版本（同一套业务随章节演进），章节 `demo.py` 委托到这里
- `agent_examples/`：离线可运行的公共基础设施（RAG / Memory / 框架桥接等）
- `51_zylos/`：第五部分的开源系统源码快照 + 实验清单
- `tests/`：全量运行与断言测试

祝学习顺利。跑通每一章，你就走完了从「玩具级」到「工业级」的完整路径。
