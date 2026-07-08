"""实体抽取 + 关系抽取 Prompt 模板（离线可运行）。

GraphRAG 的第一步：把非结构化文本变成三元组 `(主语实体, 关系, 宾语实体)`。这里给出
工业级的抽取 Prompt 模板（预定义关系白名单 + JSON 输出），以及一个**确定性离线抽取器**
（无 LLM 时用规则式，输出同样的三元组结构）。

    python3 15_graphrag/extraction_prompts.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _graph import RELATION_TYPES, SAMPLE_SENTENCES, extract_triples  # noqa: E402


ENTITY_EXTRACTION_PROMPT = """\
请从下面这段文本中抽取所有实体，并标注类型（人物/公司/金额/时间/地点等）。

文本：{chunk_text}

输出格式（JSON）：
{{
  "entities": [
    {{"name": "...", "type": "..."}},
    ...
  ]
}}"""

RELATION_EXTRACTION_PROMPT = """\
请从下面这段文本中抽取实体及其关系，输出为三元组列表。

文本：{chunk_text}

预定义的关系类型（只能用这些）：
{relation_whitelist}

输出格式（JSON）：
{{
  "triples": [
    {{"subject": "...", "relation": "...", "object": "..."}},
    ...
  ]
}}"""


def render_relation_prompt(chunk_text: str) -> str:
    whitelist = "\n".join(f"- {en}（{zh}）" for zh, en in RELATION_TYPES.items())
    return RELATION_EXTRACTION_PROMPT.format(chunk_text=chunk_text, relation_whitelist=whitelist)


def extract(chunk_text: str) -> dict:
    """在线优先 / 离线规则式兜底，返回 {"triples": [...]}。"""

    if os.getenv("OPENAI_API_KEY"):
        try:
            from openai import OpenAI

            client = OpenAI()
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": render_relation_prompt(chunk_text)}],
                response_format={"type": "json_object"},
                temperature=0,
            )
            return json.loads(resp.choices[0].message.content)
        except Exception as exc:  # pragma: no cover
            print(f"[extract] 在线抽取不可用，回退离线规则式：{exc}")
    return {"triples": [t.as_dict() for t in extract_triples(chunk_text)]}


def main() -> None:
    print("=" * 72)
    print("关系抽取 Prompt 模板（发给 LLM 的实际内容）")
    print("=" * 72)
    print(render_relation_prompt("Y投资集团全资控股X资本管理公司。"))

    print("\n" + "=" * 72)
    print("离线规则式抽取结果（无 key 时的确定性等价）")
    print("=" * 72)
    for sentence in SAMPLE_SENTENCES:
        result = extract(sentence)
        print(f"\n文本：{sentence}")
        for t in result["triples"]:
            print(f"  ({t['subject']}, {t['relation']}, {t['object']})")


if __name__ == "__main__":
    main()
