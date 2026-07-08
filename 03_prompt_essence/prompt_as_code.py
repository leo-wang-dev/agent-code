"""产物：Prompt 是代码，不是文案（对应文章 §六 最后一条 + §七 收束）。

工业级 Prompt 必须：版本化（Git 可追溯）、参数化（模板引擎、不拼字符串）、
被回归测试覆盖、上线前评估。真正稀缺的不是"会写 Prompt 的人"，是搭得起
版本管理 / 评测 / 灰度 / 回滚这套基础设施的工程师。

本文件复用仓库 PromptTemplate / PromptRegistry：注册两个版本、渲染、跑一个迷你回归集、
打印版本 diff——把"Prompt 当代码管"落成可运行的最小闭环。

    python3 prompt_as_code.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_code.prompt_essence import PromptRegistry, PromptTemplate


V1 = "把工单 {ticket} 路由到正确团队，用一句话说明理由。"
V2 = (
    "把工单 {ticket} 路由到正确团队。\n"
    "输出规范：只返回 JSON {{\"team\": ..., \"reason\": ...}}，不含其他文字。"
)

# 迷你回归集：改 Prompt 后必须重跑，验证关键约束仍成立。
REGRESSION = [
    ("含 {ticket} 占位符", lambda rendered: "{ticket}" not in rendered),
    ("v2 强制结构化输出", lambda rendered: "JSON" in rendered),
]


def main() -> None:
    registry = PromptRegistry()
    registry.add(PromptTemplate("router", "v1", V1, ("ticket",)))
    registry.add(PromptTemplate("router", "v2", V2, ("ticket",)))

    print("① 参数化渲染（模板引擎，不是字符串拼接）")
    latest = registry.get("router")  # 默认取最新版本
    print(f"    默认最新版 = v2")
    print("    渲染结果 →")
    for line in latest.render(ticket="VPN 打不开").splitlines():
        print(f"        {line}")

    print("\n② 版本化：v1 → v2 的 diff（每次改动可追溯）")
    for line in registry.diff("router", "v1", "v2").splitlines():
        print(f"    {line}")

    print("\n③ 回归测试：改 Prompt 后必须重跑")
    rendered_v2 = registry.get("router", "v2").render(ticket="X")
    for name, check in REGRESSION:
        ok = check(rendered_v2)
        print(f"    [{'PASS' if ok else 'FAIL'}] {name}")

    print("\n④ 参数化的护栏：漏传变量直接报错，而不是拼出一段坏 Prompt")
    try:
        latest.render()
    except KeyError as e:
        print(f"    render() 缺参数 → KeyError: {e}")

    print("\n没有版本管理、没有回归测试的 Prompt = 随时可能让生产崩掉的幽灵代码。")


if __name__ == "__main__":
    main()
