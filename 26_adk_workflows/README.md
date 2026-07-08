# 26_adk_workflows —— ADK 多 Agent 编排：四种 Workflow 与 Delegation

配套文章：《ADK 多 Agent 编排 —— Sequential / Parallel / Loop / Delegation 四种 Workflow》

在原有 `demo.py`（连续项目入口）之外，补齐文章文末"包含："承诺的每一件具名产物，均为**独立可运行**脚本。
约定同全系列：`google-adk` 导入 `try/except` 保护，缺依赖打印安装指引并降级到**确定性 mock**，`exit 0`；无 API key 时模型调用走 mock，不联网。

## 安装（跑真实 ADK 时）

```bash
pip install google-adk
export GOOGLE_API_KEY=...   # 或 GEMINI_API_KEY
```

## 产物对照表

| 文章承诺产物 | 文件 | 说明 | 运行 |
|---|---|---|---|
| Sequential Workflow | `sequential_workflow.py` | `output_key` + `{template}` 数据总线顺序执行 | `python3 26_adk_workflows/sequential_workflow.py` |
| Parallel Workflow | `parallel_workflow.py` | 并行 + 演示共写字段的 race condition | `python3 26_adk_workflows/parallel_workflow.py` |
| Loop Workflow | `loop_workflow.py` | `max_iterations` 兜底退出 | `python3 26_adk_workflows/loop_workflow.py` |
| Delegation Workflow | `delegation_workflow.py` | `sub_agents` 自动注入 + `transfer_to_agent` 路由 + fallback | `python3 26_adk_workflows/delegation_workflow.py` |
| escalate 退出循环 demo | `escalate_loop_exit.py` | 工具 `actions.escalate=True` 主动跳出 LoopAgent | `python3 26_adk_workflows/escalate_loop_exit.py` |
| Delegation 路由准确率监控 | `delegation_routing_accuracy.py` | 标注样例集统计准确率 + 混淆矩阵 + 误判样例 | `python3 26_adk_workflows/delegation_routing_accuracy.py` |
| 嵌套组合工业级模式 | `nested_composition.py` | Delegation 内挂 Sequential/Parallel/Loop 子流程 | `python3 26_adk_workflows/nested_composition.py` |

## 四种 Workflow 选型

| 任务特征 | 推荐 | 文件 |
|---|---|---|
| 步骤明确、顺序固定 | Sequential | `sequential_workflow.py` |
| 多维度独立任务、可并行 | Parallel | `parallel_workflow.py` |
| 自我反思 / 迭代优化 | Loop | `loop_workflow.py` / `escalate_loop_exit.py` |
| 开放对话 / 意图路由 | Delegation | `delegation_workflow.py` |
| 复杂混合场景 | 嵌套组合 | `nested_composition.py` |

> `demo.py` 仍是连续项目的第 26 章阶段入口，不受本目录新增文件影响。
