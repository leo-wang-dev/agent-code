"""语义切块阈值调优脚本（离线可运行）。

语义切块的关键细节（大部分教程不讲）：**相似度阈值怎么定**。阈值太高 → 到处切、chunk
太碎；太低 → 几乎不切、退化成整篇。本脚本扫一遍阈值，打印每个阈值下的 chunk 数、平均
长度、边界处的相似度，帮你挑出「语义跳变点」对应的拐点。

    python3 13_chunking/semantic_chunking_tuning.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _common import SAMPLE_HANDBOOK, embed_similarity, print_table  # noqa: E402


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"[。！？]+", text) if s.strip()]


def adjacent_similarities(sentences: list[str]) -> list[float]:
    return [embed_similarity(sentences[i - 1], sentences[i]) for i in range(1, len(sentences))]


def semantic_chunk(sentences: list[str], sims: list[float], threshold: float) -> list[str]:
    chunks: list[str] = []
    current = [sentences[0]]
    for i in range(1, len(sentences)):
        if sims[i - 1] < threshold:
            chunks.append("。".join(current) + "。")
            current = [sentences[i]]
        else:
            current.append(sentences[i])
    if current:
        chunks.append("。".join(current) + "。")
    return chunks


def main() -> None:
    sentences = split_sentences(SAMPLE_HANDBOOK)
    sims = adjacent_similarities(sentences)

    print("=" * 72)
    print("相邻句相似度（切点候选）")
    print("=" * 72)
    rows = []
    for i, sim in enumerate(sims):
        rows.append([f"{i}->{i+1}", f"{sim:.3f}", sentences[i][:16], sentences[i + 1][:16]])
    print_table(["边界", "相似度", "左句", "右句"], rows)

    print("\n" + "=" * 72)
    print("阈值调优扫描")
    print("=" * 72)
    scan_rows = []
    for threshold in [0.05, 0.10, 0.12, 0.15, 0.20, 0.30]:
        chunks = semantic_chunk(sentences, sims, threshold)
        avg = sum(len(c) for c in chunks) / max(1, len(chunks))
        cuts = sum(1 for s in sims if s < threshold)
        scan_rows.append([f"{threshold:.2f}", len(chunks), f"{avg:.0f}", cuts])
    print_table(["阈值", "chunk 数", "平均字数", "切点数"], scan_rows)

    # 推荐阈值：取相似度分布的一个自然拐点（这里用中位数附近）
    ordered = sorted(sims)
    median = ordered[len(ordered) // 2]
    print(f"\n相似度中位数 ≈ {median:.3f}；建议阈值取略低于跨语义段边界的相似度。")
    print("经验法则：先看『边界相似度』表里明显偏低的几个点（那就是真语义跳变），")
    print("把阈值卡在它们之上、段内相似度之下，chunk 数会在此处出现平台（拐点）。")


if __name__ == "__main__":
    main()
