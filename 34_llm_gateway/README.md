# 34_llm_gateway —— LLM Gateway 是什么

配套第 34 篇。Gateway = Agent 应用与各家 LLM API 之间的中台（LLM 调用的反向代理）。

## 文章产物 → 文件对照表

| 文章承诺 | 文件 | 说明 |
|---------|------|------|
| 最小 LiteLLM Proxy 配置 | `config.yaml` | 文章 §六 原样交付：统一 API + Fallback + 缓存 |
| Fallback / 缓存 / 限流完整 demo | `gateway_features_demo.py` | 能力 3/4/5：FallbackRouter + SemanticCache + RateLimiter，纯标准库 |
| 简易自建 Gateway 骨架 | `self_built_gateway.py` | 鉴权+模型白名单+路由+计费落库；`--serve` 起 FastAPI，缺则降级 http.server |
| 成本统计仪表盘 | `cost_dashboard.py` | 按团队/模型成本拆解 + 占比条形 + 异常告警 |
| 章节连续项目入口 | `demo.py` | `LLMOpsPlatformProject` 第 34 阶段（未改动） |

## Gateway 7 大核心能力

统一 API / Key 集中管理 / 自动降级 Fallback / 语义缓存 / 限流配额 / 成本可视化 / 可观测性

## 运行

```bash
python3 34_llm_gateway/gateway_features_demo.py            # Fallback+缓存+限流，无依赖
python3 34_llm_gateway/self_built_gateway.py              # 进程内自测（不监听端口）
python3 34_llm_gateway/self_built_gateway.py --serve      # 起 HTTP 服务(FastAPI 或 http.server)
python3 34_llm_gateway/cost_dashboard.py                  # 成本仪表盘
python3 34_llm_gateway/demo.py                            # 连续项目阶段入口

# 真实 LiteLLM Proxy（需 pip install 'litellm[proxy]' 且设置各 Provider key）：
litellm --config 34_llm_gateway/config.yaml --port 4000
```

依赖全部可选。缺 FastAPI 时 `--serve` 用标准库 http.server；无 API key 时确定性 mock。全部 exit 0，不联网。
