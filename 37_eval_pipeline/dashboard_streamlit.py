"""Streamlit 评测仪表盘。

对应文章第五节。评测数据要让业务方 / 产品 / 管理层都能看懂，不能只是工程师的 JSON。
四个面板：核心指标趋势 / 评测集分类得分 / Bad Case 漂移分析 / A/B 实验列表。

运行：
    pip install streamlit
    streamlit run dashboard_streamlit.py

缺 streamlit 时，本文件降级为纯文本渲染同样的四个面板（终端可读），保证可运行。
数据源这里用内置 mock；生产接 PostgreSQL / Langfuse 即可。
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# mock 数据（生产替换为查询 PostgreSQL / Langfuse 的结果）
# ---------------------------------------------------------------------------
METRIC_TREND = {
    "Context Precision": [0.78, 0.81, 0.83, 0.85],
    "Context Recall": [0.85, 0.82, 0.86, 0.84],
    "Faithfulness": [0.91, 0.89, 0.92, 0.93],
    "Answer Relevancy": [0.86, 0.87, 0.85, 0.88],
}

CATEGORY_SCORES = {
    "退货咨询": 0.87,
    "订单查询": 0.94,
    "投诉处理": 0.73,  # 得分低，需重点优化
    "闲聊": 0.98,
    "产品咨询": 0.85,
}

BAD_CASE_DRIFT = {
    "RAG 召回错误": (0.45, 0.32),   # (本月, 上月)
    "Prompt 漏覆盖": (0.20, 0.28),
    "工具调用失败": (0.15, 0.18),
    "模型幻觉": (0.12, 0.10),
    "其他": (0.08, 0.12),
}

AB_EXPERIMENTS = [
    {
        "id": "EXP-2026-05-01",
        "name": "Chunking 升级到 SEMANTIC",
        "status": "灰度 25%",
        "offline": "+4.2%, p=0.012",
        "online": "+3.8% (置信区间 [+1.2%, +6.4%])",
    },
    {
        "id": "EXP-2026-05-08",
        "name": "切换 reranker 到 voyage-rerank-2",
        "status": "全量观察",
        "offline": "+6.1%, p<0.001",
        "online": "+5.5% (1 周)",
    },
]


def _trend_arrow(series: list[float]) -> str:
    if series[-1] > series[0] + 0.005:
        return "↗"
    if series[-1] < series[0] - 0.005:
        return "↘"
    return "→"


def _bar(pct: float, width: int = 10) -> str:
    filled = round(pct * width)
    return "█" * filled + "░" * (width - filled)


# ---------------------------------------------------------------------------
# Streamlit 渲染
# ---------------------------------------------------------------------------
def render_streamlit() -> None:
    import streamlit as st  # type: ignore

    st.set_page_config(page_title="LLM 评测仪表盘", layout="wide")
    st.title("LLM 评测仪表盘")

    st.header("面板 1 · 核心指标趋势")
    st.line_chart({k: v for k, v in METRIC_TREND.items()})

    st.header("面板 2 · 评测集分类得分")
    st.bar_chart(CATEGORY_SCORES)

    st.header("面板 3 · Bad Case 漂移分析（本月 vs 上月）")
    st.dataframe(
        {
            "类型": list(BAD_CASE_DRIFT.keys()),
            "本月": [f"{v[0]:.0%}" for v in BAD_CASE_DRIFT.values()],
            "上月": [f"{v[1]:.0%}" for v in BAD_CASE_DRIFT.values()],
        }
    )

    st.header("面板 4 · A/B 实验列表")
    st.table(AB_EXPERIMENTS)


# ---------------------------------------------------------------------------
# 纯文本降级渲染
# ---------------------------------------------------------------------------
def render_text() -> None:
    print("=" * 60)
    print("LLM 评测仪表盘（文本降级版）")
    print("=" * 60)

    print("\n[面板 1] 核心指标趋势")
    for name, series in METRIC_TREND.items():
        arrows = " → ".join(f"{v:.2f}" for v in series)
        print(f"  {name:<20} {arrows} {_trend_arrow(series)}")

    print("\n[面板 2] 评测集分类得分")
    for cat, score in CATEGORY_SCORES.items():
        flag = "  ← 得分低，需重点优化" if score < 0.8 else ""
        print(f"  {cat:<8} {_bar(score)} {score:.0%}{flag}")

    print("\n[面板 3] Bad Case 漂移分析（过去 30 天）")
    for typ, (cur, prev) in BAD_CASE_DRIFT.items():
        trend = "↑ 警示" if cur > prev + 0.02 else "↓" if cur < prev - 0.02 else "→"
        print(f"  {typ:<14} {cur:.0%} (上月 {prev:.0%}) {trend}")

    print("\n[面板 4] 正在跑的 A/B 实验")
    for exp in AB_EXPERIMENTS:
        print(f"  {exp['id']}: {exp['name']}  状态: {exp['status']}")
        print(f"    离线: {exp['offline']}  |  线上: {exp['online']}")


def main() -> None:
    try:
        import streamlit  # noqa: F401  # type: ignore

        # 被 `streamlit run` 拉起时才真正渲染 UI
        import sys

        if any("streamlit" in a for a in sys.argv):
            render_streamlit()
            return
        print("[提示] 已安装 streamlit。用 `streamlit run dashboard_streamlit.py` 打开可视化面板。")
        print("       以下是文本降级预览：\n")
        render_text()
    except ImportError:
        print("[提示] 未安装 streamlit，使用文本降级渲染。生产安装：pip install streamlit\n")
        render_text()


if __name__ == "__main__":
    main()
