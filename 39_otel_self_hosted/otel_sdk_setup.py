"""OpenTelemetry SDK 完整接入示例（GenAI Semantic Conventions）。

对应文章第二节。每个 LLM 调用作为一个 Span，用 OTel 社区 2024 年推出的
GenAI 语义约定命名属性（gen_ai.*），这样所有 OTel 兼容工具都能读懂 LLM trace。
Tool 调用 / RAG 检索用工业实践的 span 命名（tool.execute / rag.retrieve）。

真实使用：
    pip install opentelemetry-sdk opentelemetry-exporter-otlp
    export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317

缺 opentelemetry 时，本文件回退到一个打印式 mock tracer（同名 API），
让 span 结构与属性直接打印到终端，保证可运行、可讲解。
"""
from __future__ import annotations

import json
from contextlib import contextmanager

# ---------------------------------------------------------------------------
# tracer：真实 OTel 或打印式 mock
# ---------------------------------------------------------------------------
try:
    from opentelemetry import trace  # type: ignore
    from opentelemetry.sdk.trace import TracerProvider  # type: ignore
    from opentelemetry.sdk.trace.export import (  # type: ignore
        BatchSpanProcessor,
        ConsoleSpanExporter,
    )

    trace.set_tracer_provider(TracerProvider())
    trace.get_tracer_provider().add_span_processor(
        BatchSpanProcessor(ConsoleSpanExporter())
    )
    tracer = trace.get_tracer(__name__)
    _REAL_OTEL = True
except ImportError:
    _REAL_OTEL = False
    print("[提示] 未安装 opentelemetry，使用打印式 mock tracer。")
    print("       生产安装：pip install opentelemetry-sdk opentelemetry-exporter-otlp\n")

    class _MockSpan:
        def __init__(self, name: str) -> None:
            self.name = name
            self.attributes: dict = {}

        def set_attribute(self, key: str, value) -> None:  # noqa: ANN001
            self.attributes[key] = value

    class _MockTracer:
        @contextmanager
        def start_as_current_span(self, name: str):
            span = _MockSpan(name)
            try:
                yield span
            finally:
                print(f"[span] {span.name}")
                for k, v in span.attributes.items():
                    print(f"    {k} = {v}")

    tracer = _MockTracer()


# ---------------------------------------------------------------------------
# 确定性 mock LLM 响应（无 API key 时）
# ---------------------------------------------------------------------------
class _Usage:
    prompt_tokens = 42
    completion_tokens = 18


class _Choice:
    finish_reason = "stop"


class _Resp:
    model = "gpt-4o-2024-08-06"
    id = "chatcmpl-demo-0001"
    usage = _Usage()
    choices = [_Choice()]


def _mock_chat_completion(**kwargs) -> _Resp:  # noqa: ANN003
    return _Resp()


# ---------------------------------------------------------------------------
# 三种 span：LLM chat / Tool 调用 / RAG 检索
# ---------------------------------------------------------------------------
def traced_chat(model: str = "gpt-4o", temperature: float = 0.2) -> _Resp:
    with tracer.start_as_current_span("chat") as span:
        span.set_attribute("gen_ai.system", "openai")
        span.set_attribute("gen_ai.operation.name", "chat")
        span.set_attribute("gen_ai.request.model", model)
        span.set_attribute("gen_ai.request.temperature", temperature)
        span.set_attribute("gen_ai.request.max_tokens", 1000)

        response = _mock_chat_completion(model=model, temperature=temperature)

        span.set_attribute("gen_ai.response.model", response.model)
        span.set_attribute("gen_ai.response.id", response.id)
        span.set_attribute("gen_ai.response.finish_reasons", [response.choices[0].finish_reason])
        span.set_attribute("gen_ai.usage.input_tokens", response.usage.prompt_tokens)
        span.set_attribute("gen_ai.usage.output_tokens", response.usage.completion_tokens)
        return response


def traced_tool(name: str, args: dict) -> dict:
    with tracer.start_as_current_span("tool.execute") as span:
        span.set_attribute("tool.name", name)
        span.set_attribute("tool.args", json.dumps(args, ensure_ascii=False))
        result = {"ok": True, "rows": 3}  # mock
        span.set_attribute("tool.success", result["ok"])
        return result


def traced_rag(query: str, top_k: int = 5) -> list[dict]:
    with tracer.start_as_current_span("rag.retrieve") as span:
        span.set_attribute("rag.query", query)
        span.set_attribute("rag.top_k", top_k)
        span.set_attribute("rag.embedding_model", "bge-large-zh")
        chunks = [{"score": 0.82}, {"score": 0.77}, {"score": 0.71}]  # mock
        span.set_attribute("rag.results_count", len(chunks))
        span.set_attribute("rag.avg_score", round(sum(c["score"] for c in chunks) / len(chunks), 3))
        return chunks


def main() -> None:
    print("=" * 56)
    print("OTel GenAI 语义约定 span 演示")
    print("=" * 56)
    traced_rag("员工年假怎么算？")
    traced_tool("query_order", {"order_id": "ORD20260530"})
    traced_chat()
    print(f"\n模式：{'真实 OTel（ConsoleSpanExporter）' if _REAL_OTEL else '打印式 mock'}")


if __name__ == "__main__":
    main()
