# 03 · Prompt 不是咒语，是结构化的上下文注入

对应文章《Prompt 不是咒语，是结构化的上下文注入》（系列第 03 篇）。

Prompt 的本质：用一段结构化文本，给一个无状态的概率模型，注入它做出期望输出所需的全部上下文。每个文件对应文章一节，全部离线可跑、确定性输出。

## 产物 → 文件 → 运行命令

| 文章对应 | 产物 | 文件 | 运行命令 |
|---|---|---|---|
| §一 四种上下文 | Who/What/Context/How 四类上下文组装与 token 占比 | `four_context_types.py` | `python3 four_context_types.py` |
| §二 System 优先级 | 统计倾向 + Lost in the Middle 位置权重 + 别把数据塞 System | `system_prompt_priority.py` | `python3 system_prompt_priority.py` |
| §三 Few-shot 本质 | 无示例 vs 2-shot 的格式拉齐对比 | `few_shot_templating.py` | `python3 few_shot_templating.py` |
| §四 输出格式控制 | 正则脆弱 vs Function Calling/schema 稳定 | `structured_output.py` | `python3 structured_output.py` |
| §五 CoT 取舍 | CoT token 成本量化 + 该不该上 CoT | `cot_tradeoff.py` | `python3 cot_tradeoff.py` |
| §六/§七 Prompt 是代码 | 版本化/参数化/回归/diff 最小闭环 | `prompt_as_code.py` | `python3 prompt_as_code.py` |
| 汇总 | 模板注册 + 工具调用 + 严格 JSON | `run_demo.py` | `python3 run_demo.py` |

## 一次跑全部

```bash
for f in four_context_types system_prompt_priority few_shot_templating structured_output cot_tradeoff prompt_as_code; do
  echo "===== $f ====="; python3 "$f.py"; echo
done
```

## 复用的核心实现

复用 `src/agent_code/prompt_essence.py`：`PromptTemplate` / `PromptRegistry`（版本化与 diff）、`validate_json_schema` / `dumps_strict_json`（结构化输出）、`classify_ticket_as_tool_call` / `parse_natural_language_classifier`（工具调用 vs 正则）、`estimate_cot_cost`（CoT 成本）。
