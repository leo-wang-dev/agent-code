# 44 · 语义缓存 + 模型降级路由

配套文章：《语义缓存 + 模型降级路由》（系列第 44 篇）。

全部离线可运行，无需 API Key。embedding 与模型均为确定性本地 mock。

## 文章"包含"清单 → 文件对照

| 文章承诺的产物 | 文件 | 运行 |
|---|---|---|
| 语义缓存完整实现 | `semantic_cache.py` | `python3 semantic_cache.py` |
| 三种降级路由策略 demo | `routing_strategies.py` | `python3 routing_strategies.py` |
| 级联路由 | `cascade_router.py` | `python3 cascade_router.py` |
| 模型组合 Pipeline 示例 | `model_pipeline.py` | `python3 model_pipeline.py` |
| 缓存命中率监控面板 | `cache_hit_dashboard.py` | `python3 cache_hit_dashboard.py` |

辅助模块：`_models.py`（本地确定性 embedding + 分档 mock 模型 + 价格/延迟）。

## 覆盖的文章要点

- 语义缓存三个隐藏陷阱：跨用户隔离（按 tenant 分区）、时效性绕过（关键词 + TTL）、错配（阈值可调 + hit/miss 统计）。
- 三种路由：规则路由、LLM 判别路由、级联路由（够用即停）。
- 模型组合 Pipeline：每节点声明式配"最便宜的能胜任模型"，对比全程顶级。
- 协同效应：`cache_hit_dashboard.py` 跑 1000 次混合流量，展示缓存 + 降级叠加后的成本节省。

## 生产替换点

- `_models.local_embed`：关键词加权的离线近似；生产换 `SentenceTransformer("bge-large-zh")` 等真实 embedding。
- `_models.MockModel.complete`：确定性假响应；生产换真实 Gateway/LLM 调用。
- `cascade_router.quality_ok`：离线质量打分；生产换小模型/规则/评测集打分。
