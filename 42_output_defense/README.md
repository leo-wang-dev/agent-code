# 42 · HITL 与宪法链与 Guardrails —— 输出端防御

配套文章：《HITL 与宪法链与 Guardrails —— 输出端防御》（系列第 42 篇）

## 产物对照表

| 文章承诺 | 文件 | 说明 |
|---------|------|------|
| HITL 完整工程实现 | `hitl_workflow.py` | 暂停/审批/恢复，上下文卡片、超时默认拒绝、否决理由反馈、快照令牌 |
| 宪法链多场景 demo | `constitutional_chain.py` | 6 条宪法条款，PASS/NEEDS_REVISION/BLOCK，审视→重写→再审视 |
| Guardrails AI 接入 | `guardrails_ai_demo.py` | PII/Toxicity/Length/Topic 校验，guardrails-ai / stdlib 双模式 |
| NeMo Guardrails 配置 | `nemo_config/config.yml` + `nemo_config/rails.co` | config.yml + Colang 规则，输入/输出双向护栏 |
| 三层防御端到端项目 | `three_layer_defense.py` | Guardrails → 宪法链 → HITL 协同编排 |

## 运行

```bash
python3 guardrails_ai_demo.py     # 程序化输出过滤
python3 constitutional_chain.py   # 宪法链多场景
python3 hitl_workflow.py          # HITL 审批工作流
python3 three_layer_defense.py    # 三层协同端到端
```

## 生产替代

- Guardrails：`pip install guardrails-ai`，`Guard().use(DetectPII, ProfanityFree, ...)`；本仓用正则/词表等价校验器。
- 宪法链：把 `_mock_review` 换成真实 LLM（GPT-4o，temperature=0）做裁判；宪法条款用 Git 版本管理 + 评测；只对高风险领域启用。
- NeMo：`pip install nemoguardrails`，`RailsConfig.from_path("nemo_config")` 加载本目录配置。
- HITL：接 LangGraph `interrupt()` + checkpoint 做真实暂停/恢复；审批 UI + SLA 监控 + 超时升级。
- 三层协同的分工：Guardrails(毫秒/确定性) → 宪法链(秒级/语义) → HITL(分钟-小时/人决策)。
