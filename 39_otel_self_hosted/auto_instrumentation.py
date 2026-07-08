"""自动 instrumentation 配置 —— 不要手写埋点。

对应文章第三节。手写 span 繁琐，用现成 instrumentation 库自动埋点：
装一个包就自动追踪所有 OpenAI / Anthropic / LangChain 调用，
产生的 span 自动符合 OTel GenAI 约定。

主流库：
  opentelemetry-instrumentation-openai      OpenAI 调用
  opentelemetry-instrumentation-anthropic   Anthropic 调用
  opentelemetry-instrumentation-langchain   LangChain 流程
  traceloop-sdk / openllmetry               全家桶（覆盖 30+ LLM 库，推荐）

本文件对各 instrumentor 做 try/except：装了就启用，没装就打印安装指引，
不报错。生产直接用 traceloop-sdk 一个包覆盖全场景。
"""
from __future__ import annotations


def enable_instrumentors() -> list[str]:
    """尝试启用各自动 instrumentation 库，返回已启用列表。"""
    enabled: list[str] = []

    try:
        from opentelemetry.instrumentation.openai import OpenAIInstrumentor  # type: ignore

        OpenAIInstrumentor().instrument()  # 自动追踪所有 OpenAI 调用
        enabled.append("openai")
    except ImportError:
        print("[未装] pip install opentelemetry-instrumentation-openai")

    try:
        from opentelemetry.instrumentation.anthropic import AnthropicInstrumentor  # type: ignore

        AnthropicInstrumentor().instrument()
        enabled.append("anthropic")
    except ImportError:
        print("[未装] pip install opentelemetry-instrumentation-anthropic")

    try:
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor  # type: ignore

        HTTPXClientInstrumentor().instrument()  # 自动追踪所有 HTTP 调用
        enabled.append("httpx")
    except ImportError:
        print("[未装] pip install opentelemetry-instrumentation-httpx")

    return enabled


def enable_traceloop() -> bool:
    """推荐：traceloop-sdk 全家桶，一行初始化覆盖 30+ LLM 库。"""
    try:
        from traceloop.sdk import Traceloop  # type: ignore

        Traceloop.init(app_name="agent-observability")
        return True
    except ImportError:
        print("[未装] pip install traceloop-sdk   # 推荐：装一个包覆盖全场景")
        print("       from traceloop.sdk import Traceloop")
        print('       Traceloop.init(app_name="...")')
        return False


def main() -> None:
    print("=" * 56)
    print("自动 instrumentation 启用")
    print("=" * 56)
    print("\n-- 单库 instrumentor --")
    enabled = enable_instrumentors()
    print(f"已启用：{enabled or '（当前环境未安装任何 instrumentor）'}")
    print("\n-- 全家桶（推荐）--")
    ok = enable_traceloop()
    print(f"traceloop：{'已初始化' if ok else '未安装（见上方指引）'}")
    print("\n启用后正常调用 SDK 即自动产生符合 OTel GenAI 约定的 span，无需手写埋点。")


if __name__ == "__main__":
    main()
