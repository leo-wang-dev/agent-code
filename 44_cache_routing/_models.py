"""离线 mock 模型层 —— 供本章的缓存/路由 demo 使用，无需任何 API Key。

- `local_embed`: 确定性本地 embedding（字符 n-gram 哈希袋 + L2 归一化）。
  生产替换为 SentenceTransformer("bge-large-zh") 等真实 embedding 模型。
- `MockModel`: 带成本/延迟属性的假模型，complete() 返回确定性文本。
"""

from __future__ import annotations

import hashlib
import math
import re
import time
from dataclasses import dataclass

_DIM = 256


def local_embed(text: str, term_weight: float = 5.0) -> list[float]:
    """确定性本地 embedding：关键词 term 重加权 + 字符 2-gram 哈希袋，L2 归一化。

    关键词（英文缩写/术语，如 RAG）给更高权重，这样"什么是 RAG"和"请解释一下 RAG"
    这类换说法能被判为相似——用离线手段近似"语义"命中。真实语义仍需换真 embedding：
        model = SentenceTransformer("bge-large-zh")
        return model.encode(text).tolist()
    """
    vec = [0.0] * _DIM
    lowered = text.lower()

    # 1) 领域关键词（连续 ASCII 字母，如 rag/api），高权重
    for term in re.findall(r"[a-z]{2,}", lowered):
        h = int(hashlib.md5(("T:" + term).encode()).hexdigest(), 16)
        vec[h % _DIM] += term_weight

    # 2) 字符 2-gram 袋（捕捉表层相似），基础权重
    norm = re.sub(r"\s+", "", lowered)
    grams = [norm[i:i + 2] for i in range(max(1, len(norm) - 1))] or [norm]
    for g in grams:
        h = int(hashlib.md5(g.encode()).hexdigest(), 16)
        vec[h % _DIM] += 1.0

    length = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / length for v in vec]


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


@dataclass
class MockModel:
    name: str
    input_price: float   # USD / 1M
    output_price: float  # USD / 1M
    ttft_ms: int         # 首字延迟中位数

    def complete(self, prompt: str, max_tokens: int = 256) -> dict:
        # 模拟推理延迟（缩放到毫秒级，方便 demo 快速跑完）
        time.sleep(self.ttft_ms / 100000)
        text = f"[{self.name}] 针对「{prompt[:40]}」的回答。"
        in_tok = max(1, len(prompt) // 3)
        out_tok = min(max_tokens, 60)
        cost = in_tok / 1e6 * self.input_price + out_tok / 1e6 * self.output_price
        return {"model": self.name, "text": text, "cost_usd": cost, "ttft_ms": self.ttft_ms}


# 模型梯队（对齐文章第 44 篇成本梯队表）
TINY = MockModel("gemini-flash", 0.075, 0.30, ttft_ms=300)
MINI = MockModel("gpt-4o-mini", 0.15, 0.60, ttft_ms=400)
MID = MockModel("claude-3-5-haiku", 0.80, 4.0, ttft_ms=500)
TOP = MockModel("gpt-4o", 2.50, 10.0, ttft_ms=900)
