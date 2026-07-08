# 29_adk_eval_plugins —— ADK Evaluation + Plugins

配套文章：《ADK Evaluation + Plugins —— ADK 在工业化能力上的独家牌》

在原有 `demo.py`（连续项目入口）之外，补齐文章文末"包含："承诺的每一件具名产物，均为**独立可运行**脚本。
约定同全系列：`google-adk` 导入 `try/except` 保护，缺依赖打印安装指引并降级到**确定性 mock**，`exit 0`；无 API key 时不联网。

## 安装（跑真实 ADK 时）

```bash
pip install google-adk
export GOOGLE_API_KEY=...   # 或 GEMINI_API_KEY
```

## 产物对照表

| 文章承诺产物 | 文件 | 说明 | 运行 |
|---|---|---|---|
| 完整评测套件示例 | `eval_suite.py` | 生成标准 `.test.json` + mock AgentEvaluator 跑套件出报告 | `python3 29_adk_eval_plugins/eval_suite.py` |
| 4 种 Evaluator 用法 | `four_evaluators.py` | Trajectory(EXACT/IN_ORDER/ANY_ORDER) / Response / Faithfulness(加权公式) / Composite | `python3 29_adk_eval_plugins/four_evaluators.py` |
| 生产级 Plugin 链（8 个） | `plugin_chain.py` | 审计/安全/成本/可观测/业务 8 Plugin + Plugin vs Callback 顺序 | `python3 29_adk_eval_plugins/plugin_chain.py` |
| ADK Capstone 项目骨架 | `capstone_skeleton.py` | 采购助手：Plugin+Delegation+级联搜索+渐进 Skills+Services+Eval 的 dry-run | `python3 29_adk_eval_plugins/capstone_skeleton.py` |

运行 `eval_suite.py` 会在本目录生成 `research_eval.test.json`（已存在则不覆盖），作为标准评测集样例。

## 四种 Evaluator

| Evaluator | 评估的事 |
|---|---|
| TrajectoryEvaluator | 工具调用序列是否正确（三种匹配模式） |
| ResponseEvaluator | 文本回答与 reference 的相似度 |
| FaithfulnessEvaluator | 回答是否基于工具输出（防幻觉） |
| CompositeEvaluator | 多维度加权综合，阈值判定通过 |

> Faithfulness 采用文章给出的加权公式 `0.6×工具支撑比例 + 0.4×问题覆盖比例`；文章内联的 1.0/0.0/0.5 是示意值，脚本输出的是公式实算的分级分（排序一致：忠实 > 夹带 > 编造）。

> `demo.py` 仍是连续项目的第 29 章阶段入口，不受本目录新增文件影响。
