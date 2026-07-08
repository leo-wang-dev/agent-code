"""PortKey SDK 接入示例 —— 对应第 35 篇「二、PortKey 企业级 SaaS」。

展示 PortKey 四大强项的接入形态：虚拟 Key、语义缓存、链路可视化、A/B 路由。

未安装 portkey-ai 或未配置 key 时，打印安装指引 + 配置样例并 exit 0（不联网）。
"""

from __future__ import annotations

import os
import sys

# PortKey 语义缓存 / A/B 路由配置（文章 §二，config 原样）。
SEMANTIC_CACHE_CONFIG = {"mode": "semantic", "max_age": 86400}  # 缓存 24 小时
AB_ROUTER_CONFIG = {
    "strategy": "ab-test",
    "variants": [
        {"weight": 80, "model": "gpt-4o"},
        {"weight": 20, "model": "claude-3-5-sonnet"},
    ],
}
# 虚拟 Key 层级：组织 -> 工作空间 -> 虚拟 Key（预算/白名单/速率/标签/过期）。
VIRTUAL_KEY_HIERARCHY = {
    "organization": "acme",
    "workspace": "sales",
    "virtual_key": {
        "budget_usd_per_month": 500,
        "allowed_models": ["gpt-4o", "claude-3-5-sonnet"],
        "rate_limit_rpm": 600,
        "metadata": {"team": "sales", "env": "prod"},
        "expires_at": "2026-12-31",
    },
}


def _print_config_reference() -> None:
    print("PortKey 强项配置参考：")
    print("  虚拟 Key 层级：", VIRTUAL_KEY_HIERARCHY)
    print("  语义缓存：", SEMANTIC_CACHE_CONFIG, "（问答类可砍 30-50% token）")
    print("  A/B 路由：", AB_ROUTER_CONFIG)


def main() -> int:
    try:
        from portkey_ai import Portkey
    except ImportError:
        print("未安装 portkey-ai。安装：pip install portkey-ai\n")
        _print_config_reference()
        print("\n典型调用（装好后）：")
        print(
            "    client = Portkey(api_key=PORTKEY_API_KEY, virtual_key=VIRTUAL_KEY)\n"
            "    client.chat.completions.create(model='gpt-4o', messages=[...])"
        )
        return 0

    api_key = os.getenv("PORTKEY_API_KEY")
    virtual_key = os.getenv("PORTKEY_VIRTUAL_KEY")
    if not api_key or not virtual_key:
        print("已安装 portkey-ai，但未设置 PORTKEY_API_KEY / PORTKEY_VIRTUAL_KEY，跳过真实调用。\n")
        _print_config_reference()
        return 0

    # PortKey 是 OpenAI 兼容客户端：虚拟 Key + 配置驱动语义缓存/AB。
    client = Portkey(api_key=api_key, virtual_key=virtual_key)
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": "用一句话解释 LLM Gateway"}],
    )
    print(resp.choices[0].message.content)
    return 0


if __name__ == "__main__":
    sys.exit(main())
