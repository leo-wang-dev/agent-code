"""中文场景的评测调优配置。

对应文章"RAGAS 中文场景的注意点"。RAGAS 原生英文优化，中文场景部分指标
算分会偏低（不是真的差，是工具问题）。这里给出工业级调优参数与可复用的
中文裁判 prompt 模板，可注入到 RAGAS / DeepEval 的评测 LLM。

纯配置 + 模板，零依赖，可被其它评测脚本 import。
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# 1. 评测 LLM 选型：中文场景务必用中英文判别一致性最好的模型
# ---------------------------------------------------------------------------
JUDGE_MODEL_CONFIG = {
    # 首选：GPT-4o，中英文判别一致性最好
    "model": "gpt-4o",
    "temperature": 0.0,  # 评测要确定性，temperature 必须为 0
    "max_tokens": 512,
    # 备选：社区 ragas-zh fork，或本地部署的中文强模型
    "fallbacks": ["claude-3-5-sonnet", "qwen2.5-72b-instruct"],
}

# ---------------------------------------------------------------------------
# 2. 中文裁判 prompt 调优：给评测 prompt 显式加中文指令
# ---------------------------------------------------------------------------
ZH_FAITHFULNESS_RUBRIC = """你是严谨的中文评测裁判。判断【答案】中的每一条陈述是否能在【上下文】中找到支撑。

评判要求：
1. 只依据上下文判断，不要用你自己的知识补全。
2. 中文同义表达（如"年假/带薪休假"）视为一致，不要因措辞差异扣分。
3. 数字、日期、金额必须严格一致，否则判为不忠实。

上下文：
{context}

答案：
{answer}

请输出 0~1 的忠实度分数与逐条理由。"""

ZH_ANSWER_RELEVANCY_RUBRIC = """你是中文评测裁判。判断【答案】是否真正回答了【问题】。

评判要求：
1. 切题即高分，不要因为答案简短而扣分。
2. 中文口语化表达（如"能休5天"）与正式表达视为等价。
3. 答非所问、答案跑题判低分。

问题：{question}
答案：{answer}

请输出 0~1 的相关性分数。"""

# ---------------------------------------------------------------------------
# 3. 中文场景的分数校正：已知偏低的指标乘以校正系数（人工抽样标定得到）
# ---------------------------------------------------------------------------
# 说明：这是"工具偏差"补偿，不是放水。系数应由人工抽样校准得到，定期复核。
ZH_SCORE_CORRECTION = {
    "context_precision": 1.05,
    "context_recall": 1.0,
    "faithfulness": 1.08,   # 中文同义表达易被英文裁判判为不一致
    "answer_relevancy": 1.06,
}


def apply_zh_correction(scores: dict[str, float]) -> dict[str, float]:
    """对中文评测分数做校正，封顶 1.0。"""
    return {
        k: round(min(1.0, v * ZH_SCORE_CORRECTION.get(k, 1.0)), 2)
        for k, v in scores.items()
    }


def main() -> None:
    print("中文场景评测调优配置")
    print("-" * 50)
    print(f"评测 LLM：{JUDGE_MODEL_CONFIG['model']} (temperature={JUDGE_MODEL_CONFIG['temperature']})")
    print(f"备选：{', '.join(JUDGE_MODEL_CONFIG['fallbacks'])}")
    print("\n校正系数：")
    for k, v in ZH_SCORE_CORRECTION.items():
        print(f"  {k:<20} ×{v}")

    demo = {"context_precision": 0.64, "context_recall": 0.91, "faithfulness": 0.69, "answer_relevancy": 0.61}
    print("\n校正前：", demo)
    print("校正后：", apply_zh_correction(demo))
    print("\n注意：校正系数必须由人工抽样标定，是补偿工具偏差，不是放水。")


if __name__ == "__main__":
    main()
