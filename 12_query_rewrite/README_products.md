# 12_query_rewrite — 查询重写：从单一改写到多意图拆分（配套产物）

第 12 篇《RAG 进阶 2》文末「包含：」承诺的产物清单与文件对照。查询这一层做扎实，召回率
能上 20 个百分点；这一层做不好，向量库换 10 个、Embedding 升 5 代都救不回来。

> 所有脚本**离线可运行**。LLM 调用统一走 `_llm.py`：有 `OPENAI_API_KEY` 且装了
> `openai` 时用真模型，否则用 `agent_examples.rag` 里打磨过的规则式改写做确定性兜底。
> 导入不发起网络请求。

## 文章「包含：」→ 文件对照表

| 文章承诺的产物 | 文件 | 说明 |
|---|---|---|
| Query Rewrite 模板库 | `query_rewrite_templates.py` | 四类改写模板（书面化 / 第三人称 / HyDE / Multi-Query）+ 渲染 + 端到端改写 |
| HyDE 完整实现 | `hyde_retrieve.py` | 先编假设性答案再检索，对照『原话直搜 vs HyDE』的 top1 |
| Multi-Query 异步并发版 | `multi_query_async.py` | `asyncio.gather` 并行多问法检索 + 按 chunk_id 合并去重保留最高分 |
| 多意图拆分极简示例 | `multi_intent_split.py` | 复合查询拆原子问题 → 各自召回 → 求交集融合（招聘检索例子，AND 全约束） |
| 召回率对照实验脚本 | `recall_comparison.py` | 原话直搜 / Rewrite / HyDE / Multi-Query 四策略 Recall@1 对照（80% → 100%） |
| 可选 LLM 封装 | `_llm.py` | 在线优先 / 离线规则式兜底的 rewrite / hyde / paraphrases |

## 运行

```bash
python3 12_query_rewrite/query_rewrite_templates.py
python3 12_query_rewrite/hyde_retrieve.py
python3 12_query_rewrite/multi_query_async.py
python3 12_query_rewrite/multi_intent_split.py
python3 12_query_rewrite/recall_comparison.py
```

> 连续项目统一入口（`demo.py` / `chapter_runner 12`）见同目录 `README.md`。
