"""4 种内置 Evaluator 用法 —— Trajectory / Response / Faithfulness / Composite。

对应文章第一节四种 Evaluator。

    TrajectoryEvaluator   工具调用序列是否正确（EXACT / IN_ORDER / ANY_ORDER）
    ResponseEvaluator     文本回答是否相似（此处用确定性词重叠近似 ROUGE）
    FaithfulnessEvaluator  回答是否基于工具输出（防幻觉），文章公式：
        Faithfulness = 0.6 × (回答关键事实出现在工具输出的比例)
                     + 0.4 × (回答关键事实出现在用户问题中的比例)
    CompositeEvaluator    多维度加权综合

本脚本用确定性 mock 实现四个 Evaluator（无需 google-adk / 模型 / 网络）。
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass

try:  # google-adk 导入 try/except 保护
    from google.adk.evaluation import AgentEvaluator  # noqa: F401

    HAS_ADK = True
except ImportError:
    HAS_ADK = False


# ---------------------------------------------------------------------------
# 1. TrajectoryEvaluator —— 工具调用序列匹配
# ---------------------------------------------------------------------------
class TrajectoryEvaluator:
    def __init__(self, match_type: str = "EXACT") -> None:
        assert match_type in {"EXACT", "IN_ORDER", "ANY_ORDER"}
        self.match_type = match_type

    def evaluate(self, expected: list[str], actual: list[str]) -> float:
        if self.match_type == "EXACT":
            return 1.0 if expected == actual else 0.0
        if self.match_type == "ANY_ORDER":
            return 1.0 if set(expected) <= set(actual) else 0.0
        # IN_ORDER：期望序列是实际序列的子序列（允许额外调用）
        it = iter(actual)
        return 1.0 if all(e in it for e in expected) else 0.0


# ---------------------------------------------------------------------------
# 2. ResponseEvaluator —— 文本相似度（确定性 bigram 重叠 F1）
# ---------------------------------------------------------------------------
class ResponseEvaluator:
    @staticmethod
    def _grams(s: str) -> set[str]:
        s = re.sub(r"\s+", "", s)
        return {s[i:i + 2] for i in range(len(s) - 1)}

    def evaluate(self, reference: str, response: str) -> float:
        ref, res = self._grams(reference), self._grams(response)
        if not ref or not res:
            return 0.0
        inter = len(ref & res)
        precision = inter / len(res)
        recall = inter / len(ref)
        if precision + recall == 0:
            return 0.0
        return round(2 * precision * recall / (precision + recall), 3)


# ---------------------------------------------------------------------------
# 3. FaithfulnessEvaluator —— 幻觉检测（文章加权公式）
# ---------------------------------------------------------------------------
class FaithfulnessEvaluator:
    @staticmethod
    def _facts(answer: str) -> list[str]:
        parts = re.split(r"[，。,\.\s]+", answer)
        return [p for p in parts if p]

    def evaluate(self, question: str, tool_output: str, answer: str) -> float:
        facts = self._facts(answer)
        if not facts:
            return 0.0
        in_tool = sum(1 for f in facts if f in tool_output) / len(facts)
        in_question = sum(1 for f in facts if f in question) / len(facts)
        return round(0.6 * in_tool + 0.4 * in_question, 3)


# ---------------------------------------------------------------------------
# 4. CompositeEvaluator —— 多维度加权
# ---------------------------------------------------------------------------
@dataclass
class CompositeEvaluator:
    weights: dict           # {"trajectory": 0.3, "faithfulness": 0.4, "quality": 0.3}
    threshold: float = 0.7

    def evaluate(self, scores: dict) -> dict:
        total = sum(scores[k] * w for k, w in self.weights.items())
        total = round(total, 3)
        return {"composite": total, "passed": total >= self.threshold, "detail": scores}


def main() -> int:
    if not HAS_ADK:
        print("[提示] 未检测到 google-adk，使用确定性 mock 实现四种 Evaluator。")
        print("       安装： pip install google-adk")
        print("-" * 60)

    print("== 1. TrajectoryEvaluator ==")
    expected = ["search_web", "summarize_text"]
    for mt, actual in [("EXACT", ["search_web", "summarize_text"]),
                       ("EXACT", ["summarize_text", "search_web"]),
                       ("IN_ORDER", ["search_web", "rerank", "summarize_text"]),
                       ("ANY_ORDER", ["summarize_text", "search_web"])]:
        score = TrajectoryEvaluator(mt).evaluate(expected, actual)
        print(f"   [{mt:9}] actual={actual} -> {score}")

    print("\n== 2. ResponseEvaluator（与 reference 比对） ==")
    re_eval = ResponseEvaluator()
    ref = "上海今天22°C多云"
    for resp in ["上海今天22°C多云", "上海今天晴热35°C"]:
        print(f"   resp={resp!r} -> {re_eval.evaluate(ref, resp)}")

    print("\n== 3. FaithfulnessEvaluator（防幻觉，加权公式） ==")
    fe = FaithfulnessEvaluator()
    q = "上海今天天气怎么样？"
    tool = "上海今天 22°C，多云。"
    cases = {
        "A 忠实": "上海今天 22°C，多云。",
        "B 编造": "上海今天 25°C，下雨。",
        "C 夹带": "上海今天 22°C，多云，建议带伞。",
    }
    for label, ans in cases.items():
        print(f"   {label}: {fe.evaluate(q, tool, ans)}  <- {ans}")
    print("   注：文章内联的 1.0/0.0/0.5 是示意；加权公式给出的是上面这组分级分，")
    print("       但排序一致（忠实 > 夹带 > 编造），足以卡出幻觉。")

    print("\n== 4. CompositeEvaluator（多维加权，阈值 0.7） ==")
    composite = CompositeEvaluator(
        weights={"trajectory": 0.3, "faithfulness": 0.4, "quality": 0.3}, threshold=0.7)
    result = composite.evaluate({"trajectory": 1.0, "faithfulness": 0.73, "quality": 0.8})
    print("  ", result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
