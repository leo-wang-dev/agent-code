# 38 · 可观测工具横评 —— LangSmith / Langfuse / Helicone

配套文章：《可观测工具横评 —— LangSmith / Langfuse / Helicone》（系列第 38 篇）

## 产物对照表

| 文章承诺 | 文件 | 说明 |
|---------|------|------|
| 三家完整接入示例 | `integrations_three_vendors.py` | LangSmith 环境变量 / Langfuse 装饰器 / Helicone 反向代理，import 全保护 |
| 三家功能对比矩阵 | `comparison_matrix.py` | 12 维矩阵 + 7 条选型决策 |
| 4 类指标采集脚本 | `metrics_collector.py` | 业务/性能/系统/质量四类，带健康阈值自动判定 |
| 模型漂移检测器 | `drift_detector.py` | 金标准每日对比，语义漂移近似 + 告警 |
| 异常成本告警 demo | `cost_alert.py` | 绝对阈值 + 基线倍数 + 超长会话，三重触发 |

## 运行

```bash
python3 integrations_three_vendors.py   # 三家接入示例（缺 SDK 打印接入指引）
python3 comparison_matrix.py            # 对比矩阵 + 选型决策
python3 metrics_collector.py            # 4 类指标采集与健康度
python3 drift_detector.py               # 漂移检测（正常波动 vs 供应商换模型）
python3 cost_alert.py                   # 异常成本告警扫描
```

## 生产替代

- LangSmith：`LANGCHAIN_TRACING_V2=true` + `LANGCHAIN_API_KEY`，LangChain 代码零改动。
- Langfuse：`pip install langfuse`，`@observe()` 或 `from langfuse.openai import openai`；可 docker-compose 自部署。
- Helicone：`base_url=https://oai.helicone.ai/v1` + `Helicone-Auth` header。
- `metrics_collector` 的 `_mock_raw_events` 换成从 trace 后端 / usage_logs 聚合；`drift_detector` 换成 embedding 余弦距离。
