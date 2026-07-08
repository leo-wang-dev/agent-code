# 15_graphrag — GraphRAG：当余弦相似度走到尽头（配套产物）

第 15 篇《RAG 进阶 5》文末「包含：」承诺的产物清单与文件对照。当用户的问题需要跨多个
文档、需要关系推理时，余弦相似度从根上不够用——GraphRAG 从「找相似 chunk」转向「找相关
实体的关系网络」。

> 所有脚本**离线可运行**、纯 stdlib。知识图谱用内存邻接表实现（等价 Neo4j）；
> LLM 抽取 / Neo4j 写库 / 各家 GraphRAG 包缺失时自动走确定性离线等价并打印安装指引。
> 导入不发起网络请求。

## 文章「包含：」→ 文件对照表

| 文章承诺的产物 | 文件 | 说明 |
|---|---|---|
| 实体抽取 + 关系抽取 Prompt 模板 | `extraction_prompts.py` | 实体/关系抽取 Prompt（关系白名单 + JSON 输出）+ 确定性离线规则式抽取器 |
| Neo4j 入图脚本 | `neo4j_ingest.py` | 三元组 → 幂等 Cypher `MERGE`；有 neo4j 驱动+env 真写库，否则 dry-run + 内存图校验 |
| 子图召回 | `subgraph_recall.py` | query 实体识别 → 种子节点 → N 跳遍历；无实体则降级向量 RAG（对照 `graph_retrieve`） |
| 子图序列化 | `subgraph_serialize.py` | 三种注入格式：三元组列表 / 自然语言事实 / 实体为中心邻接 + prompt 组装 |
| 三方案对照实验 | `three_approach_comparison.py` | Microsoft GraphRAG / LightRAG / 自建 Cypher 统一接口机制模拟 + 能力成本对照表 |
| GraphRAG 与向量 RAG 效果对比 | `graphrag_vs_vector.py` | 多跳关系推理问题上向量 RAG 33% vs GraphRAG 100% |
| 公共图基础设施 | `_graph.py` | `KnowledgeGraph` + 三元组抽取 + 遍历 + 示例语料 |

## 运行

```bash
python3 15_graphrag/extraction_prompts.py
python3 15_graphrag/neo4j_ingest.py
python3 15_graphrag/subgraph_recall.py
python3 15_graphrag/subgraph_serialize.py
python3 15_graphrag/three_approach_comparison.py
python3 15_graphrag/graphrag_vs_vector.py
```

## 核心示例

图里有 `(Y投资集团 控股 X资本管理公司)`、`(X资本管理公司 破产 2021/50亿)`。问「Y投资集团
有没有卷入破产？」——向量 RAG 因为两个事实分散在不同句子、语义不相似而漏掉；GraphRAG
顺着控股关系 2 跳就把破产事实连起来。**但这是小众杀器**：单跳事实型问题向量 RAG 就够了，
盲目上 GraphRAG 是增加工程难度而非收益，要算 ROI。

> 连续项目统一入口（`demo.py` / `chapter_runner 15`）见同目录 `README.md`。
