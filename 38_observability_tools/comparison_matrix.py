"""三家可观测平台功能对比矩阵 + 选型决策。

对应文章第五节。数据即文章表格，零依赖，可 import 复用。
"""
from __future__ import annotations

VENDORS = ["LangSmith", "Langfuse", "Helicone"]

# 每个维度：{vendor: 评价}
MATRIX = {
    "开源": {"LangSmith": "❌", "Langfuse": "✅", "Helicone": "⚠️ 部分"},
    "自部署": {"LangSmith": "商业版可(贵)", "Langfuse": "✅ 完全", "Helicone": "有,弱"},
    "接入难度": {"LangSmith": "低(LangChain)", "Langfuse": "中", "Helicone": "最低"},
    "Trace 可视化": {"LangSmith": "强", "Langfuse": "强", "Helicone": "中"},
    "Agent 多步流程": {"LangSmith": "强", "Langfuse": "强", "Helicone": "弱"},
    "评测集成": {"LangSmith": "强", "Langfuse": "强", "Helicone": "弱"},
    "Prompt 管理": {"LangSmith": "强", "Langfuse": "强", "Helicone": "弱"},
    "成本追踪": {"LangSmith": "强", "Langfuse": "强", "Helicone": "最强"},
    "OTel 集成": {"LangSmith": "中", "Langfuse": "中", "Helicone": "最强"},
    "国内访问": {"LangSmith": "难", "Langfuse": "容易(自部署)", "Helicone": "难"},
    "价格": {"LangSmith": "$$$", "Langfuse": "免费/$", "Helicone": "$$"},
    "学习曲线": {"LangSmith": "中", "Langfuse": "中", "Helicone": "最低"},
}

DECISION = [
    ("用 LangChain/LangGraph + 数据可出境", "LangSmith"),
    ("国内项目 + 数据不能出境", "Langfuse 自部署"),
    ("多用户/多团队企业项目", "Langfuse"),
    ("想要 Prompt 管理 + 评测一体化", "Langfuse"),
    ("只想看成本 + 最快接入", "Helicone"),
    ("已经有公司 OTel 基础设施", "Helicone"),
    ("大型企业、要求严格审计", "Langfuse 自部署"),
]


def _pad(s: str, width: int) -> str:
    # 中文占 2 宽度，简单对齐
    w = sum(2 if ord(c) > 127 else 1 for c in s)
    return s + " " * max(0, width - w)


def print_matrix() -> None:
    print("三家横评矩阵")
    header = _pad("维度", 18) + "".join(_pad(v, 16) for v in VENDORS)
    print(header)
    print("-" * len(header))
    for dim, row in MATRIX.items():
        line = _pad(dim, 18) + "".join(_pad(row[v], 16) for v in VENDORS)
        print(line)


def print_decision() -> None:
    print("\n选型决策")
    print("-" * 50)
    for scene, rec in DECISION:
        print(f"  {_pad(scene, 40)} → {rec}")


def main() -> None:
    print_matrix()
    print_decision()


if __name__ == "__main__":
    main()
