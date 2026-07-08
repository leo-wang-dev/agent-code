# 第 17 篇配套代码 · Mem0 深度拆解

> 对应文章《Mem0 深度拆解 —— Agent 记忆服务的实战要点》。在原有 `demo.py` 之外，
> 补齐文章承诺的每个可运行产物。全部**离线可跑**，无需 mem0 / Neo4j / OpenAI。

## 文章承诺 → 文件对照

| 文章承诺产物 | 文件 | 运行 |
|------|------|------|
| Mem0 SDK 完整接入示例 | `mem0_integration.py`（真实 SDK + `Mem0OfflineClient` 离线等价） | `python3 17_mem0/mem0_integration.py` |
| Vector 模式 vs Graph 模式对照实验 | `vector_vs_graph.py` | `python3 17_mem0/vector_vs_graph.py` |
| Operation Engine 行为分析脚本 | `operation_engine.py`（ADD/UPDATE/DELETE/NOOP 决策 + 版本历史） | `python3 17_mem0/operation_engine.py` |
| 三层 ID 多租户隔离测试 | `three_tier_id.py`（user/agent/run，4 场景带断言） | `python3 17_mem0/three_tier_id.py` |
| Mem0 与手搓 Memory 性能对照基准 | `perf_benchmark.py` | `python3 17_mem0/perf_benchmark.py` |

## 复现文章关键结论

- **Operation Engine**（`operation_engine.py`）：复现文章四个对话——ADD → UPDATE（旧值进历史）→ DELETE（否定检测）→ NOOP（去重）；输出 Operation 分布，即文章要监控的指标。
- **Graph 模式的价值**（`vector_vs_graph.py`）：Vector 只能直接命中，Graph 沿 `(用户)-[妻子]->(王芳)-[职业]->(产品经理)` 两跳回答关系性问题。
- **三层 ID**（`three_tier_id.py`）：4 个 `assert` 场景证明 user/agent/run 隔离边界正确——Agent 不串味、用户不越界、会话可清理、全局/私有分层。
- **性能代价**（`perf_benchmark.py`）：Operation Engine 每条事实多一次决策（线上 = 一次 LLM 调用），换来去重（1000 条重复事实 → 库中 1 条）。异步执行不打到用户延迟，同步会拖慢回复。

## 离线 / 线上开关

| 组件 | 缺依赖时（默认离线） | 装了依赖 + 配置时 |
|------|------|------|
| Mem0 客户端 | `Mem0OfflineClient`（确定性规则 + OperationEngine） | 有 `mem0` + `OPENAI_API_KEY` → `from mem0 import Memory` |
| 抽取 / 决策 | 规则式（否定词 / 槽位冲突 / 完全相同） | Mem0 内部 LLM |
| 向量检索 | `agent_examples.text` 词频余弦 | Mem0 配置的 vector store |
| Graph | 内置三元组图 + 图遍历 | Mem0 Graph 模式（Neo4j） |

`import` 均不发起网络；缺依赖打印安装指引并跑内置等价。
