from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from agent_examples.rag import Document


# 采购目录与知识库数据，供第 11-48 篇的连续项目使用。
#
# 数据来源优先级：
#   1. 环境变量 PRACTICE_DATA_DIR 指向的目录（可选，放你自己的 catalog.json / knowledge/）
#   2. 本仓库内的 series_projects/_practice_data/（如果存在）
#   3. 下方内置的离线样本数据（默认，保证任何机器上都能离线跑通）
#
# 内置样本足以演示所有章节的检索 / 记忆 / 编排逻辑；想用更大的真实数据集，
# 设置 PRACTICE_DATA_DIR 即可，无需改代码。

_REPO_DATA_DIR = Path(__file__).resolve().parent / "_practice_data"


def _external_data_dir() -> Path | None:
    env = os.environ.get("PRACTICE_DATA_DIR")
    if env and Path(env).is_dir():
        return Path(env)
    if _REPO_DATA_DIR.is_dir():
        return _REPO_DATA_DIR
    return None


# ── 内置离线样本 ─────────────────────────────────────────────────────────────

_BUILTIN_CATALOG: list[dict[str, Any]] = [
    {"id": "P001", "name": "304 Stainless Steel Sheet 1mm", "category": "steel",
     "moq": 5, "lead_time_days": 7, "price_range": {"min": 2800, "max": 3200, "unit": "CNY/ton"},
     "tags": ["stainless", "sheet", "304", "stainless steel"]},
    {"id": "P002", "name": "316L Stainless Steel Sheet 2mm", "category": "steel",
     "moq": 5, "lead_time_days": 10, "price_range": {"min": 4500, "max": 5200, "unit": "CNY/ton"},
     "tags": ["stainless", "sheet", "316L", "stainless steel"]},
    {"id": "P003", "name": "304 Stainless Steel Coil 0.5mm", "category": "steel",
     "moq": 10, "lead_time_days": 14, "price_range": {"min": 3000, "max": 3500, "unit": "CNY/ton"},
     "tags": ["stainless", "coil", "304", "stainless steel"]},
    {"id": "P004", "name": "Q235 Carbon Steel Plate 10mm", "category": "steel",
     "moq": 20, "lead_time_days": 5, "price_range": {"min": 2200, "max": 2600, "unit": "CNY/ton"},
     "tags": ["carbon steel", "plate", "Q235", "steel"]},
    {"id": "P005", "name": "Q345 Carbon Steel Sheet 6mm", "category": "steel",
     "moq": 20, "lead_time_days": 5, "price_range": {"min": 2400, "max": 2800, "unit": "CNY/ton"},
     "tags": ["carbon steel", "sheet", "Q345", "steel"]},
    {"id": "P006", "name": "6061 Aluminum Plate 5mm", "category": "aluminum",
     "moq": 8, "lead_time_days": 9, "price_range": {"min": 18000, "max": 21000, "unit": "CNY/ton"},
     "tags": ["aluminum", "plate", "6061", "alloy"]},
    {"id": "P007", "name": "T2 Copper Sheet 3mm", "category": "copper",
     "moq": 3, "lead_time_days": 12, "price_range": {"min": 62000, "max": 68000, "unit": "CNY/ton"},
     "tags": ["copper", "sheet", "T2", "conductive"]},
    {"id": "P008", "name": "430 Stainless Steel Strip 0.8mm", "category": "steel",
     "moq": 10, "lead_time_days": 8, "price_range": {"min": 2600, "max": 3000, "unit": "CNY/ton"},
     "tags": ["stainless", "strip", "430", "magnetic"]},
]

_BUILTIN_KNOWLEDGE: dict[str, str] = {
    "quality_standards": (
        "Quality Standards Reference for Industrial Sourcing\n\n"
        "ISO 9001: Quality Management Systems — the most widely recognized quality "
        "standard worldwide; requires documented processes and annual surveillance "
        "audits; current version ISO 9001:2015.\n"
        "ISO 14001: Environmental Management Systems — covers waste management, "
        "emissions control and resource efficiency; increasingly required by "
        "multinational buyers.\n"
        "IATF 16949: the automotive quality standard, mandatory for suppliers into "
        "automotive supply chains.\n"
    ),
    "sourcing_guide": (
        "Sourcing Guide: Industrial Materials Procurement\n\n"
        "Chapter 1 Supplier Evaluation — evaluate suppliers on quality certifications "
        "(ISO9001/ISO14001/IATF16949), production capacity, financial stability, "
        "location and Minimum Order Quantity (MOQ).\n"
        "Chapter 2 Pricing — common terms: FOB (seller pays until goods are on the "
        "ship), CIF (seller pays shipping and insurance). Leave 30-day cool-off "
        "before re-optimizing pricing to avoid over-optimization.\n"
    ),
    "steel_knowledge": (
        "Steel Knowledge Base: Grades, Standards, and Applications\n\n"
        "Stainless: 201 SS budget/decorative; 304 SS most common, food-safe, "
        "excellent corrosion resistance; 316L SS premium with molybdenum, superior "
        "in marine/chemical environments; 430 SS ferritic, magnetic, lower cost.\n"
        "Carbon: Q235B general structural, weldable; Q345B higher strength for "
        "bridges and heavy machinery; SPCC cold-rolled for automotive panels; "
        "S45C medium carbon, heat-treatable for shafts and gears.\n"
    ),
}


def load_json_file(path: Path) -> Any:
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def load_practice_catalog(limit: int = 8) -> list[dict[str, Any]]:
    """Load the sourcing catalog. Uses an external data dir if configured,
    otherwise the built-in offline sample."""

    data_dir = _external_data_dir()
    if data_dir:
        path = data_dir / "catalog.json"
        if not path.exists():
            path = data_dir / "llamaindex-learn" / "data" / "catalog.json"
        if path.exists():
            return load_json_file(path)[:limit]
    return [dict(item) for item in _BUILTIN_CATALOG[:limit]]


def load_practice_knowledge_documents() -> list[Document]:
    """Turn sourcing knowledge into RAG documents. Uses an external data dir
    if configured, otherwise the built-in offline sample.

    Intentionally lightweight: the project stays runnable without LlamaIndex,
    using the same kind of source material as the practice project.
    """

    docs: list[Document] = []
    data_dir = _external_data_dir()
    if data_dir:
        knowledge_dir = data_dir / "knowledge"
        if not knowledge_dir.exists():
            knowledge_dir = data_dir / "llamaindex-learn" / "data" / "knowledge"
        if knowledge_dir.exists():
            for path in sorted(knowledge_dir.glob("*.txt")):
                docs.append(
                    Document(
                        id=f"practice_{path.stem}",
                        text=path.read_text(encoding="utf-8"),
                        metadata={"category": "sourcing", "title": path.stem, "source": path.name},
                    )
                )
            if docs:
                return docs

    for name, text in _BUILTIN_KNOWLEDGE.items():
        docs.append(
            Document(
                id=f"practice_{name}",
                text=text,
                metadata={"category": "sourcing", "title": name, "source": "builtin"},
            )
        )
    return docs


def catalog_summary(limit: int = 5) -> list[dict[str, Any]]:
    return [
        {
            "id": item["id"],
            "name": item["name"],
            "category": item.get("category"),
            "moq": item.get("moq"),
            "lead_time_days": item.get("lead_time_days"),
            "price_range": item.get("price_range"),
        }
        for item in load_practice_catalog(limit)
    ]
