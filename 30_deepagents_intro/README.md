# 30_deepagents_intro —— DeepAgents：Harness vs Framework vs Runtime

配套第 30 篇《DeepAgents 是什么》。除章节连续项目入口 `demo.py` 外，本目录补齐了文末承诺的四个产物。

## 文章产物 → 文件对照表

| 文章承诺 | 文件 | 说明 |
|---------|------|------|
| DeepAgents 极简 demo（5 行 = 一个 Agent） | `deepagents_minimal.py` | 真 SDK；缺 `deepagents` 打印安装指引，缺 key 只组装不调用 |
| 180 行手搓 Harness 完整实现 | `handwritten_harness.py` | 纯标准库，State/TODO/虚拟FS/子Agent/SystemPrompt/ReAct 六段全实现，确定性 mock 驱动 |
| LangGraph + DeepAgents 混合示例 | `hybrid_langgraph_deepagents.py` | 报销审批：LangGraph 骨架 + Harness 生成审核理由；缺任一库回退纯 Python |
| 三层抽象对比代码 | `three_layer_abstraction.py` | Runtime/Framework/Harness 定位、工程类比、选型自测 |
| 章节连续项目入口 | `demo.py` | `SourcingAgentProject` 第 30 阶段（未改动） |

## 运行

```bash
python3 30_deepagents_intro/handwritten_harness.py        # 无需任何依赖
python3 30_deepagents_intro/three_layer_abstraction.py    # 无需任何依赖
python3 30_deepagents_intro/hybrid_langgraph_deepagents.py # 缺库自动回退
python3 30_deepagents_intro/deepagents_minimal.py         # 缺 deepagents 打印指引
python3 30_deepagents_intro/demo.py                       # 连续项目阶段入口
```

## 依赖（可选）

```bash
pip install deepagents   # 自动带 langchain>=1.2.11 / langgraph>=1.1.1
export ANTHROPIC_API_KEY=sk-ant-...   # 仅真实调用时需要
```

缺依赖或缺 key 时所有脚本都以 exit 0 正常结束，不联网、不报错。
