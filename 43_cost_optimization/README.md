# 43 · Token 成本拆解 + Prompt 压缩

配套文章：《Token 成本拆解 + Prompt 压缩》（系列第 43 篇）。

全部离线可运行，无需 API Key。可选依赖 `tiktoken`（未装则自动用 CJK 启发式估算）、
`llmlingua`（未装则用等价的离线降级压缩）。

## 文章"包含"清单 → 文件对照

| 文章承诺的产物 | 文件 | 运行 |
|---|---|---|
| 成本归因仪表盘 | `cost_attribution.py` | `python3 cost_attribution.py` |
| LLMLingua 完整集成示例 | `llmlingua_integration.py` | `python3 llmlingua_integration.py` |
| System Prompt 优化对照实验 | `system_prompt_optimization.py` | `python3 system_prompt_optimization.py` |
| 工具描述压缩工具 | `tool_description_compression.py` | `python3 tool_description_compression.py` |
| 对话历史分层摘要实现 | `history_layered_summary.py` | `python3 history_layered_summary.py` |

辅助模块：`_tokens.py`（token 估算 + 价格表，被上面各文件复用）。

原有入口 `demo.py`（调 `series_projects.chapter_runner`）保持不变。

## 生产替换点

- `_tokens.estimate_tokens`：装 `tiktoken` 后自动走真实 tokenizer。
- `llmlingua_integration`：装 `llmlingua` 后 `compress()` 自动走真实小模型打分；
  否则用词表近似的离线降级实现（接口一致）。
- `history_layered_summary._summarize`：离线抽取式摘要，生产替换为一次小模型抽象式摘要调用。

## 依赖安装（可选，装了效果更真实）

```bash
pip install tiktoken llmlingua
```
