# 33_framework_decision —— 选型决策树：从业务特征到框架选择

配套第 33 篇。把 32 篇的对比数据翻译成可执行的选型工具。

## 文章产物 → 文件对照表

| 文章承诺 | 文件 | 说明 |
|---------|------|------|
| 完整选型决策树 CLI 工具 | `decision_tree_cli.py` | Q1-Q7 决策树；默认跑三个内置示例，支持 `--flag` 直接选型 / `--interactive` 逐题 |
| 6 种项目类型的框架推荐 | `project_recommendations.py` | 6 类项目特征喂进决策树，验证与文章推荐一致 |
| 三种混用模式最小可运行代码 | `hybrid_patterns.py` | LangGraph主+CrewAI子 / ADK主+DeepAgents子 / 三层叠加；缺库回退 |
| 三种迁移路径工程示例 | `migration_scripts.py` | CrewAI→LangGraph / LangGraph→ADK / +DeepAgents子任务；概念映射 + 清单生成器 |
| 章节连续项目入口 | `demo.py` | `SourcingAgentProject` 第 33 阶段（未改动） |

## 决策树骨架（Q1-Q7）

```
Q1 高风险操作? 是→Q2 / 否→Q4
Q2 流程确定? 确定→LangGraph或ADK / 开放→Q3
Q3 GCP生态? 是→ADK+DeepAgents / 否→LangGraph+DeepAgents
Q4 核心? 多Agent协作→Q5 / 复杂流程编排→Q6
Q5 Demo还是生产? Demo→CrewAI / 生产→ADK
Q6 复杂状态/并行/循环? 是→LangGraph / 否→Q7
Q7 团队规模? 小→CrewAI / 中→LangGraph / 大→ADK
```

## 运行

```bash
python3 33_framework_decision/decision_tree_cli.py                       # 三个内置示例
python3 33_framework_decision/decision_tree_cli.py --high-risk yes --flow open --gcp no
python3 33_framework_decision/project_recommendations.py
python3 33_framework_decision/hybrid_patterns.py
python3 33_framework_decision/migration_scripts.py
python3 33_framework_decision/demo.py                                    # 连续项目阶段入口
```

依赖可选：`pip install langgraph crewai google-adk deepagents`。CLI 与推荐脚本无需任何第三方库；混用脚本缺库自动回退。全部 exit 0，不联网。
