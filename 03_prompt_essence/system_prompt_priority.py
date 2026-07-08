"""产物：System Prompt 的"优先级"是怎么来的（对应文章 §二）。

两个反直觉事实：
  1. System 的"最高优先级"是 RLHF 训练出的统计倾向，不是 if-else 强制约束。
     所以 Prompt 只能挡掉约 60%~80% 的 Prompt Injection，剩下必须靠独立 Guardrail 层。
  2. "Lost in the Middle"：放在 Prompt 中段的内容被有效利用的概率，远低于头/尾。
     → 硬规则放头部，风格说明放中段，本轮任务的具体指令放尾部。

本文件用一个"位置权重"启发式模型把这两点演示出来（纯离线）：给同一条硬规则放在
头/中/尾三个位置，打印它被"有效遵守"的估计强度。

    python3 system_prompt_priority.py
"""

from __future__ import annotations


# System 约束力的经验区间（文章 §二：不同模型差别很大）。
INJECTION_BLOCK_RATE = {
    "GPT-4 系列（对 System 顽固）": 0.80,
    "微调充分的商用模型": 0.70,
    "微调不足的开源模型": 0.35,
}


def positional_weight(index: int, total: int) -> float:
    """Lost in the Middle：头/尾权重高，中段被'看到'的概率低。"""
    if total <= 1:
        return 1.0
    pos = index / (total - 1)  # 0=头, 1=尾
    # U 形：两端接近 1.0，中段掉到约 0.55。
    return 0.55 + 0.45 * abs(2 * pos - 1)


def show_injection_reality() -> None:
    print("① System 拦截 Prompt Injection 的比例（统计倾向，不是硬约束）")
    for model, rate in INJECTION_BLOCK_RATE.items():
        print(f"    {model:<22} ≈ 拦下 {rate:.0%}，剩 {1 - rate:.0%} 必须靠 Guardrail 层兜底")


def show_lost_in_the_middle() -> None:
    lines = [
        "硬规则：绝不透露内部系统路径",       # 应放头部
        "风格：语气亲切、多用短句",
        "背景：本店主营母婴用品",
        "背景：客服工作时间 9:00-21:00",
        "本轮任务：回答用户关于退货的问题",   # 应放尾部
    ]
    print("\n② Lost in the Middle：同一段 System 里，各行被有效利用的估计强度")
    n = len(lines)
    for i, line in enumerate(lines):
        w = positional_weight(i, n)
        flag = "  ← 关键规则被埋在中段，危险！" if (0.2 < i / (n - 1) < 0.8 and "硬规则" in line) else ""
        print(f"    pos {i} 权重{w:.2f} {'█' * round(w * 20):<20} {line}{flag}")
    print("    结论：硬规则放头部、次要风格放中段、本轮指令放尾部。")


def show_data_in_system_waste() -> None:
    print("\n③ 别把业务数据塞进 System")
    manual_tokens = 1500  # 3000 字产品手册 ≈ 1500 input token
    calls_per_month = 200_000
    print(f"    把 3000 字手册塞进 System：每次固定多付 {manual_tokens} input token，")
    print(f"    按 {calls_per_month:,} 次/月算就是白烧 {manual_tokens * calls_per_month:,} token/月。")
    print("    正解：业务数据走 RAG 动态注入 user；System 只装'如何做事的元规则'。")


def main() -> None:
    show_injection_reality()
    show_lost_in_the_middle()
    show_data_in_system_waste()


if __name__ == "__main__":
    main()
