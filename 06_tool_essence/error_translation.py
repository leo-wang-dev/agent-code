"""产物：错误翻译层（对应文章 §二/§六 "错误要可读"）。

工具会失败：API 超时、数据库报错、权限不足。绝不能把 stack trace 直接塞回模型——
给模型看的错误不是日志，是它下一步决策的依据。必须翻译成结构化、可区分的错误：
temporary(可重试) / permission(要审批) / bad_tool(工具名错) / unknown。

本文件用仓库 ErrorTranslator 把各类异常翻成结构化错误，并演示模型据此做不同决策。

    python3 error_translation.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_code.tool_essence import ErrorTranslator


# 模型看到不同 type 应采取的下一步（错误是决策依据，不是日志）。
NEXT_ACTION = {
    "temporary": "退避后重试，或改成更小的任务",
    "permission": "转人工审批链路，不要自行执行",
    "bad_tool": "工具名不存在，换用正确工具或告知用户",
    "unknown": "如实上报，不要编造成功",
}


def main() -> None:
    translator = ErrorTranslator()

    raw_errors = [
        TimeoutError("upstream weather API timed out after 5s"),
        PermissionError("user lacks refund:write scope"),
        KeyError("unknown tool: send_sms"),
        ValueError("division by zero in calculate"),
    ]

    print(f"{'原始异常':<28}{'翻译后 type':<14}模型下一步")
    print("-" * 72)
    for err in raw_errors:
        translated = translator.translate(err)
        etype = translated["type"]
        print(f"{type(err).__name__ + ': ' + str(err)[:20]:<28}{etype:<14}{NEXT_ACTION[etype]}")

    print("\n对比反面教材：直接把 Traceback 塞回模型 → 模型看不懂、乱重试、或幻觉出成功。")
    print("原则：permission / timeout_retryable / invalid_argument 要区分清楚，")
    print("      每一类对应模型一个明确的下一步动作。")


if __name__ == "__main__":
    main()
