# 37 · 评测流水线工业级实现 —— Bad Case 闭环与 CI 集成

配套文章：《评测流水线工业级实现 —— 从 Bad Case 闭环到 CI 集成》（系列第 37 篇）

## 产物对照表

| 文章承诺 | 文件 | 说明 |
|---------|------|------|
| 评测集 schema 模板 | `eval_schema.py` + `cases/case_001.yaml` | 带完整元数据的 case 模板 + 零依赖校验器 |
| Bad Case 自动采样系统 | `bad_case_sampler.py` | 6 条采样规则、Bad Case 池落盘、按规则统计 |
| GitHub Actions 三级评测流水线 | `github_actions_eval.yml` | Smoke / Regression / Full 三级，放到 `.github/workflows/` 即生效 |
| A/B 实验显著性检验工具 | `ab_significance.py` | 配对 t-test，scipy / 零依赖双实现，PROCEED/REJECT/NO_CHANGE 决策 |
| Streamlit 评测仪表盘 | `dashboard_streamlit.py` | 四面板（趋势/分类/漂移/AB），streamlit / 文本降级双模式 |

## 运行

```bash
python3 eval_schema.py           # 校验评测集（缺 pyyaml 走内置样例）
python3 bad_case_sampler.py      # 跑一遍自动采样，落盘 bad_case_pool.json
python3 ab_significance.py       # 配对 t-test 显著性判定
python3 dashboard_streamlit.py   # 文本预览；streamlit run 打开可视化
```

## 生产替代

- `pip install pyyaml` 后 `eval_schema.py` 读真实 `cases/*.yaml`。
- `pip install scipy` 后 A/B 检验走 scipy（否则用自带 Student-t CDF，数值一致）。
- `pip install streamlit` 后 `streamlit run dashboard_streamlit.py` 打开可视化，数据源换成 PostgreSQL/Langfuse。
- `github_actions_eval.yml` 中的 `promptfoo/ragas/deepeval` 命令与 `eval/*.py` 脚本按你的评测集路径落地。
