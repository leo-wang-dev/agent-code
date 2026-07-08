# 39 · OpenTelemetry 集成与自建可观测平台

配套文章：《OpenTelemetry 集成 + 自建可观测平台》（系列第 39 篇）

## 产物对照表

| 文章承诺 | 文件 | 说明 |
|---------|------|------|
| OTel SDK 完整接入示例 | `otel_sdk_setup.py` | GenAI 语义约定 span（chat/tool.execute/rag.retrieve），真实 OTel / 打印 mock 双模式 |
| 自动 instrumentation 配置 | `auto_instrumentation.py` | openai/anthropic/httpx instrumentor + traceloop 全家桶，import 全保护 |
| 工业级 Collector 配置模板 | `otel-collector-config.yaml` | 批处理/尾采样/脱敏/属性丰富/多后端导出 |
| 自建可观测平台 docker-compose | `docker-compose.yaml` | Collector + Tempo + Prometheus + Loki + Grafana |
| 脱敏规则库 | `redaction_rules.py` | 三档分级脱敏，正则实现 + presidio 可选 |
| 数据归档自动化脚本 | `archive_data.py` | 热/温/冷三层，冷层降采样，成本估算 |

## 运行

```bash
python3 otel_sdk_setup.py        # 产生 GenAI 约定 span（装了 opentelemetry 走真实导出）
python3 auto_instrumentation.py  # 尝试启用自动埋点（缺库打印安装指引）
python3 redaction_rules.py       # 脱敏演示
python3 archive_data.py          # 分层归档计划

# 自建平台
docker compose up -d             # Grafana: http://localhost:3000 (admin/admin)
```

## 生产替代

- `pip install opentelemetry-sdk opentelemetry-exporter-otlp` + `OTEL_EXPORTER_OTLP_ENDPOINT`。
- 自动埋点推荐 `pip install traceloop-sdk`，一个包覆盖 30+ LLM 库。
- `docker-compose.yaml` 需配套 `tempo.yaml`/`prometheus.yml`/Loki 配置（按各自官方模板）。
- 脱敏：应用层用 `presidio-analyzer` 智能识别 PII，Collector 的 `attributes/redact` 兜底。
- 归档：把 `plan_archive` 决策映射到 S3/OSS lifecycle 规则，数据自动迁移。
