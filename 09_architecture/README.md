# 09 Agent 的 7 层架构 — 配套资料

对应文章《Agent 的 7 层架构：一张图看懂工业级系统的全貌》。

本章偏资料型：用「markdown 速查表 + 可运行示例」组合。下面四张表可直接查阅，
每张表都对应一个可运行的 `.py`，跑一遍能看到同样内容的结构化输出。

## 产物对照表

| 文章承诺 | 文件 | 说明 |
| --- | --- | --- |
| 7 层架构图谱 | `seven_layer_map.py` | L1-L7 职责/故障/工具的完整图谱 |
| 故障点速查表 | `fault_lookup.py` | 症状 → 首查层级 → 先查什么 |
| 框架映射表 | `framework_mapping.py` | 各框架主要落在哪一层（正反向） |
| 真实项目拆解 | `real_project_breakdown.py` | 企业客服 Agent 按 L1-L7 落地 |
| 汇总入口 | `run_demo.py` | 原有委托 `src/agent_code` 的组合 demo |

## 7 层架构图谱

| 层 | 名称 | 职责 | 关键判断 |
| --- | --- | --- | --- |
| L1 | 模型层 | 请求/响应、token、采样、流式、重试、限流、路由 | 能不能跑 |
| L2 | 记忆与检索层 | 短时上下文、长时记忆、RAG、权限过滤、token 预算 | 能不能跑 |
| L3 | 执行层 | Tool / Function Calling / Skill / MCP、幂等、参数校验、错误翻译 | 能不能跑 |
| L4 | 编排层 | Agent 循环、多 Agent、工作流、状态机、checkpoint、终止条件 | 能不能跑 |
| L5 | 交互层 | 提问、上传、流式展示、人工审批、IM 接入 | 能不能跑 |
| L6 | 安全治理层 | Prompt Injection、RBAC、PII、工具权限、HITL、审计 | 敢不敢上线 |
| L7 | 评估反馈层 | 评测集、回归、trace、反馈、归因、灰度、回滚 | 敢不敢上线 |

## 故障点速查表

| 症状 | 先看 | 先查什么 |
| --- | --- | --- |
| 429 / 超时 / 流式中断 | L1 | 重试、退避、队列、fallback 路由 |
| 引用错资料 / 记忆丢 / RAG 没召回 | L2 | 检索上下文、记忆选择、prompt 拼装 trace |
| 工具选错 / 参数错 / 副作用重复 | L3 | 工具描述、参数 schema、负例 |
| 循环跑偏 / 多 Agent 拉扯 / 卡住 | L4 | 最大迭代、重复动作检测、状态跳转 |
| 前端看不到完整输出 / 审批不同步 | L5 | SSE 缓冲、重连、partial JSON 组装 |
| 数据泄露 / 越权 / 注入 | L6 | RBAC 过滤、PII 脱敏、间接注入 |
| 改 Prompt 后效果说不清 | L7 | 回归评测，发布前比对 trace |

## 框架映射表

| 框架/工具 | 主要层 |
| --- | --- |
| OpenAI SDK | L1 |
| RAG 框架 / 向量库 | L2 |
| MCP | L3 |
| LangChain AgentExecutor | L3 + L4 |
| LangGraph / CrewAI / AutoGen | L4 |
| Guardrails / OPA / 权限网关 / 审计 | L6 |
| Langfuse / LangSmith / RAGAS / Harness | L7 |

> 大多数框架只覆盖 L1-L4，L6 安全与 L7 评估仍要自己建设。

## 运行

```bash
python3 09_architecture/seven_layer_map.py
python3 09_architecture/fault_lookup.py
python3 09_architecture/framework_mapping.py
python3 09_architecture/real_project_breakdown.py
python3 09_architecture/run_demo.py
```

底层数据源在 `src/agent_code/seven_layer.py`（`LAYERS` / `SYMPTOM_LOOKUP` /
`FRAMEWORK_MAPPING` / `sample_customer_service_breakdown`）。
