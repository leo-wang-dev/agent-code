# 40 · Prompt Injection 全景 —— 直接 / 间接 / 工具注入防御

配套文章：《Prompt Injection 全景 —— 直接 / 间接 / 工具注入》（系列第 40 篇）

## 产物对照表

| 文章承诺 | 文件 | 说明 |
|---------|------|------|
| 5 层防御完整实现 | `five_layer_defense.py` | 输入过滤/Prompt加固/工具脱敏/行为监控/审计冻结，端到端编排 |
| 字符规范化工具 | `char_normalizer.py` | NFKC + 去零宽/控制字符 + 限长，防不可见字符绕过 |
| Lakera Guard 接入示例 | `lakera_guard_client.py` | 商用检测模型，缺 key 走规则回退，不裸调网络 |
| Prompt-Guard 自部署 demo | `prompt_guard_selfhost.py` | Meta 开源 BERT 检测，transformers 保护 + 启发式回退 |
| 行为白名单引擎 | `behavior_whitelist.py` | 角色工具白名单 + HITL + 行为指纹阈值 |
| Red Team 自动化测试套件 | `redteam_suite.py` | 内置 6 类攻击样本，输出拦截统计表 + 漏报/误报 |

## 运行

```bash
python3 char_normalizer.py        # 字符规范化演示
python3 lakera_guard_client.py    # Injection 检测（规则回退）
python3 prompt_guard_selfhost.py  # Prompt-Guard 分类（启发式回退）
python3 behavior_whitelist.py     # 行为白名单
python3 five_layer_defense.py     # 五层端到端
python3 redteam_suite.py          # Red Team 拦截统计表
```

## 生产替代

- `lakera_guard_client`：设 `LAKERA_GUARD_API_KEY` 启用商用检测（70-90% 拦截）。
- `prompt_guard_selfhost`：`pip install transformers torch` + `meta-llama/Prompt-Guard-86M`，可离线自部署。
- Layer 1 策略 B（安全分类 LLM）与 Layer 4 多 LLM 投票需接真实 LLM；本仓用规则/启发式做确定性演示。
- Red Team 拦截率 100% 是因内置样本均命中规则；真实攻击变体会绕过，须持续扩充样本、叠加专用模型。防御目标是压低攻击 ROI，而非消灭攻击。
