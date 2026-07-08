# 第 18 篇配套代码 · 分层记忆 + 异步事实抽取

> 对应文章《分层记忆 + 异步事实抽取 —— 让 Agent 真的"长出记忆"》。在原有 `demo.py`
> 之外，补齐文章承诺的每个可运行产物。全部**离线可跑**，无需 pgvector / Redis / LLM。

## 文章承诺 → 文件对照

| 文章承诺产物 | 文件 | 运行 |
|------|------|------|
| 4 层 Memory 完整 schema | `layered_schema.py`（Profile/Preference/Episodic/Working + 治理策略表） | `python3 18_layered_memory/layered_schema.py` |
| 联合检索引擎 | `joint_retrieval.py`（`assemble_memory_context` + 分块注入） | `python3 18_layered_memory/joint_retrieval.py` |
| 异步抽取队列 | `async_extraction.py`（fire-and-forget + 按层路由） | `python3 18_layered_memory/async_extraction.py` |
| debounce 机制 | `debounce.py`（30s 窗口合并，逻辑时钟驱动） | `python3 18_layered_memory/debounce.py` |
| 失败重试与死信队列 | `retry_dlq.py`（30s/2min/10min 指数退避 + DLQ） | `python3 18_layered_memory/retry_dlq.py` |
| 置信度暂存区 | `staging_area.py`（<0.7 进暂存 · 3 次确认升级 · 30 天清理） | `python3 18_layered_memory/staging_area.py` |
| 5 个核心监控指标采集脚本 | `metrics.py`（queue_depth / failure_rate / latency / cost / relevance） | `python3 18_layered_memory/metrics.py` |

## 4 层治理策略（文章"一张关键决策表"）

| 维度 | Profile | Preference | Episodic | Working |
|------|---------|-----------|---------|---------|
| 持久化 | 是 | 是 | 是 | 否 |
| 向量化 | 否 | 是 | 是 | 否 |
| 检索方式 | 直接读 | 语义 Top-2 | 语义+时间 Top-3 | 直接读 |
| 每次注入 | 是 | Top-K | Top-K | 是 |
| TTL | 无 | 无 | 90 天 | 会话结束 |
| 抽取方式 | 结构化映射 | LLM | LLM(带时间戳) | 可选 |

代码里对应 `layered_schema.LAYER_POLICY`。Episodic 打分公式（`joint_retrieval.rerank_with_time_decay`）：
`score = semantic*0.6 + time_decay*0.3 + importance*0.1`。

## 异步抽取管线（文章第六节整体架构图）

```
主流程（同步，用户感知延迟只到这里）
  加载 Profile/Working → 检索 Preference/Episodic → 组装 Prompt → LLM 生成 → 流式返回
       │ fire-and-forget（async_extraction.AsyncExtractor.fire）
       ↓
抽取流程（异步）
  LLM 抽取 → 按层路由（Profile→UPSERT / Pref·Epi→向量层 / Working→session）
  失败重试+死信（retry_dlq）· debounce 批量化（debounce）· 低置信→暂存区（staging_area）
```

## 离线 / 线上开关

| 组件 | 缺依赖时（默认离线） | 线上形态 |
|------|------|------|
| Profile 存储 | 内存 KV | 关系型表 + Redis 缓存 |
| Preference/Episodic | `agent_examples.text` 词频向量 | pgvector / Pinecone |
| Working 存储 | 内存 session dict | Redis / Session Store |
| 队列 | 内存 `queue.Queue` + 线程 | Redis Queue / RabbitMQ / Celery |
| debounce | 逻辑时钟内存去抖 | 有 `REDIS_URL` → Redis SETEX |
| 监控 | 内存指标 + 阈值判定 | push 到 Prometheus / StatsD |

`import` 均不发起网络；缺依赖打印安装指引并跑内置等价。
