# 14_rerank_hybrid — Cross-Encoder 重排与 Hybrid Search（配套产物）

第 14 篇《RAG 进阶 4》文末「包含：」承诺的产物清单与文件对照。RAG 的工程难度不在算法，
在「承认每一层都会出错，并设计好出错时的兜底」。

> 所有脚本**离线可运行**。真实 Reranker SDK（`FlagEmbedding` / `cohere` / `voyageai`）或
> API key 缺失时自动回退确定性离线打分并打印安装指引。导入不发起网络请求。

## 文章「包含：」→ 文件对照表

| 文章承诺的产物 | 文件 | 说明 |
|---|---|---|
| Bi/Cross 对照实验脚本 | `bi_vs_cross_experiment.py` | 同一候选集上比较 Bi-Encoder 召回序 vs Cross-Encoder 重排序的 Top1 命中 |
| 双阶段检索完整 demo | `two_stage_retrieval.py` | 阶段1 Bi 召回 Top-8 → 阶段2 Cross 重排 Top-3 |
| Hybrid Search + RRF 融合实现 | `hybrid_search_rrf.py` | 向量 + BM25 两路并行召回 → `rrf_fuse`（k=60）融合 |
| bge/Cohere/Voyage 统一接口适配器 | `reranker_adapters.py` | `Reranker.score(query, passages)` 统一接口，三家子类，缺 SDK/key 自动离线兜底 |
| 完整的降级容错中间件 | `rerank_fallback_middleware.py` | 召回不许失败、重排超时/异常降级到向量原序，带可观测计数器 |

## 运行

```bash
python3 14_rerank_hybrid/bi_vs_cross_experiment.py
python3 14_rerank_hybrid/two_stage_retrieval.py
python3 14_rerank_hybrid/hybrid_search_rrf.py
python3 14_rerank_hybrid/reranker_adapters.py
python3 14_rerank_hybrid/rerank_fallback_middleware.py
```

## 选型速记

- 中文场景 → **bge-reranker**（`pip install FlagEmbedding`）
- 国际场景 → **Cohere Rerank** / **Voyage Rerank**（需对应 API key）
- 重排永远是「锦上添花」层：挂了就降级到 Bi-Encoder 召回原序，绝不让链路崩。

> 连续项目统一入口（`demo.py` / `chapter_runner 14`）见同目录 `README.md`。
