"""LangSmith / Langfuse / Helicone 三家接入示例。

对应文章第二、三、四节。三家接入方式各不相同：
  - LangSmith：设环境变量，LangChain 代码零改动自动追踪
  - Langfuse：装 SDK，用 @observe 装饰器 或 langfuse.openai 透明替换
  - Helicone：反向代理，只改 base_url + 加一个 header，0 代码改动

本文件把三种接入封装成可调用函数，并对所有第三方 import 做 try/except：
缺依赖 / 缺 key 时打印接入指引 + 生产替代，不报错退出。
"""
from __future__ import annotations

import os


# ---------------------------------------------------------------------------
# LangSmith —— 环境变量即开启，LangChain / LangGraph 零改动
# ---------------------------------------------------------------------------
def setup_langsmith() -> bool:
    """开启 LangSmith 追踪。真实使用需 LANGCHAIN_API_KEY。"""
    api_key = os.getenv("LANGCHAIN_API_KEY")
    if not api_key:
        print("[LangSmith] 未配置 LANGCHAIN_API_KEY，示例接入方式：")
        print('    os.environ["LANGCHAIN_TRACING_V2"] = "true"')
        print('    os.environ["LANGCHAIN_API_KEY"] = "lsm-..."')
        print("    # 你的 LangChain / LangGraph 代码完全不用改，自动记录所有 LLM/Tool 调用")
        return False

    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    print("[LangSmith] 已开启追踪（LangChain 生态零改动自动捕获）。")
    return True


# ---------------------------------------------------------------------------
# Langfuse —— 装饰器 / OpenAI 封装，框架无关，可自部署
# ---------------------------------------------------------------------------
def observe_with_langfuse(query: str) -> str:
    """用 Langfuse @observe 装饰器追踪任意函数。"""
    try:
        from langfuse.decorators import observe  # type: ignore
    except ImportError:
        print("[Langfuse] 未安装 langfuse。生产安装：pip install langfuse")
        print("    from langfuse.decorators import observe")
        print("    @observe()")
        print("    def my_agent(query): ...   # 装饰器自动记录调用/参数/返回/耗时")
        print("    # 或用 from langfuse.openai import openai 透明替换 OpenAI 客户端")
        return f"[mock] answered: {query}"

    @observe()
    def my_agent(q: str) -> str:  # noqa: ANN001
        return f"answered: {q}"

    return my_agent(query)


# ---------------------------------------------------------------------------
# Helicone —— 反向代理，只改 base_url + 加 header
# ---------------------------------------------------------------------------
def build_helicone_client():
    """构造走 Helicone 代理的 OpenAI 客户端（接入最快，0 代码改动业务逻辑）。"""
    helicone_key = os.getenv("HELICONE_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    try:
        import openai  # type: ignore
    except ImportError:
        print("[Helicone] 未安装 openai。生产安装：pip install openai")
        print("    client = openai.OpenAI(")
        print('        base_url="https://oai.helicone.ai/v1",   # 改一个地址')
        print('        api_key="sk-...",')
        print('        default_headers={"Helicone-Auth": "Bearer hc-..."},  # 加一个 header')
        print("    )")
        return None

    if not (helicone_key and openai_key):
        print("[Helicone] 未配置 HELICONE_API_KEY / OPENAI_API_KEY，示例见上；返回 None。")
        return None

    return openai.OpenAI(
        base_url="https://oai.helicone.ai/v1",
        api_key=openai_key,
        default_headers={"Helicone-Auth": f"Bearer {helicone_key}"},
    )


def main() -> None:
    print("=" * 56)
    print("三家可观测平台接入示例")
    print("=" * 56)
    print("\n-- LangSmith --")
    setup_langsmith()
    print("\n-- Langfuse --")
    print("  返回：", observe_with_langfuse("员工年假怎么算？"))
    print("\n-- Helicone --")
    client = build_helicone_client()
    print("  client:", "已构造" if client else "None（未配置 key，见上方示例）")
    print("\n三家接入难度：Helicone（改 URL）< LangSmith（环境变量）< Langfuse（装 SDK/装饰器）")


if __name__ == "__main__":
    main()
