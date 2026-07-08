"""18 章配套：异步抽取队列（fire-and-forget + 按层路由入库）。

对应文章第五节"异步事实抽取" + 第六节整体架构图后半部分：

  [用户消息] → 主流程（检索+生成+流式返回，用户感知延迟只到这里）
                    │ fire-and-forget
                    ↓
             抽取流程（异步）：LLM 抽取 → 按层路由：
               - Profile 字段     → 关系型表 UPSERT
               - Preference/Episodic → Operation Engine（向量层）
               - Working          → Session Store update
             失败重试 / 死信兜底（retry_dlq）+ 置信度低 → 暂存区（staging_area）

本文件把这几件事串成一条离线可跑的异步抽取管线：内存队列 + 后台 worker +
规则式抽取 + 按层路由。debounce / retry / staging 作为可组合零件在同目录另有独立文件。

离线可运行：`python3 18_layered_memory/async_extraction.py`
"""

from __future__ import annotations

import json
import queue
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from layered_schema import Layer, LayeredMemory, VectorMemory, WorkingItem  # noqa: E402
from staging_area import StagingArea  # noqa: E402


# 规则式抽取：一句话 → 若干 (layer, key, value, confidence)
_RULES = [
    ("张伟", (Layer.PROFILE, "name", "张伟", 0.95)),
    ("上海", (Layer.PROFILE, "location", "上海", 0.9)),
    ("产品经理", (Layer.PROFILE, "occupation", "产品经理", 0.9)),
    ("简洁", (Layer.PREFERENCE, "pref_style", "喜欢简洁、直接的回答", 0.8)),
    ("成本", (Layer.PREFERENCE, "pref_cost", "关注成本敏感度", 0.75)),
    ("咨询", (Layer.EPISODIC, "episodic_event", None, 0.7)),
    ("心情", (Layer.WORKING, "mood", None, 0.6)),
    ("急", (Layer.WORKING, "mood", "用户当下比较急", 0.6)),
]


def extract(utterance: str) -> list[tuple[Layer, str, str, float]]:
    facts = []
    for keyword, (layer, key, value, conf) in _RULES:
        if keyword in utterance:
            facts.append((layer, key, value or utterance, conf))
    return facts


@dataclass
class ExtractJob:
    user_id: str
    session_id: str
    conversation_id: str
    utterance: str


class AsyncExtractor:
    """fire-and-forget 抽取队列 + 后台 worker + 按层路由。"""

    def __init__(self, mem: LayeredMemory) -> None:
        self.mem = mem
        self.staging = StagingArea()
        self._q: "queue.Queue[str]" = queue.Queue()
        self.routed = {"profile": 0, "preference": 0, "episodic": 0, "working": 0, "staged": 0}

    # 主流程调用：立即返回，不等抽取
    def fire(self, job: ExtractJob) -> None:
        self._q.put(json.dumps(job.__dict__, ensure_ascii=False))

    def _route(self, job: ExtractJob) -> None:
        for layer, key, value, conf in extract(job.utterance):
            # 低置信 → 暂存区（Profile/Preference/Episodic 才需要，Working 临时不入正式库）
            if layer != Layer.WORKING and conf < 0.7:
                self.staging.ingest(f"{job.user_id}:{key}", value, conf)
                self.routed["staged"] += 1
                continue

            if layer == Layer.PROFILE:
                self.mem.upsert_profile(job.user_id, **{key: value})
                self.routed["profile"] += 1
            elif layer == Layer.PREFERENCE:
                self.mem.add_vector(VectorMemory(f"{job.user_id}:{key}", job.user_id, Layer.PREFERENCE, value, confidence=conf))
                self.routed["preference"] += 1
            elif layer == Layer.EPISODIC:
                now = time.time()
                self.mem.add_vector(VectorMemory(f"{job.user_id}:epi:{int(now*1000)}", job.user_id,
                                                 Layer.EPISODIC, value, confidence=conf,
                                                 expires_at=now + 90 * 86400))
                self.routed["episodic"] += 1
            elif layer == Layer.WORKING:
                self.mem.add_working(WorkingItem(job.session_id, value))
                self.routed["working"] += 1

    def drain(self, max_jobs: int = 100) -> int:
        processed = 0
        while processed < max_jobs:
            try:
                payload = self._q.get_nowait()
            except queue.Empty:
                break
            self._route(ExtractJob(**json.loads(payload)))
            processed += 1
        return processed

    def run_worker(self, idle_timeout: float = 0.5) -> threading.Thread:
        def loop() -> None:
            last = time.time()
            while time.time() - last < idle_timeout:
                if self.drain(1):
                    last = time.time()
                else:
                    time.sleep(0.02)

        t = threading.Thread(target=loop, daemon=True)
        t.start()
        return t


def _demo() -> None:
    mem = LayeredMemory()
    ext = AsyncExtractor(mem)

    conversation = [
        "我叫张伟，家在上海。",
        "我是产品经理，喜欢简洁的回答。",
        "我比较关注成本。",
        "我今天心情有点急，赶 deadline。",
        "上周我咨询过定价方案。",
        "顺便提一句可能不太确定的爱好（低置信）成本。",
    ]
    for i, u in enumerate(conversation):
        ext.fire(ExtractJob("u1", "s1", f"c{i}", u))
    print("6 条消息已 fire（主流程无需等待，已可返回回答）。\n")

    processed = ext.drain()
    print(f"后台 worker 处理 {processed} 个任务，按层路由统计：{ext.routed}")

    print("\n入库结果：")
    print("  Profile   :", mem.get_profile("u1").as_fields())
    print("  Preference:", [m.text for m in mem.vectors("u1", Layer.PREFERENCE)])
    print("  Episodic  :", [m.text for m in mem.vectors("u1", Layer.EPISODIC)])
    print("  Working   :", [w.text for w in mem.get_working("s1")])
    print("  暂存区    :", list(ext.staging.staging.keys()))


if __name__ == "__main__":
    _demo()
