"""评测集 schema 模板与校验器。

对应文章第一节"评测集的写作规范"。工业级评测 case 远超 "input + expected output"
两个字段——每个 case 都带完整元数据（来源、报告人、预期行为、指标阈值、复核日期），
出问题时能查"这个 case 怎么来的、应该怎么改"。

配套 `cases/case_001.yaml` 是一份可直接复制的模板。本文件提供：
  - CASE_SCHEMA：字段定义与必填项
  - validate_case()：零依赖校验（缺 pyyaml 时用内置样例 dict）
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# schema 定义
# ---------------------------------------------------------------------------
REQUIRED_TOP_FIELDS = [
    "id",
    "category",
    "difficulty",
    "source",       # 这个 case 怎么来的
    "input",
    "expected_behavior",
    "evaluation_metrics",
]

REQUIRED_INPUT_FIELDS = ["user_query"]
REQUIRED_BEHAVIOR_FIELDS = ["intent"]
VALID_DIFFICULTY = {"easy", "medium", "hard"}

# 与文章一致的样例（当没有 pyyaml 时作为校验对象）
SAMPLE_CASE = {
    "id": "case_001",
    "category": "退货政策",
    "difficulty": "medium",
    "source": "线上_2026_05_03_工单_T12345",
    "reporter": "客服张伟",
    "added_date": "2026-05-05",
    "input": {
        "user_query": "我上周买的产品想退，但发票丢了能退吗？",
        "user_context": {"vip_level": 1, "purchase_history": "..."},
    },
    "expected_behavior": {
        "intent": "退货咨询",
        "should_call_tools": ["query_order", "check_refund_policy"],
        "should_mention": ["无发票退货政策", "VIP 退货特权"],
        "should_not_mention": ["拒绝退款"],
        "tone": "礼貌、解决导向",
    },
    "evaluation_metrics": [
        {"faithfulness": 0.9},
        {"answer_relevancy": 0.85},
        {"llm_rubric": "回答必须明确告诉用户能否退、需要什么材料"},
    ],
    "notes": "历史 Bad Case：之前 AI 错误回答'无发票不能退'，实际 VIP 有'无发票申诉退货'特权",
    "last_validated": "2026-05-15",
}


@dataclass
class ValidationResult:
    case_id: str
    ok: bool
    errors: list[str] = field(default_factory=list)


def validate_case(case: dict) -> ValidationResult:
    errors: list[str] = []
    cid = case.get("id", "<无 id>")

    for f in REQUIRED_TOP_FIELDS:
        if f not in case:
            errors.append(f"缺少顶层字段：{f}")

    if case.get("difficulty") not in VALID_DIFFICULTY:
        errors.append(f"difficulty 必须是 {VALID_DIFFICULTY}，实际：{case.get('difficulty')}")

    inp = case.get("input", {})
    for f in REQUIRED_INPUT_FIELDS:
        if f not in inp:
            errors.append(f"input 缺少字段：{f}")

    beh = case.get("expected_behavior", {})
    for f in REQUIRED_BEHAVIOR_FIELDS:
        if f not in beh:
            errors.append(f"expected_behavior 缺少字段：{f}")

    if not case.get("evaluation_metrics"):
        errors.append("evaluation_metrics 不能为空")

    return ValidationResult(cid, not errors, errors)


def load_cases_from_dir(cases_dir: str) -> list[dict]:
    """从目录加载 yaml 用例；缺 pyyaml 时回退到内置样例。"""
    try:
        import yaml  # type: ignore
    except ImportError:
        print("[提示] 未安装 pyyaml，使用内置样例校验。生产安装：pip install pyyaml")
        return [SAMPLE_CASE]

    cases: list[dict] = []
    if not os.path.isdir(cases_dir):
        return [SAMPLE_CASE]
    for name in sorted(os.listdir(cases_dir)):
        if name.endswith((".yaml", ".yml")):
            with open(os.path.join(cases_dir, name), encoding="utf-8") as fh:
                doc = yaml.safe_load(fh)
                # 文件可能是单个 case 或 case 列表
                cases.extend(doc if isinstance(doc, list) else [doc])
    return cases or [SAMPLE_CASE]


def main() -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    cases = load_cases_from_dir(os.path.join(here, "cases"))
    print("=" * 56)
    print(f"评测集 schema 校验（共 {len(cases)} 条）")
    print("=" * 56)
    all_ok = True
    for case in cases:
        r = validate_case(case)
        print(f"\n[{'OK' if r.ok else 'ERROR'}] {r.case_id}")
        for e in r.errors:
            print(f"    · {e}")
        all_ok = all_ok and r.ok
    print("\n" + ("全部通过 ✅" if all_ok else "存在不合规用例 ❌"))


if __name__ == "__main__":
    main()
