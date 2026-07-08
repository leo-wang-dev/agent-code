"""bge-reranker / Cohere / Voyage 三家 Reranker 的统一接口适配器（离线可运行）。

工业级做法：把不同 Reranker 收敛到同一个 `Reranker.score(query, passages) -> list[float]`
接口，业务层不关心底层是哪家。中文场景 → bge-reranker，国际场景 → Cohere/Voyage。

真实 SDK（`cohere` / `voyageai` / `sentence-transformers`）缺失或无 key 时，自动回退到
**确定性离线打分**（复用 agent_examples 的 cross 代理），并打印安装指引。导入不发起网络请求。

    python3 14_rerank_hybrid/reranker_adapters.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent_examples.rag import query_rewrite  # noqa: E402
from agent_examples.text import ScoredText, tokenize  # noqa: E402


def _offline_score(query: str, passages: list[str]) -> list[float]:
    """确定性离线 cross 打分代理：query↔passage 词重叠 + 答案型句式加权。"""

    q = set(tokenize(query_rewrite(query)))
    scores = []
    for text in passages:
        toks = set(tokenize(text))
        overlap = len(q & toks) / max(1, len(q))
        bonus = 0.2 if any(m in text for m in ["享有", "支持", "申请", "额度", "必须"]) else 0.0
        scores.append(round(overlap + bonus, 4))
    return scores


class Reranker:
    """统一接口。子类实现 `_score_impl`；基类负责回退与归一。"""

    name = "base"

    def score(self, query: str, passages: list[str]) -> list[float]:
        try:
            return self._score_impl(query, passages)
        except Exception as exc:  # pragma: no cover - optional/online path
            print(f"[{self.name}] 不可用，回退离线打分：{exc}")
            return _offline_score(query, passages)

    def _score_impl(self, query: str, passages: list[str]) -> list[float]:
        raise NotImplementedError

    def rerank(self, query: str, candidates: list[ScoredText], top_n: int = 3) -> list[ScoredText]:
        scores = self.score(query, [c.text for c in candidates])
        paired = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
        return [ScoredText(c.text, s, c.metadata) for c, s in paired[:top_n]]


class BgeReranker(Reranker):
    """bge-reranker-v2（中文首选）。需要 sentence-transformers / FlagEmbedding。"""

    name = "bge-reranker"

    def _score_impl(self, query, passages):
        try:
            from FlagEmbedding import FlagReranker  # noqa: F401
        except Exception:
            print("[bge-reranker] 未安装，pip install FlagEmbedding；本次用离线打分。")
            return _offline_score(query, passages)
        model = FlagReranker("BAAI/bge-reranker-v2-m3")  # pragma: no cover
        return [float(s) for s in model.compute_score([[query, p] for p in passages])]


class CohereReranker(Reranker):
    """Cohere Rerank（国际场景）。需要 cohere + COHERE_API_KEY。"""

    name = "cohere-rerank"

    def _score_impl(self, query, passages):
        if not os.getenv("COHERE_API_KEY"):
            print("[cohere-rerank] 无 COHERE_API_KEY，用离线打分。")
            return _offline_score(query, passages)
        import cohere  # pragma: no cover

        client = cohere.Client(os.environ["COHERE_API_KEY"])
        resp = client.rerank(model="rerank-multilingual-v3.0", query=query, documents=passages)
        out = [0.0] * len(passages)
        for r in resp.results:
            out[r.index] = r.relevance_score
        return out


class VoyageReranker(Reranker):
    """Voyage Rerank（国际场景）。需要 voyageai + VOYAGE_API_KEY。"""

    name = "voyage-rerank"

    def _score_impl(self, query, passages):
        if not os.getenv("VOYAGE_API_KEY"):
            print("[voyage-rerank] 无 VOYAGE_API_KEY，用离线打分。")
            return _offline_score(query, passages)
        import voyageai  # pragma: no cover

        client = voyageai.Client()
        resp = client.rerank(query, passages, model="rerank-2")
        out = [0.0] * len(passages)
        for r in resp.results:
            out[r.index] = r.relevance_score
        return out


RERANKERS = {"bge": BgeReranker, "cohere": CohereReranker, "voyage": VoyageReranker}


def main() -> None:
    query = "我今年能休几天假"
    passages = [
        "入职满 1 年至 5 年的员工享有 5 个工作日带薪年假。",
        "差旅报销额度根据职级而定，普通员工 300 元/天。",
        "公司支持远程办公，员工需提前一天提交 WFH 申请。",
        "本机支持 5G 双模，典型续航 36 小时。",
    ]
    print("=" * 72)
    print("三家 Reranker 统一接口对照（同一 query / 同一候选集）")
    print("=" * 72)
    print(f"query：{query}\n")
    for key, cls in RERANKERS.items():
        reranker = cls()
        scores = reranker.score(query, passages)
        best = max(range(len(passages)), key=lambda i: scores[i])
        print(f"[{reranker.name}] 分数={[f'{s:.2f}' for s in scores]}  → top: {passages[best][:20]}")
    print("\n业务层只调用 Reranker.score(query, passages)，切换厂商 = 换一个子类，零改动。")


if __name__ == "__main__":
    main()
