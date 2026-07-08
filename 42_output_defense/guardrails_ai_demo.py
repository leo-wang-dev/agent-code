"""Guardrails AI 接入 —— 程序化的输出过滤（毫秒级、确定性强）。

对应文章第三节。Guardrails 用规则 + 模型程序化过滤输出，与宪法链（LLM 审视）互补。
覆盖：PII 泄露 / Toxicity / Topic Restriction / Output Length / Schema / URL 安全等。

真实使用：
    pip install guardrails-ai
    from guardrails import Guard
    from guardrails.validators import DetectPII, ProfanityFree, ValidLength, RestrictToTopic

本文件对 guardrails 做 try/except：缺依赖时回退到零依赖的等价校验器
（正则 PII / 脏词表 / 长度 / 主题白名单），保证可运行且行为可复现。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

try:
    from guardrails import Guard  # type: ignore
    from guardrails.validators import (  # type: ignore
        DetectPII,
        ProfanityFree,
        RestrictToTopic,
        ValidLength,
    )

    _HAS_GUARDRAILS = True
except ImportError:
    _HAS_GUARDRAILS = False
    print("[提示] 未安装 guardrails-ai，使用零依赖等价校验器。安装：pip install guardrails-ai\n")


@dataclass
class Violation:
    id: str
    severity: str  # critical / high / medium
    detail: str


@dataclass
class GuardResult:
    passed: bool
    violations: list[Violation] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 零依赖等价校验器
# ---------------------------------------------------------------------------
_PII_PATTERNS = {
    "PHONE_NUMBER": re.compile(r"\b1[3-9]\d{9}\b"),
    "EMAIL_ADDRESS": re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    "ID_CARD": re.compile(r"\b\d{17}[\dXx]\b"),
    "BANK_CARD": re.compile(r"\b\d{16,19}\b"),
}
_PROFANITY = {"傻", "滚", "垃圾", "idiot", "stupid", "shit"}
VALID_TOPICS = ["产品咨询", "订单查询", "投诉处理"]
_TOPIC_HINTS = {"产品咨询": ["产品", "推荐", "功效", "成分"],
                "订单查询": ["订单", "物流", "发货", "快递"],
                "投诉处理": ["投诉", "问题", "不满", "退"]}


def _detect_pii(text: str, entities: list[str]) -> list[Violation]:
    out = []
    for ent in entities:
        pat = _PII_PATTERNS.get(ent)
        if pat and pat.search(text):
            out.append(Violation("pii_detected", "critical", f"输出含 {ent}"))
    return out


def _profanity_free(text: str) -> list[Violation]:
    hits = [w for w in _PROFANITY if w in text.lower()]
    return [Violation("toxicity", "critical", f"含不当词: {hits}")] if hits else []


def _valid_length(text: str, lo: int, hi: int) -> list[Violation]:
    if not (lo <= len(text) <= hi):
        return [Violation("length", "medium", f"长度 {len(text)} 不在 [{lo},{hi}]")]
    return []


def _restrict_topic(text: str, topics: list[str]) -> list[Violation]:
    if any(any(h in text for h in _TOPIC_HINTS.get(t, [])) for t in topics):
        return []
    return [Violation("off_topic", "high", f"输出偏离允许主题 {topics}")]


def validate(response: str) -> GuardResult:
    """程序化输出过滤。真实环境用 guardrails Guard().use(...).validate()。"""
    if _HAS_GUARDRAILS:
        guard = Guard().use(
            DetectPII(pii_entities=["PHONE_NUMBER", "EMAIL_ADDRESS", "ID_CARD"]),
            ProfanityFree(),
            ValidLength(min=10, max=2000),
            RestrictToTopic(valid_topics=VALID_TOPICS),
        )
        outcome = guard.validate(response)
        if getattr(outcome, "validation_passed", True):
            return GuardResult(True)
        return GuardResult(False, [Violation("guardrails", "high", "见 failed_validations")])

    violations: list[Violation] = []
    violations += _detect_pii(response, ["PHONE_NUMBER", "EMAIL_ADDRESS", "ID_CARD", "BANK_CARD"])
    violations += _profanity_free(response)
    violations += _valid_length(response, 10, 2000)
    violations += _restrict_topic(response, VALID_TOPICS)
    return GuardResult(not violations, violations)


def main() -> None:
    print("=" * 60)
    print("Guardrails AI 输出过滤演示")
    print("=" * 60)
    samples = [
        "为您推荐这款适合油皮的洁面产品，成分温和。",
        "客户张伟的电话是 13800138000，您可以直接联系。",  # PII 泄露
        "你这个问题真是垃圾，我不想回答。",  # toxicity
        "今天天气不错，我们聊聊政治吧。",  # off-topic
    ]
    for s in samples:
        r = validate(s)
        if r.passed:
            print(f"  [PASS ] {s}")
        else:
            vs = "; ".join(f"{v.id}({v.severity})" for v in r.violations)
            print(f"  [BLOCK] {s}\n          → {vs}")


if __name__ == "__main__":
    main()
