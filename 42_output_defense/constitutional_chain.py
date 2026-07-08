"""宪法链（Constitutional Chain）多场景 demo。

对应文章第二节。Constitutional AI（Anthropic 提出）给 Agent 一套"宪法"（核心价值观），
让 Agent 在输出前自己审视是否违背；违背则重写，严重违规则拦截。

  [初始回答] → [宪法 Agent 审视] --违背--> [重写] → [再审视] --通过--> [返回]

宪法 Agent 用一次独立 LLM 调用做判别（成本/延迟翻倍），生产只对高风险场景
（客服/医疗/法律/金融）启用。

本文件用确定性 mock reviewer（规则匹配宪法条款）替代 LLM 裁判，保证可复现。
接真实 LLM 时把 `_mock_review` 换成 constitutional_review 的 prompt 调用即可。
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# 宪法条款（标准结构，生产用 Git 版本管理 + 评测）
# ---------------------------------------------------------------------------
CONSTITUTION = [
    {"id": "no_personal_info_leak", "rule": "回答中不能包含其他用户的姓名、电话、邮箱、身份证号", "severity": "critical"},
    {"id": "no_unauthorized_promise", "rule": "回答中不能承诺超出公司政策的退款、补偿或服务", "severity": "high"},
    {"id": "no_competitor_promotion", "rule": "回答中不能推荐竞争对手的产品", "severity": "high"},
    {"id": "no_offensive_content", "rule": "回答不能包含冒犯、歧视、不当内容", "severity": "critical"},
    {"id": "factual_in_company_domain", "rule": "涉及公司产品和政策时必须基于知识库，不能编造", "severity": "high"},
    {"id": "no_legal_advice", "rule": "不能提供法律建议", "severity": "medium"},
]

_SEVERITY_RANK = {"critical": 3, "high": 2, "medium": 1}

# 规则化违规检测（mock LLM 裁判）
_DETECTORS = {
    "no_personal_info_leak": lambda t: bool(re.search(r"1[3-9]\d{9}|[\w.+-]+@[\w-]+\.\w+", t)),
    "no_unauthorized_promise": lambda t: any(w in t for w in ["全额退款", "无条件退", "永久免费", "包赔"]),
    "no_competitor_promotion": lambda t: any(w in t for w in ["竞品", "隔壁家", "建议买别家"]),
    "no_offensive_content": lambda t: any(w in t for w in ["垃圾", "傻", "滚"]),
    "factual_in_company_domain": lambda t: "据我所知可能" in t or "应该大概是" in t,
    "no_legal_advice": lambda t: any(w in t for w in ["您应该起诉", "法律上您可以", "建议走法律程序"]),
}


@dataclass
class Review:
    verdict: str  # PASS / NEEDS_REVISION / BLOCK
    violations: list[dict]


def _mock_review(response: str) -> Review:
    violations = []
    for clause in CONSTITUTION:
        det = _DETECTORS.get(clause["id"])
        if det and det(response):
            violations.append(clause)
    if not violations:
        return Review("PASS", [])
    worst = max(_SEVERITY_RANK[v["severity"]] for v in violations)
    verdict = "BLOCK" if worst == 3 else "NEEDS_REVISION"
    return Review(verdict, violations)


def _mock_revise(response: str, violations: list[dict]) -> str:
    """让原 Agent 依据违规重写（此处 mock：删除违规片段）。"""
    revised = response
    ids = {v["id"] for v in violations}
    if "no_personal_info_leak" in ids:
        revised = re.sub(r"1[3-9]\d{9}", "[已隐去]", revised)
        revised = re.sub(r"[\w.+-]+@[\w-]+\.\w+", "[已隐去]", revised)
    if "no_unauthorized_promise" in ids:
        for w in ["全额退款", "无条件退", "永久免费", "包赔"]:
            revised = revised.replace(w, "按公司政策处理")
    if "no_competitor_promotion" in ids:
        revised = "很抱歉，我只能介绍本公司产品。"
    return revised


def constitutional_chain(response: str, max_rounds: int = 2) -> dict:
    """宪法链：审视 → 重写 → 再审视，最多 max_rounds 轮。"""
    current = response
    trace = []
    for _round in range(max_rounds):
        review = _mock_review(current)
        trace.append({"verdict": review.verdict, "violations": [v["id"] for v in review.violations]})
        if review.verdict == "PASS":
            return {"final": current, "verdict": "PASS", "trace": trace}
        if review.verdict == "BLOCK":
            return {
                "final": "抱歉，我不能这样回答。请换个方式描述您的需求。",
                "verdict": "BLOCK",
                "trace": trace,
            }
        # NEEDS_REVISION → 重写后再来一轮
        current = _mock_revise(current, review.violations)
    # 轮次用尽仍未 PASS
    return {"final": current, "verdict": "REVISED_MAX_ROUNDS", "trace": trace}


def main() -> None:
    print("=" * 60)
    print("宪法链多场景演示")
    print("=" * 60)
    scenarios = {
        "正常回答": "为您推荐这款保湿面霜，适合秋冬使用。",
        "越权承诺(high→重写通过)": "没问题，我给您办理全额退款并永久免费续费。",
        "泄露他人隐私(critical→拦截)": "上一位客户张伟的电话 13800138000，您可参考。",
        "冒犯内容(critical→拦截)": "你这个问题真垃圾，不想回答。",
    }
    for name, resp in scenarios.items():
        result = constitutional_chain(resp)
        print(f"\n[{name}] verdict={result['verdict']}")
        print(f"  原始: {resp}")
        print(f"  最终: {result['final']}")
        print(f"  链路: {result['trace']}")


if __name__ == "__main__":
    main()
