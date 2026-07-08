"""LLMLingua 完整集成示例 —— 真装了就用真的，没装则用等价的离线降级实现。

对应文章第 43 篇 二、Prompt 压缩 —— LLMLingua 系列。

设计要点（都来自文章"工程实现注意点"）：
- 只有输入 > 阈值(默认 5000 token 处对应约 20000 字)才压缩，太短压缩反而亏；
- force_tokens 强制保留关键 token；
- 压缩结果可缓存（System Prompt 这种每次一样的内容压一次即可）。

离线可运行：`python3 llmlingua_integration.py`
缺 llmlingua 时打印安装指引，但仍用离线降级实现跑完 demo（退出码 0）。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _tokens import estimate_tokens  # noqa: E402

try:
    from llmlingua import PromptCompressor  # type: ignore

    _HAS_LLMLINGUA = True
except Exception:  # pragma: no cover - offline / not installed
    PromptCompressor = None  # type: ignore
    _HAS_LLMLINGUA = False


# 低信息量的"客套"词/停用词——真 LLMLingua 用小模型算重要性，这里用词表近似。
_LOW_VALUE = {
    "please", "actually", "you", "know", "very", "really", "just", "kind",
    "of", "sort", "the", "a", "an", "that", "to", "make", "sure",
    "请", "务必", "一定", "的", "了", "非常", "仔细地", "认真地", "尽量",
}


def _offline_compress(prompt: str, rate: float, force_tokens: list[str]) -> str:
    """离线降级压缩：按词过滤低信息量 token，强制保留 force_tokens。

    生产替换：装 llmlingua 后走真实的小模型重要性打分（见 compress 分支）。
    """
    keep_ratio = max(0.1, min(1.0, rate))
    # 按标点/空白切成词，保留原分隔以便重组可读。
    tokens = re.findall(r"\w+|[^\w\s]|\s+", prompt)
    words = [t for t in tokens if t.strip() and not re.match(r"[^\w\s]", t)]
    target = max(1, int(len(words) * keep_ratio))

    kept: list[str] = []
    for tok in tokens:
        w = tok.strip().lower()
        if not w or re.match(r"[^\w\s]", tok):
            continue
        force = any(f.lower() in w for f in force_tokens)
        low = w in _LOW_VALUE
        if force or (not low and len(kept) < target):
            kept.append(tok.strip())
    return " ".join(kept)


class LLMLinguaCompressor:
    """统一入口：接口对齐真实 PromptCompressor，缺依赖时透明降级。"""

    def __init__(self, model_name: str = "microsoft/llmlingua-2-xlm-roberta-large-meetingbank"):
        self.model_name = model_name
        self._cache: dict[str, dict] = {}
        self._real = None
        if _HAS_LLMLINGUA:
            self._real = PromptCompressor(model_name=model_name)  # type: ignore

    def compress(
        self,
        prompt: str,
        rate: float = 0.5,
        force_tokens: list[str] | None = None,
        min_tokens: int = 5000,
        use_cache: bool = True,
    ) -> dict:
        force_tokens = force_tokens or []
        original_tokens = estimate_tokens(prompt)

        # 注意 2：太短不划算——直接返回原文。
        if original_tokens < min_tokens:
            return {
                "compressed_prompt": prompt,
                "original_tokens": original_tokens,
                "compressed_tokens": original_tokens,
                "saved_ratio": 0.0,
                "skipped": True,
                "reason": f"input {original_tokens} < min_tokens {min_tokens}",
            }

        # 注意 3：结果缓存——同一段 System Prompt 压一次即可。
        cache_key = f"{rate}:{','.join(force_tokens)}:{hash(prompt)}"
        if use_cache and cache_key in self._cache:
            return {**self._cache[cache_key], "cached": True}

        if self._real is not None:
            out = self._real.compress_prompt(prompt, rate=rate, force_tokens=force_tokens)
            compressed = out["compressed_prompt"]
        else:
            compressed = _offline_compress(prompt, rate, force_tokens)

        compressed_tokens = estimate_tokens(compressed)
        result = {
            "compressed_prompt": compressed,
            "original_tokens": original_tokens,
            "compressed_tokens": compressed_tokens,
            "saved_ratio": round(1 - compressed_tokens / max(1, original_tokens), 3),
            "skipped": False,
            "engine": "llmlingua" if self._real else "offline-fallback",
        }
        if use_cache:
            self._cache[cache_key] = result
        return result


def _demo() -> None:
    if not _HAS_LLMLINGUA:
        print("[提示] 未安装 llmlingua，使用离线降级压缩演示。")
        print("       生产安装：pip install llmlingua  （并需要可下载的小模型权重）")
        print()

    compressor = LLMLinguaCompressor()

    long_prompt = (
        "You are a helpful customer service assistant. Please respond to the user "
        "politely. Make sure to actually understand the user's question carefully "
        "before answering. You should provide accurate information based on company "
        "policies. The customer policy states that refunds are allowed within 30 days. "
    ) * 110  # 放大到超过 min_tokens 阈值(默认 5000)

    result = compressor.compress(
        long_prompt,
        rate=0.5,
        force_tokens=["customer", "policy", "refund"],
    )
    print(f"engine          : {result.get('engine', 'skipped')}")
    print(f"original tokens : {result['original_tokens']}")
    print(f"compressed      : {result['compressed_tokens']}")
    print(f"saved ratio     : {result['saved_ratio']:.1%}")

    # 太短的 prompt 会被跳过（不划算）
    short = compressor.compress("你是客服助手，请礼貌回答。", rate=0.5)
    print(f"\n短 prompt 是否跳过压缩: {short['skipped']}  ({short.get('reason', '')})")


if __name__ == "__main__":
    _demo()
