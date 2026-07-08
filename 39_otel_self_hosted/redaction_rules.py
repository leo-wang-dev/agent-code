"""脱敏规则库 —— 生产 trace 落盘前必须脱敏。

对应文章第七节"隐私脱敏"。LLM trace 几乎必然含敏感信息（姓名/电话/身份证/
订单号/邮箱等），不脱敏直接落盘 = 合规事故。

三档策略（按敏感度分级）：
  极敏感（身份证/银行卡/健康信息） → 完全删除
  敏感（姓名/电话/地址/邮箱）       → 哈希或替换占位符
  一般（订单号/产品名）             → 保留或脱敏到类别级
  公开（产品信息/政策）             → 保留

本文件用零依赖正则实现规则级脱敏；PII 智能检测（presidio）做 try/except 保护。
生产在应用层先脱敏，再由 OTel Collector 的 attributes/redact 兜底二次处理。
"""
from __future__ import annotations

import hashlib
import re

# ---------------------------------------------------------------------------
# 规则表：(正则, 处理动作, 占位符/说明)
# ---------------------------------------------------------------------------
Tier = str  # "delete" | "hash" | "mask"

RULES: list[tuple[str, re.Pattern, Tier, str]] = [
    # 极敏感 → 完全删除（用 [REDACTED] 占位，不留原文）
    ("身份证", re.compile(r"\b\d{17}[\dXx]\b"), "delete", "[ID_CARD]"),
    ("银行卡", re.compile(r"\b\d{16,19}\b"), "delete", "[BANK_CARD]"),
    # 敏感 → 哈希 / 占位符
    ("邮箱", re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "hash", "[EMAIL:{h}]"),
    ("手机号", re.compile(r"\b1[3-9]\d{9}\b"), "mask", "[PHONE]"),
    # 一般 → 脱敏到类别级（保留可关联性但不泄露具体值）
    ("订单号", re.compile(r"\bORD\d{6,}\b"), "mask", "[ORDER_ID]"),
]

# 中文姓名（简单启发式：常见前缀"我叫/姓名是"后跟 2-3 个汉字）
NAME_HINT = re.compile(r"(我叫|姓名是|本人)([一-龥]{2,3})")


def _hash8(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:8]


def redact(text: str) -> str:
    """对一段文本应用全部脱敏规则。"""
    out = text
    # 姓名（带上下文提示）
    out = NAME_HINT.sub(lambda m: m.group(1) + "[PERSON]", out)
    for _name, pat, action, placeholder in RULES:
        if action == "hash":
            out = pat.sub(lambda m: placeholder.format(h=_hash8(m.group(0))), out)
        else:  # delete / mask 都替换成占位符（delete 表示不留原文）
            out = pat.sub(placeholder, out)
    return out


def redact_attributes(attrs: dict) -> dict:
    """对一个 span 的属性字典脱敏（gen_ai.prompt 等字段）。"""
    redacted = {}
    drop_keys = {"user.phone", "user.email_raw", "user.id_card"}  # 极敏感直接 drop
    for k, v in attrs.items():
        if k in drop_keys:
            continue
        redacted[k] = redact(v) if isinstance(v, str) else v
    return redacted


def try_presidio(text: str) -> str | None:
    """可选：用 presidio 做 PII 智能检测脱敏（缺依赖返回 None）。"""
    try:
        from presidio_analyzer import AnalyzerEngine  # type: ignore
        from presidio_anonymizer import AnonymizerEngine  # type: ignore
    except ImportError:
        return None
    analyzer = AnalyzerEngine()
    results = analyzer.analyze(text=text, language="zh")
    return AnonymizerEngine().anonymize(text=text, analyzer_results=results).text


def main() -> None:
    samples = [
        "我叫张伟，电话 13800138000，订单号 ORD20260530，邮箱 zhangwei@example.com",
        "客户身份证 11010119900307391X，银行卡 6222021234567890123 请核对",
        "查询一下产品退货政策，谢谢",  # 无敏感信息
    ]
    print("=" * 60)
    print("脱敏规则库演示")
    print("=" * 60)
    for s in samples:
        print(f"\n原文  : {s}")
        print(f"脱敏后: {redact(s)}")

    p = try_presidio(samples[0])
    print("\nPresidio 智能脱敏：", p if p else "未安装 presidio（pip install presidio-analyzer presidio-anonymizer）")

    print("\n铁律：生产 trace 永远脱敏后才落盘；要看完整 prompt 走带审计的敏感数据访问申请流程。")


if __name__ == "__main__":
    main()
