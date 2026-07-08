# 05 · RAG 的本质：把搜索引擎塞进 Prompt 里

对应文章《RAG 的本质：把搜索引擎塞进 Prompt 里》（系列第 05 篇）。文末承诺本目录包含：朴素 RAG、Hybrid Search、Reranker、RAG 评估流水线、fine-tune 数据构造示例。

RAG 不是模型，是工程模式：检索系统负责翻资料，LLM 负责说人话。全部离线可跑、确定性输出。

> 离线环境没有真实 embedding，向量分用词频余弦作 stand-in；语料用英文以便 `[a-z0-9]` 分词命中。真实系统把检索器换成 embedding 模型即可，链路不变。

## 产物 → 文件 → 运行命令

| 承诺产物 | 文件 | 运行命令 |
|---|---|---|
| 朴素 RAG（切块→Top-K→拼 Prompt + 向量天花板） | `naive_rag.py` | `python3 naive_rag.py` |
| Hybrid Search（关键词 + 向量融合，keyword_weight 旋钮） | `hybrid_search.py` | `python3 hybrid_search.py` |
| Reranker（两阶段：召回多捞 → 精排定序） | `reranker.py` | `python3 reranker.py` |
| RAG 评估流水线（faithfulness / 相关性 / bad case 回归） | `rag_evaluation.py` | `python3 rag_evaluation.py` |
| fine-tune 数据构造（(query,positive) 对 → JSONL） | `finetune_data.py` | `python3 finetune_data.py` |
| 汇总（Hybrid + Rerank + 评估一把跑） | `run_demo.py` | `python3 run_demo.py` |

## 一次跑全部

```bash
for f in naive_rag hybrid_search reranker rag_evaluation finetune_data; do
  echo "===== $f ====="; python3 "$f.py"; echo
done
```

## 复用的核心实现

复用 `src/agent_code/rag_essence.py`：`chunk_text` / `NaiveRAGRetriever`（朴素 RAG）、`HybridSearch`（混合检索）、`Reranker`（精排）、`RAGEvaluator`（评估）、`build_finetune_pairs` / `write_jsonl`（微调数据）。`finetune_data.py` 的 JSONL 写到系统临时目录，不污染仓库。
