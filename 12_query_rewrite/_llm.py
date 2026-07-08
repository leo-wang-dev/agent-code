"""可选 LLM 封装：有 OPENAI_API_KEY 且装了 openai 时走真模型，否则走确定性离线桩。

离线桩复用 ``agent_examples.rag`` 里已经打磨过的规则式改写/HyDE/多问法，保证无 key
也能跑出稳定、可复现的结果。导入本模块不发起任何网络请求。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent_examples.rag import hyde_answer, multi_queries, query_rewrite  # noqa: E402


def _online_generate(prompt: str) -> str | None:
    if not os.getenv("OPENAI_API_KEY"):
        return None
    try:
        from openai import OpenAI

        client = OpenAI()
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        return resp.choices[0].message.content
    except Exception as exc:  # pragma: no cover - optional/online path
        print(f"[llm] 在线模型不可用，回退离线桩：{exc}")
        return None


def rewrite(user_query: str) -> str:
    """口语→书面 + 第一人称→第三人称。在线优先，离线用规则式。"""

    online = _online_generate(
        "请将下面的用户问题改写成更接近企业文档语言的版本，口语换书面、第一人称换第三人称，"
        f"只输出一句话：\n{user_query}"
    )
    return online.strip() if online else query_rewrite(user_query)


def hyde(user_query: str) -> str:
    """HyDE：生成一段假设性答案用于检索。"""

    online = _online_generate(
        f"请给下面的问题写一段 2-3 句的假设性回答，即使不确定也按合理方式编写：\n{user_query}"
    )
    return online.strip() if online else hyde_answer(user_query)


def paraphrases(user_query: str, n: int = 4) -> list[str]:
    """Multi-Query：生成 n 种不同问法（含原问题）。"""

    online = _online_generate(
        f"请把下面的问题改写成 {n} 种不同表达，输出 JSON 数组：\n{user_query}"
    )
    if online:
        import json

        try:
            arr = json.loads(online)
            if isinstance(arr, list):
                return list(dict.fromkeys([user_query, *[str(x) for x in arr]]))
        except Exception:
            pass
    return multi_queries(user_query)
