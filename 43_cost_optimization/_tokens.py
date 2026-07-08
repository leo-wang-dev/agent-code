"""Token estimation helper shared across chapter 43 demos.

Prefers the real `tiktoken` tokenizer when installed; otherwise falls back to a
deterministic heuristic that is good enough for the cost-attribution demos in
this chapter (CJK ~= 1 token/char, ASCII words ~= 1 token / 4 chars).
"""

from __future__ import annotations

import re

try:  # optional dependency
    import tiktoken

    _ENC = tiktoken.get_encoding("cl100k_base")
except Exception:  # pragma: no cover - offline / not installed
    _ENC = None


def estimate_tokens(text: str) -> int:
    """Estimate the token count of *text*.

    Uses tiktoken if available, else a CJK-aware heuristic.
    """
    if not text:
        return 0
    if _ENC is not None:
        return len(_ENC.encode(text))
    # Heuristic: count CJK chars as 1 token each, the rest as ~4 chars/token.
    cjk = len(re.findall(r"[一-鿿]", text))
    non_cjk = len(re.sub(r"[一-鿿]", "", text))
    return cjk + max(1, non_cjk // 4)


# Public price table (USD per 1M tokens) mirroring the article's table.
PRICES = {
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "claude-3-5-sonnet": {"input": 3.00, "output": 15.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gemini-flash": {"input": 0.075, "output": 0.30},
}


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    price = PRICES.get(model, PRICES["gpt-4o"])
    return (
        input_tokens / 1_000_000 * price["input"]
        + output_tokens / 1_000_000 * price["output"]
    )
