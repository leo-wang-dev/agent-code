# 11_rag_diagnosis — 你的 RAG 召回率为什么只有 50%（配套产物）

第 11 篇《RAG 进阶 1》文末「包含：」承诺的产物清单与文件对照。本章把「RAG 召回率低」
拆成**三个可观察的瓶颈层**，并用一个能跑出 50% → 100% 的对照 demo 证明：召回率的差距
不来自向量库或 Embedding，来自整条流水线的每一环。

> 所有脚本**离线可运行**，不联网、不需要 API key。Embedding 默认用确定性词频向量
> （`agent_examples.text`）；设置 `OPENAI_API_KEY` 且装了 `openai` 时自动切真 embedding。
> RAGAS 缺失时跑内置离线等价实现。

## 文章「包含：」→ 文件对照表

| 文章承诺的产物 | 文件 | 说明 |
|---|---|---|
| 朴素 RAG 的 50% 召回率复现 demo | `naive_rag_recall_demo.py` | 朴素（固定切块+纯向量+原话）Recall@1 = 50%，工业级（结构化+改写+重排）= 100% |
| 每个瓶颈的可观察指标采集脚本 | `bottleneck_metrics.py` | 瓶颈一查询层 `query_doc_lexical_gap`、瓶颈二切块层 `answer_chunk_integrity`、瓶颈三检索层 `precision@k` |
| 用 RAGAS 测 Context Precision/Recall 的对照实验 | `ragas_context_metrics.py` | 有 ragas 走真评测，没有跑同定义离线等价；朴素 vs 工业级两列对照 |
| 公共数据/工具 | `_common.py` | 评测语料（含刻意设计的干扰文档）、口语化标注 query、embedding 切换、召回率与打印工具 |

## 运行

```bash
python3 11_rag_diagnosis/naive_rag_recall_demo.py   # 50% → 100% 主 demo
python3 11_rag_diagnosis/bottleneck_metrics.py       # 三层瓶颈指标
python3 11_rag_diagnosis/ragas_context_metrics.py    # Context Precision/Recall 对照
```

## 关于数字的诚实说明

离线词频向量是一个**乐观的关键词匹配器**（更接近 BM25 而非弱 bi-encoder），所以我们
用刻意设计的干扰文档 + Recall@1 口径复现出文章的 50%。线上真实 bi-encoder 在语义鸿沟
上的朴素基线会更低。这里**复现的是结构**——「朴素低、每叠加一环就升」——而非某个具体
小数点。

> 连续项目统一入口（`demo.py` / `chapter_runner 11`）见同目录 `README.md`，二者互补。
