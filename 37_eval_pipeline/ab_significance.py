"""A/B 实验显著性检验工具。

对应文章第四节。判断实验组是否显著优于对照组，决策：
  - 关键指标显著提升 + 无显著下降 → PROCEED（进灰度）
  - 关键指标显著下降 → REJECT
  - 无显著差异 → NO_CHANGE（默认保持现状，不引入未知风险）

优先用 scipy 的配对 t-test；缺 scipy 时用零依赖实现（自带 Student-t 分布 CDF，
基于正则化不完全 Beta 函数），结果与 scipy 数值一致，教学用完全够。
"""
from __future__ import annotations

import math

try:
    from scipy import stats  # type: ignore

    _HAS_SCIPY = True
except ImportError:
    _HAS_SCIPY = False


# ---------------------------------------------------------------------------
# 零依赖 Student-t 双尾 p 值（Numerical Recipes 的 betacf 连分式）
# ---------------------------------------------------------------------------
def _betacf(a: float, b: float, x: float) -> float:
    MAXIT, EPS, FPMIN = 200, 3.0e-12, 1.0e-30
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < FPMIN:
        d = FPMIN
    d = 1.0 / d
    h = d
    for m in range(1, MAXIT + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < EPS:
            break
    return h


def _betai(a: float, b: float, x: float) -> float:
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    bt = math.exp(
        math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
        + a * math.log(x) + b * math.log(1.0 - x)
    )
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def _t_sf_two_sided(t: float, df: float) -> float:
    """Student-t 双尾 p 值。"""
    return _betai(df / 2.0, 0.5, df / (df + t * t))


def _paired_ttest(experiment: list[float], baseline: list[float]) -> tuple[float, float]:
    """配对 t-test，返回 (t_stat, p_value)。"""
    if _HAS_SCIPY:
        t_stat, p_value = stats.ttest_rel(experiment, baseline)
        return float(t_stat), float(p_value)

    n = len(experiment)
    diffs = [e - b for e, b in zip(experiment, baseline)]
    mean_d = sum(diffs) / n
    var_d = sum((d - mean_d) ** 2 for d in diffs) / (n - 1)
    if var_d == 0:
        # 完全无差异
        return 0.0, 1.0
    se = math.sqrt(var_d / n)
    t_stat = mean_d / se
    p_value = _t_sf_two_sided(t_stat, n - 1)
    return t_stat, p_value


def evaluate_ab(baseline_scores: list[float], experiment_scores: list[float]) -> dict:
    """判断实验组是否显著优于对照组。"""
    if len(baseline_scores) != len(experiment_scores):
        raise ValueError("配对检验要求两组长度一致（每个 case 一对得分）")

    baseline_mean = sum(baseline_scores) / len(baseline_scores)
    experiment_mean = sum(experiment_scores) / len(experiment_scores)
    t_stat, p_value = _paired_ttest(experiment_scores, baseline_scores)

    if p_value < 0.05 and experiment_mean > baseline_mean:
        decision = "PROCEED"
    elif p_value < 0.05 and experiment_mean < baseline_mean:
        decision = "REJECT"
    else:
        decision = "NO_CHANGE"  # 无显著差异，保持现状

    return {
        "engine": "scipy" if _HAS_SCIPY else "stdlib",
        "baseline_mean": round(baseline_mean, 4),
        "experiment_mean": round(experiment_mean, 4),
        "improvement_pct": round((experiment_mean - baseline_mean) / baseline_mean * 100, 2),
        "t_stat": round(t_stat, 4),
        "p_value": round(p_value, 6),
        "is_significant": p_value < 0.05,
        "decision": decision,
    }


def main() -> None:
    # 模拟 20 个 case 上，两个版本的 RAG 综合分（实验组略优且稳定）
    baseline = [0.78, 0.80, 0.75, 0.82, 0.79, 0.77, 0.81, 0.76, 0.80, 0.78,
                0.79, 0.83, 0.74, 0.80, 0.77, 0.81, 0.78, 0.79, 0.76, 0.80]
    experiment = [0.82, 0.83, 0.79, 0.85, 0.83, 0.80, 0.84, 0.81, 0.84, 0.82,
                  0.83, 0.86, 0.78, 0.84, 0.81, 0.85, 0.82, 0.83, 0.80, 0.84]

    print("=" * 56)
    print("A/B 显著性检验（配对 t-test）")
    print("=" * 56)
    result = evaluate_ab(baseline, experiment)
    for k, v in result.items():
        print(f"  {k:<16} {v}")
    print("\n工程纪律：无显著差异（NO_CHANGE）默认保持现状——不显著的改动不值得引入维护成本。")


if __name__ == "__main__":
    main()
