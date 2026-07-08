# 45 · 并发优化 + 流式 + 异步工具调用

配套文章：《并发优化 + 流式 + 异步工具调用》（系列第 45 篇）。

全部离线可运行，无需 API Key。asyncio 并发是真实的；流式用本地 mock 生成器。

## 文章"包含"清单 → 文件对照

| 文章承诺的产物 | 文件 | 运行 |
|---|---|---|
| 并发 fan-out/in 完整 demo | `concurrent_fanout.py` | `python3 concurrent_fanout.py` |
| 流式输出端到端实现 | `streaming_e2e.py` | `python3 streaming_e2e.py` |
| 流式的 Nginx 配置（含 SSE 透传） | `nginx_streaming.conf` | 配置文件，供 Nginx 使用 |
| 异步工具调用模式 | `async_tool_calls.py` | `python3 async_tool_calls.py` |
| 投机执行示例 | `speculative_execution.py` | `python3 speculative_execution.py` |
| 完整的延迟监控仪表盘 | `latency_dashboard.py` | `python3 latency_dashboard.py` |

## 覆盖的文章要点

- 并发：串行 vs `asyncio.gather` 并行对比；fan-out/fan-in（多 worker → aggregator）。
- 流式：SSE 编码、客户端逐块累积、工具调用中间态、中途出错优雅降级、句子块级流式 Guardrails。四个坑对应代码注释。
- Nginx：`proxy_buffering off` + `X-Accel-Buffering no` 才能透传 SSE。
- 异步工具：立即返回+异步通知、流式进度更新、工具内部并发。
- 投机执行：预判分支 prefetch，命中省一次串行等待，未命中回退。
- 延迟仪表盘：P50/P95/P99 + 各阶段延迟构成占比。

## 生产替换点

- `streaming_e2e.stream_response`：本地 mock 生成器；生产换 `client.chat.completions.create(..., stream=True)`。
- `async_tool_calls.TaskQueue`：内存队列；生产换 Celery / RQ / arq。
- 延迟样本为模拟生成；生产从真实 trace（OTel / Langfuse）读取。
