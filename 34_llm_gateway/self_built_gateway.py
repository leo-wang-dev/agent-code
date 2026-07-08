"""简易自建 Gateway 骨架 —— 统一 API + Key 校验 + 路由 + 计费落库。

对应第 34 篇「五、路线 B：自建 Gateway」+「六」。

优先用 FastAPI 起真实 HTTP 服务；缺 FastAPI 时降级到标准库 http.server（同样对外提供
OpenAI 兼容的 /v1/chat/completions 端点）。不带参数则跑一次进程内 self-test，不监听端口：

    python3 34_llm_gateway/self_built_gateway.py            # 进程内自测（不联网、不监听）
    python3 34_llm_gateway/self_built_gateway.py --serve    # 起 HTTP 服务(FastAPI 或 http.server)
"""

from __future__ import annotations

import json
import sys
import time

# 内部虚拟 Key -> 允许的模型；真实项目存 DB。
VIRTUAL_KEYS = {
    "gw-sales-team": {"models": ["gpt-4o", "claude"], "owner": "sales"},
    "gw-support": {"models": ["claude"], "owner": "support"},
}
# 模型 -> 后端 Provider 路由（换模型=改字符串，不改 Agent 代码）。
MODEL_ROUTES = {"gpt-4o": "openai", "claude": "anthropic"}
USAGE_LOG: list[dict] = []


def _mock_provider_call(provider: str, model: str, prompt: str) -> dict:
    """确定性 mock：无 API key 时不发网络，返回可复现结果。"""

    completion = f"[{provider}:{model}] {prompt[:60]}"
    return {"content": completion, "prompt_tokens": len(prompt), "completion_tokens": len(completion)}


def handle_chat_completion(api_key: str, body: dict) -> tuple[int, dict]:
    """核心 Proxy 逻辑：鉴权 -> 模型白名单 -> 路由 -> 调用 -> 计费落库。"""

    key_info = VIRTUAL_KEYS.get(api_key)
    if key_info is None:
        return 401, {"error": "invalid virtual key"}

    model = body.get("model", "")
    if model not in key_info["models"]:
        return 403, {"error": f"key not allowed to use model {model}"}

    provider = MODEL_ROUTES.get(model)
    if provider is None:
        return 404, {"error": f"unknown model {model}"}

    prompt = "".join(m.get("content", "") for m in body.get("messages", []))
    result = _mock_provider_call(provider, model, prompt)

    cost = (result["prompt_tokens"] + result["completion_tokens"]) * 1e-5
    USAGE_LOG.append(
        {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "gateway_key": api_key,
            "owner": key_info["owner"],
            "model": model,
            "provider": provider,
            "prompt_tokens": result["prompt_tokens"],
            "completion_tokens": result["completion_tokens"],
            "cost_usd": round(cost, 6),
        }
    )
    # OpenAI 兼容响应形态。
    return 200, {
        "id": f"chatcmpl-{len(USAGE_LOG)}",
        "model": model,
        "choices": [{"message": {"role": "assistant", "content": result["content"]}}],
        "usage": {
            "prompt_tokens": result["prompt_tokens"],
            "completion_tokens": result["completion_tokens"],
        },
    }


def _self_test() -> None:
    print("=== 自建 Gateway 进程内自测 ===")
    cases = [
        ("gw-sales-team", {"model": "gpt-4o", "messages": [{"role": "user", "content": "什么是 RAG"}]}),
        ("gw-support", {"model": "gpt-4o", "messages": [{"role": "user", "content": "越权用模型"}]}),
        ("bad-key", {"model": "claude", "messages": []}),
    ]
    for key, body in cases:
        status, resp = handle_chat_completion(key, body)
        summary = resp.get("choices", [{}])[0].get("message", {}).get("content") or resp.get("error")
        print(f"  key={key:14} model={body['model']:7} -> {status} {summary}")
    print("\n计费落库记录：")
    for row in USAGE_LOG:
        print("  ", row)


def _serve(port: int = 4000) -> None:
    try:
        import uvicorn
        from fastapi import FastAPI, Header, Request

        app = FastAPI(title="Self-built LLM Gateway")

        @app.post("/v1/chat/completions")
        async def chat_completions(request: Request, authorization: str = Header(default="")):
            api_key = authorization.replace("Bearer ", "").strip()
            body = await request.json()
            status, resp = handle_chat_completion(api_key, body)
            return resp if status == 200 else (resp, status)

        print(f"FastAPI Gateway 监听 http://localhost:{port}/v1/chat/completions")
        uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")
    except ImportError:
        print("未安装 FastAPI/uvicorn（pip install fastapi uvicorn），降级到标准库 http.server。")
        from http.server import BaseHTTPRequestHandler, HTTPServer

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:  # noqa: N802
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length) or b"{}")
                api_key = self.headers.get("Authorization", "").replace("Bearer ", "").strip()
                status, resp = handle_chat_completion(api_key, body)
                payload = json.dumps(resp).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *args) -> None:  # 静音
                pass

        print(f"http.server Gateway 监听 http://localhost:{port}/v1/chat/completions")
        HTTPServer(("0.0.0.0", port), Handler).serve_forever()


def main() -> int:
    if "--serve" in sys.argv:
        _serve()
    else:
        _self_test()
    return 0


if __name__ == "__main__":
    sys.exit(main())
