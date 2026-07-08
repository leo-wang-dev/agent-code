"""产物：temperature 到底调的是什么（对应文章 §四 "temperature 调的是什么"）。

每生成一个 token，模型先对整个词表算一个概率分布，再从分布里采样。temperature 就是
softmax 之前对 logits 做的那次除法：

  - <1.0：分布变"尖"，高概率 token 更高、低概率更低 → 更确定、更保守；
  - >1.0：分布被拉平，低概率 token 有了出头机会 → 更发散、更容易胡说；
  -  =0 ：退化成贪心解码，永远选概率最大的那个。

本文件用仓库内的 sample_next_token（纯 Python、确定性 seed）复现这个过程，离线可跑：

    python3 temperature_sampling.py
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_code.llm_call import sample_next_token


# 文章里的例子："今天天气真" 后面的下一个 token 概率分布。
NEXT_TOKEN_DIST = {
    "好": 0.52,
    "不错": 0.18,
    "热": 0.09,
    "糟": 0.06,
    "冷": 0.05,
    "潮": 0.04,
    "闷": 0.03,
    "怪": 0.03,
}

# 不同任务的经验温度参考（文章 §四）。
TASK_TEMPERATURE = {
    "分类 / 抽取 / Function Calling": 0.0,
    "RAG 问答 / 客服": 0.2,
    "代码生成": 0.1,
    "创意写作": 0.9,
}


def show_distribution() -> None:
    print("① 下一个 token 的概率分布（'今天天气真' 之后）")
    for token, p in NEXT_TOKEN_DIST.items():
        bar = "█" * round(p * 40)
        print(f"    {token:<4} {p:>4.2f} {bar}")


def show_sampling_by_temperature() -> None:
    print("\n② 同一个分布，不同 temperature 采样 200 次的结果")
    print("    （seed 随第几次采样递增，模拟真实的多次独立采样）")
    for temp in (0.0, 0.3, 0.7, 1.2):
        counts: Counter[str] = Counter()
        for i in range(200):
            counts[sample_next_token(NEXT_TOKEN_DIST, temperature=temp, seed=i)] += 1
        top = "  ".join(f"{tok}×{n}" for tok, n in counts.most_common(4))
        distinct = len(counts)
        print(f"    T={temp:<3}  出现 {distinct} 种候选 | {top}")
    print("    观察：T 越高，越敢选原本不自信的候选词——看着像创造力，更多时候是胡说八道。")


def show_task_guide() -> None:
    print("\n③ 经验温度参考（不是玄学，是概率分布尖/平的取舍）")
    for task, temp in TASK_TEMPERATURE.items():
        print(f"    T={temp:<3}  {task}")


def show_reproducibility_trap() -> None:
    print("\n④ 陷阱：temperature=0 也不等于 100% 可复现")
    print("    并行推理时 GPU 浮点累加顺序不确定，后端负载均衡可能路由到不同版本。")
    print("    → 回归测试别写  assert response == 'xxx'，要写语义比较或关键字段校验。")


def main() -> None:
    show_distribution()
    show_sampling_by_temperature()
    show_task_guide()
    show_reproducibility_trap()


if __name__ == "__main__":
    main()
