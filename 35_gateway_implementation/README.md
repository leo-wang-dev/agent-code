# 35_gateway_implementation —— LiteLLM / PortKey 实战 + 自建 Gateway 选型

配套第 35 篇。90% 项目从 LiteLLM 起步，10% 真需要自建 —— 讲清这个 90/10 分界。

## 文章产物 → 文件对照表

| 文章承诺 | 文件 | 说明 |
|---------|------|------|
| LiteLLM 完整生产配置 | `litellm_config.yaml` | 文章 §一 原样：多 Provider + 链式 Fallback + Redis 缓存 + master_key + PG |
| PortKey SDK 接入示例 | `portkey_integration.py` | 虚拟 Key/语义缓存/AB 路由配置；缺 portkey-ai 或 key 打印指引 |
| 自建 Gateway 最小骨架(FastAPI+Redis+PG) | `gateway_app.py` | 鉴权+限流+缓存+路由+Fallback+计费落库；Redis→dict、PG→sqlite、FastAPI→http.server 全降级 |
| 虚拟 Key 治理面板 | `virtual_key_panel.py` | 自助申请→审批→预算/过期强制→闲置回收 review，sqlite |
| 三方案成本对比脚本 | `cost_comparison.py` | 三档调用量下 LiteLLM/PortKey/自建 年度成本 + 决策门槛 |
| 章节连续项目入口 | `demo.py` | `LLMOpsPlatformProject` 第 35 阶段（未改动） |

## 选型门槛

| 月调用量 | 推荐 |
|---------|------|
| < 1000 万次 | LiteLLM 自部署 |
| 1000 万 - 1 亿次 | LiteLLM 仍可用，PortKey 看预算 |
| > 1 亿次 | 自建经济上合理 |

## 运行

```bash
python3 35_gateway_implementation/gateway_app.py            # 进程内自测（Redis/PG/FastAPI 缺则自动降级）
python3 35_gateway_implementation/gateway_app.py --serve    # 起 HTTP 服务
python3 35_gateway_implementation/virtual_key_panel.py
python3 35_gateway_implementation/portkey_integration.py    # 缺 portkey-ai 打印指引
python3 35_gateway_implementation/cost_comparison.py
python3 35_gateway_implementation/demo.py                   # 连续项目阶段入口

# 真实 LiteLLM Proxy：
litellm --config 35_gateway_implementation/litellm_config.yaml --port 4000
```

依赖全部可选：`pip install fastapi uvicorn redis psycopg portkey-ai litellm`。缺任一都优雅降级（内存 dict / sqlite / http.server / 确定性 mock），exit 0，不联网。运行产生的 `.db` 已被 `.gitignore` 忽略。
