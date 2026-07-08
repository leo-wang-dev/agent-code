"""三框架横评的共享业务定义 —— 让对比公平：同一个采购助手、同一份数据。

对应文章第 32 篇「一、统一项目：一个企业级采购助手」。

六步业务流程（三个框架各实现一遍）：
  1. 意图分类（搜索 / 比价 / 闲聊）
  2. 需求收集（产品类型、规格、数量、预算）
  3. 三级级联搜索（自家目录 -> 供应商库 -> web 搜索）
  4. 结果重排和合并
  5. 生成报价对比报告（Artifact）
  6. 大额采购 -> 转经理审批（HITL）

数据优先复用系列采购目录；外部路径不可用时用内置副本，保证任何机器可跑。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# 内置采购目录副本（与系列 sourcing 项目同源，去掉外部路径依赖）。
_EMBEDDED_CATALOG: list[dict[str, Any]] = [
    {"id": "P001", "name": "钛合金板 TA2 1mm", "category": "titanium", "moq": 5, "lead_time_days": 7, "price": 3100},
    {"id": "P002", "name": "钛合金板 TC4 2mm", "category": "titanium", "moq": 5, "lead_time_days": 10, "price": 4800},
    {"id": "P003", "name": "钛合金棒 TA1", "category": "titanium", "moq": 10, "lead_time_days": 14, "price": 3300},
    {"id": "P004", "name": "304 不锈钢板 1mm", "category": "steel", "moq": 5, "lead_time_days": 7, "price": 3000},
    {"id": "P005", "name": "316L 不锈钢板 2mm", "category": "steel", "moq": 5, "lead_time_days": 10, "price": 4900},
]


def load_catalog(limit: int = 5) -> list[dict[str, Any]]:
    """优先复用系列采购目录，失败回退内置副本。"""

    try:
        from series_projects.practice_assets import catalog_summary

        rows = catalog_summary(limit=limit)
        if rows:
            return [
                {
                    "id": r["id"],
                    "name": r["name"],
                    "category": r.get("category"),
                    "moq": r.get("moq"),
                    "lead_time_days": r.get("lead_time_days"),
                    "price": (r.get("price_range") or {}).get("min", 3000),
                }
                for r in rows
            ]
    except Exception:
        pass
    return _EMBEDDED_CATALOG[:limit]


# 供应商库（第 2 级级联）与 web 结果（第 3 级级联）。
SUPPLIER_DB = [
    {"supplier": "京钛金属", "city": "北京", "sku": "TA2", "quote": 3080, "moq": 5},
    {"supplier": "华北钛业", "city": "北京", "sku": "TC4", "quote": 4750, "moq": 8},
    {"supplier": "首钢特材", "city": "北京", "sku": "TA1", "quote": 3260, "moq": 10},
]
WEB_RESULTS = [
    {"supplier": "西部超导(web)", "city": "西安", "sku": "TC4", "quote": 4680, "moq": 12},
]

LARGE_ORDER_THRESHOLD = 100_000  # 超过转经理审批（HITL）


def classify_intent(query: str) -> str:
    if any(k in query for k in ["比价", "报价", "对比"]):
        return "quote"
    if any(k in query for k in ["找", "搜索", "供应商"]):
        return "search"
    return "chitchat"


def collect_requirements(query: str) -> dict[str, Any]:
    """从查询里抽取需求（确定性 mock；真实项目由 LLM 完成）。"""

    qty = 40 if "40" in query else 20
    return {
        "product": "钛合金" if "钛" in query else "钢材",
        "city": "北京" if "北京" in query else "不限",
        "quantity_ton": qty,
        "budget": 200_000,
    }


def cascade_search(requirements: dict[str, Any]) -> dict[str, Any]:
    """三级级联：目录不足则查供应商库，再不足则 web；记录每级命中。"""

    trace: list[str] = []
    keyword = requirements["product"][:2]  # "钛合" / "钢材"
    category_key = "titanium" if "钛" in keyword else "steel"
    catalog = [
        c for c in load_catalog()
        if keyword in c["name"] or c.get("category") == category_key
    ]
    trace.append(f"L1 目录命中 {len(catalog)}")
    results = list(catalog)
    if len(results) < 3:
        supplier_hits = [s for s in SUPPLIER_DB if requirements["city"] in (s["city"], "不限")]
        trace.append(f"L2 供应商库命中 {len(supplier_hits)}")
        results += supplier_hits
    if len(results) < 5:
        trace.append(f"L3 web 命中 {len(WEB_RESULTS)}")
        results += WEB_RESULTS
    return {"results": results, "cascade_trace": trace}


def rerank_and_merge(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """按报价升序重排（越便宜越靠前），统一字段。"""

    normalized = []
    for r in results:
        normalized.append(
            {
                "supplier": r.get("supplier") or r.get("name", "自家目录"),
                "quote": r.get("quote") or r.get("price", 0),
                "moq": r.get("moq", 0),
            }
        )
    return sorted(normalized, key=lambda x: x["quote"])


def build_report(ranked: list[dict[str, Any]], requirements: dict[str, Any]) -> dict[str, Any]:
    """生成报价对比报告 Artifact，并判断是否触发 HITL 审批。"""

    top = ranked[:5]
    est_amount = (top[0]["quote"] if top else 0) * requirements["quantity_ton"]
    needs_approval = est_amount >= LARGE_ORDER_THRESHOLD
    lines = ["# 钛合金供应商报价对比", f"需求：{requirements}", ""]
    for i, row in enumerate(top, 1):
        lines.append(f"{i}. {row['supplier']}  报价 {row['quote']} 元/吨  MOQ {row['moq']}")
    lines.append(f"\n预估金额：{est_amount} 元 -> {'需经理审批(HITL)' if needs_approval else '可直接下单'}")
    return {
        "artifact": "\n".join(lines),
        "estimated_amount": est_amount,
        "needs_approval": needs_approval,
        "top_supplier": top[0]["supplier"] if top else None,
    }


@dataclass
class SourcingResult:
    """三个框架统一返回结构，方便 benchmark 对齐比较。"""

    framework: str
    intent: str
    requirements: dict[str, Any]
    ranked: list[dict[str, Any]]
    report: dict[str, Any]
    trace: list[str] = field(default_factory=list)
    used_real_lib: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "framework": self.framework,
            "intent": self.intent,
            "requirements": self.requirements,
            "top_supplier": self.report.get("top_supplier"),
            "estimated_amount": self.report.get("estimated_amount"),
            "needs_approval": self.report.get("needs_approval"),
            "trace": self.trace,
            "used_real_lib": self.used_real_lib,
        }


DEFAULT_QUERY = "帮我找北京 5 家可靠的钛合金供应商，比较他们的报价（40 吨）"
