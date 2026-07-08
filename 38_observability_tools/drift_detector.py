"""模型行为漂移检测器。

对应文章第七节"用途 1：模型行为漂移检测"。LLM 提供商经常悄悄升级模型，
"gpt-4o" 指向的版本可能换了、输出突然变化。工业级做法：每天用一份
"金标准 100 题"自动测一遍，对比历史输出，漂移超阈值就告警。

这里用零依赖的语义漂移近似（词袋 Jaccard 距离 + 长度变化）。
生产建议换成 embedding 余弦距离（如 text-embedding-3）做 compute_semantic_drift。
"""
from __future__ import annotations

import re

DRIFT_THRESHOLD = 0.25


def _tokens(text: str) -> set[str]:
    zh = set(re.findall(r"[一-鿿]", text))
    en = set(re.findall(r"[a-zA-Z0-9]+", text.lower()))
    return zh | en


def _jaccard_distance(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta and not tb:
        return 0.0
    inter = len(ta & tb)
    union = len(ta | tb)
    return 1.0 - inter / union if union else 0.0


def compute_semantic_drift(today: list[str], yesterday: list[str]) -> float:
    """两批输出的平均语义漂移（0=完全一致，1=完全不同）。"""
    n = min(len(today), len(yesterday))
    if n == 0:
        return 0.0
    total = 0.0
    for t, y in zip(today[:n], yesterday[:n]):
        lex = _jaccard_distance(t, y)
        # 长度剧变也是漂移信号
        len_change = abs(len(t) - len(y)) / max(len(t), len(y), 1)
        total += 0.7 * lex + 0.3 * len_change
    return round(total / n, 4)


def daily_drift_check(golden_today: list[str], golden_yesterday: list[str]) -> dict:
    score = compute_semantic_drift(golden_today, golden_yesterday)
    alert = score > DRIFT_THRESHOLD
    return {
        "drift_score": score,
        "threshold": DRIFT_THRESHOLD,
        "alert": alert,
        "message": "模型行为漂移异常，请人工审查" if alert else "输出稳定，无异常漂移",
    }


def main() -> None:
    # 金标准题库的两天输出（同题、同 model 名，但供应商可能悄悄换了权重）
    yesterday = [
        "RAG 是检索增强生成，先检索再生成。",
        "年假入职满 1 年可休 5 天。",
        "退款一般 3-7 个工作日到账。",
    ]
    today_stable = [
        "RAG 即检索增强生成，先检索文档再让模型生成。",
        "入职满 1 年可享 5 天带薪年假。",
        "退款通常 3 到 7 个工作日到账。",
    ]
    today_drifted = [
        "As an AI language model, I cannot be certain about RAG.",
        "关于年假的问题，建议您咨询 HR 部门获取准确信息。",
        "抱歉，我无法提供退款相关的具体时间。",
    ]

    print("=" * 56)
    print("模型行为漂移检测（每日金标准对比）")
    print("=" * 56)
    print("\n场景 A：正常波动（同义改写）")
    print(" ", daily_drift_check(today_stable, yesterday))
    print("\n场景 B：疑似供应商换模型（风格突变/开始拒答）")
    print(" ", daily_drift_check(today_drifted, yesterday))
    print("\n生产替代：compute_semantic_drift 换成 embedding 余弦距离，阈值按历史分布标定。")


if __name__ == "__main__":
    main()
