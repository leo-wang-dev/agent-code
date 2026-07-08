"""手写 Agent · plus 版：在基础版上加「流式输出」与「简易持久化」。

对应文章第 10 篇末尾承诺：两文件基础版 + 带流式和持久化的 plus 版。

在 agent.py（基础版）之上补两件生产常见能力，仍不依赖任何 Agent 框架：
- 流式输出：把最终答案按 token 逐个 yield，模拟 SSE 逐字下发。
- 简易持久化：每轮对话与 trace 落到 JSON 文件，请求断了任务可恢复。

离线可跑，无需 API key。默认写到系统临时目录，跑完自动清理。
"""

from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

from agent import HandwrittenAgent
from tools import build_registry


@dataclass
class PersistentStreamingAgent(HandwrittenAgent):
    """基础 Agent + 持久化 + 流式。"""

    state_path: Path = field(default_factory=lambda: Path(tempfile.gettempdir()) / "handwritten_agent_state.json")

    def run(self, user_input: str) -> dict[str, Any]:
        state = self._load()
        state.setdefault("turns", []).append({"role": "user", "content": user_input})
        result = super().run(user_input)
        answer = result.get("answer") or f"[{result.get('reason', 'stopped')}]"
        state["turns"].append({"role": "assistant", "content": answer})
        state.setdefault("traces", []).append(result.get("trace", []))
        self._save(state)  # 简易持久化
        return result

    def stream_answer(self, user_input: str) -> Iterator[str]:
        """流式输出：逐 token 下发最终答案，模拟 SSE。"""
        result = self.run(user_input)
        answer = result.get("answer") or f"[{result.get('reason', 'stopped')}]"
        for token in str(answer).split():
            yield token + " "

    def history(self) -> list[dict[str, str]]:
        return self._load().get("turns", [])

    def _load(self) -> dict[str, Any]:
        if not self.state_path.exists():
            return {}
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def _save(self, state: dict[str, Any]) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        agent = PersistentStreamingAgent(
            registry=build_registry(),
            state_path=Path(tmp) / "state.json",
        )

        print("=== 流式输出（逐 token 下发）===")
        print("回答: ", end="", flush=True)
        for chunk in agent.stream_answer("请计算 (3+5)*2"):
            print(chunk, end="", flush=True)
        print()

        # 第二轮，验证持久化跨轮累积。
        list(agent.stream_answer("What is the weather in Dubai?"))

        print("\n=== 持久化状态（可用于断点恢复）===")
        for turn in agent.history():
            print(f"  {turn['role']}: {turn['content']}")
        print(f"\n状态文件: {agent.state_path.name}（已落盘 {len(agent.history())} 条对话）")


if __name__ == "__main__":
    main()
