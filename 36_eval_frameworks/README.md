# 36 · 评测框架横评 —— RAGAS / Promptfoo / DeepEval

配套文章：《RAGAS / Promptfoo / DeepEval —— 评测框架横评》（系列第 36 篇）

## 产物对照表

| 文章承诺 | 文件 | 说明 |
|---------|------|------|
| RAGAS 4 指标完整 demo | `ragas_four_metrics.py` | Context Precision/Recall + Faithfulness + Answer Relevancy，真实 ragas / 教学版双模式 |
| Promptfoo 多 Prompt 对比示例 | `promptfooconfig.yaml` + `prompts/classifier_v1.txt` + `prompts/classifier_v2.txt` | 多 Prompt × 多 Model 对比，含 equals/contains/latency/llm-rubric 断言 |
| DeepEval Pytest 风格用例 | `test_deepeval_cases.py` | 类 Pytest 用例，AnswerRelevancy/Faithfulness/Hallucination，可 `pytest` 或 `deepeval test run` |
| 三框架叠加的工业级评测套件 | `industrial_eval_suite.py` | RAGAS(RAG内部) + Promptfoo(整体流程) + DeepEval(安全性) 三层编排 + 总闸门 |
| 中文场景的调优配置 | `zh_tuning_config.py` | 评测 LLM 选型、中文裁判 prompt 模板、分数校正系数 |

## 运行

```bash
# 全部为零依赖可运行（缺 ragas/deepeval 时自动走确定性教学版）
python3 ragas_four_metrics.py
python3 industrial_eval_suite.py
python3 zh_tuning_config.py
python3 test_deepeval_cases.py        # 或 pytest test_deepeval_cases.py

# Promptfoo（需 Node 环境）
npx promptfoo@latest eval && npx promptfoo@latest view
```

## 生产替代

- RAGAS：`pip install ragas datasets` + 配置评测 LLM（建议 GPT-4o）。
- DeepEval：`pip install deepeval` + `OPENAI_API_KEY`，用 `deepeval test run`。
- Promptfoo：`npm i -g promptfoo`，providers 配置对应厂商 key。
- 无 API key 时，各脚本自动回退到词汇重叠近似的确定性 mock，输出稳定可复现，仅供演示链路，**不可用于真实质量判定**。
