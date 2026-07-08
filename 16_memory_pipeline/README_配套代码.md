# 第 16 篇配套代码 · 跨会话长期记忆的工程链路

> 对应文章《跨会话长期记忆的工程链路》。本目录在原有 `demo.py`（连续项目入口）之外，
> 补齐文章正文承诺的每一个可运行产物。全部**离线可跑**，无需 PostgreSQL / pgvector / Redis / LLM。

## 文章承诺 → 文件对照

| 文章承诺产物 | 文件 | 运行 |
|------|------|------|
| 约 230 行最小可上线 Memory 系统完整实现（含 schema + 综合打分 retrieve_memory） | `memory_system.py` | `python3 16_memory_pipeline/memory_system.py` |
| 抽取 Prompt 模板 | `extraction_prompt.py`（`EXTRACTION_PROMPT` 原样落地 + 抽取器） | `python3 16_memory_pipeline/extraction_prompt.py` |
| 异步任务队列接入 | `async_queue.py`（Redis List / 内存队列等价） | `python3 16_memory_pipeline/async_queue.py` |
| 检索综合打分逻辑 | `memory_system.py::retrieve_memory`（`semantic*0.6 + time_decay*0.2 + importance*0.2`） | 见上 |
| 遗忘 CronJob | `forgetting_cron.py`（TTL 过期 + 重要性衰减） | `python3 16_memory_pipeline/forgetting_cron.py` |
| 用户记忆面板示例 API | `memory_panel_api.py`（list / delete / delete_all，含 FastAPI 路由） | `python3 16_memory_pipeline/memory_panel_api.py` |

## 五步工程链路映射

```
抽取 Extraction  → extraction_prompt.py（低温度 + confidence + 反向断言黑名单）
存储 Storage     → memory_system.py::MemoryStore.upsert（ADD / UPDATE / NOOP）
检索 Retrieval   → memory_system.py::retrieve_memory（语义 + 时间衰减 + 重要性 + 类型过滤）
注入 Injection   → memory_system.py::build_memory_block / assemble_prompt（分块明示）
遗忘 Forgetting  → forgetting_cron.py（TTL）+ memory_panel_api.py（用户撤回）
```

## 离线 / 线上开关

| 组件 | 缺依赖时（默认离线） | 装了依赖 + 配置时（线上形态） |
|------|------|------|
| 抽取 | 确定性规则式抽取器 | 有 `OPENAI_API_KEY` → LLM 抽取（`temperature=0`） |
| 向量检索 | `agent_examples.text` 词频余弦等价 | 换 `embed()` / `vector_search()` 为 pgvector |
| 队列 | 内存 FIFO + 后台线程 | 有 `REDIS_URL` + `redis` 包 → Redis List |
| 面板 API | 纯 Python 服务层 + 离线自测 | 装 `fastapi uvicorn` → 挂 REST 路由 |

所有 `import` 均不发起网络；缺依赖会打印安装指引并跑内置等价实现。

## schema 一致性

`memory_system.MemoryFact` 的字段与文章正文的 `CREATE TABLE memory_facts` 一一对应：
`id / user_id / type / key / value / embedding / confidence / importance /
source_conversation_id / created_at / updated_at / expires_at / is_deprecated`。
