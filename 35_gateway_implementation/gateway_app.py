"""自建 Gateway 最小可上线骨架（FastAPI + Redis + PG）。

对应第 35 篇「三、自建 Gateway 的最小可上线架构」。

每一层都有优雅降级，保证任何机器都能跑：
  - HTTP 层   ：FastAPI + uvicorn  -> 缺则标准库 http.server
  - Redis 层  ：redis（限流计数 + 精确缓存） -> 缺则内存 dict 等价
  - PG 层     ：psycopg（虚拟 Key + 计费/审计） -> 缺则 sqlite 等价
  - Provider  ：真实 API -> 无 key 时确定性 mock

    python3 35_gateway_implementation/gateway_app.py           # 进程内自测（不监听端口）
    python3 35_gateway_implementation/gateway_app.py --serve   # 起 HTTP 服务
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
import time
from pathlib import Path

DB_PATH = str(Path(__file__).resolve().parent / ".gateway_selfbuilt.db")


# ---------------------------------------------------------------------------
# Redis 层：限流令牌桶 + 精确缓存（缺 redis 用内存 dict）
# ---------------------------------------------------------------------------


class RedisBackend:
    def __init__(self) -> None:
        self.kind = "memory"
        self._client = None
        try:
            import redis

            client = redis.Redis(host="localhost", port=6379, socket_connect_timeout=0.2)
            client.ping()  # 真实连接才切换
            self._client = client
            self.kind = "redis"
        except Exception:
            self._store: dict[str, str] = {}
            self._counters: dict[str, list[float]] = {}

    def cache_get(self, key: str) -> str | None:
        if self._client:
            val = self._client.get(key)
            return val.decode() if val else None
        return self._store.get(key)

    def cache_set(self, key: str, value: str) -> None:
        if self._client:
            self._client.set(key, value, ex=3600)
        else:
            self._store[key] = value

    def rate_allow(self, key: str, limit: int, window: float = 60.0, now: float | None = None) -> bool:
        now = now if now is not None else time.time()
        if self._client:
            pipe_key = f"rl:{key}:{int(now // window)}"
            count = self._client.incr(pipe_key)
            if count == 1:
                self._client.expire(pipe_key, int(window))
            return count <= limit
        calls = self._counters.setdefault(key, [])
        calls[:] = [t for t in calls if now - t <= window]
        if len(calls) >= limit:
            return False
        calls.append(now)
        return True


# ---------------------------------------------------------------------------
# PG 层：虚拟 Key + 计费/审计（缺 psycopg 用 sqlite）
# ---------------------------------------------------------------------------


class PGBackend:
    def __init__(self) -> None:
        self.kind = "sqlite"
        self._pg = None
        try:
            import psycopg  # noqa: F401

            # 真实项目连接 PG；此处不假设本地有 PG 实例，仅标记可用性。
            self.kind = "psycopg-available(未连库,回退sqlite)"
        except ImportError:
            pass
        # 无论如何都用 sqlite 作为可跑的落库实现（等价语义）。
        self._conn = sqlite3.connect(DB_PATH)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS virtual_keys (key TEXT PRIMARY KEY, owner TEXT, models TEXT, rpm INTEGER, budget REAL)"
        )
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS usage_log (ts TEXT, key TEXT, model TEXT, provider TEXT, "
            "prompt_tokens INT, completion_tokens INT, cost REAL, cached INT)"
        )
        self._seed()

    def _seed(self) -> None:
        rows = [
            ("gw-sales", "sales", "gpt-4o,claude", 600, 500.0),
            ("gw-support", "support", "claude", 300, 100.0),
        ]
        for row in rows:
            self._conn.execute("INSERT OR IGNORE INTO virtual_keys VALUES (?,?,?,?,?)", row)
        self._conn.commit()

    def get_key(self, key: str) -> dict | None:
        cur = self._conn.execute("SELECT key,owner,models,rpm,budget FROM virtual_keys WHERE key=?", (key,))
        row = cur.fetchone()
        if not row:
            return None
        return {"key": row[0], "owner": row[1], "models": row[2].split(","), "rpm": row[3], "budget": row[4]}

    def log_usage(self, entry: dict) -> None:
        self._conn.execute(
            "INSERT INTO usage_log VALUES (?,?,?,?,?,?,?,?)",
            (
                entry["ts"], entry["key"], entry["model"], entry["provider"],
                entry["prompt_tokens"], entry["completion_tokens"], entry["cost"], int(entry["cached"]),
            ),
        )
        self._conn.commit()

    def usage_summary(self) -> list[tuple]:
        cur = self._conn.execute(
            "SELECT key, COUNT(*), ROUND(SUM(cost),6), SUM(cached) FROM usage_log GROUP BY key"
        )
        return cur.fetchall()


# ---------------------------------------------------------------------------
# Provider 适配 + Fallback
# ---------------------------------------------------------------------------

MODEL_ROUTES = {"gpt-4o": ["openai", "anthropic"], "claude": ["anthropic"]}  # 含 fallback 链
PRICE_PER_1K = {"gpt-4o": 0.005, "claude": 0.004}


def _provider_call(provider: str, model: str, prompt: str) -> str:
    """确定性 mock（无 key 不联网）。真实项目在此对接各 Provider SDK。"""

    return f"[{provider}:{model}] {prompt[:60]}"


# ---------------------------------------------------------------------------
# Gateway 核心
# ---------------------------------------------------------------------------


class Gateway:
    def __init__(self) -> None:
        self.redis = RedisBackend()
        self.pg = PGBackend()

    def backends_info(self) -> str:
        return f"redis={self.redis.kind}, pg={self.pg.kind}"

    def chat(self, api_key: str, body: dict) -> tuple[int, dict]:
        key_info = self.pg.get_key(api_key)
        if key_info is None:
            return 401, {"error": "invalid virtual key"}
        model = body.get("model", "")
        if model not in key_info["models"]:
            return 403, {"error": f"model {model} not allowed for key"}
        if not self.redis.rate_allow(api_key, key_info["rpm"]):
            return 429, {"error": "rate limit exceeded"}

        prompt = "".join(m.get("content", "") for m in body.get("messages", []))
        cache_key = "cache:" + hashlib.sha1(f"{model}:{prompt}".encode()).hexdigest()
        cached = self.redis.cache_get(cache_key)
        if cached is not None:
            content, is_cached, provider = cached, True, "cache"
        else:
            provider = None
            content = None
            for candidate in MODEL_ROUTES.get(model, []):
                try:
                    content = _provider_call(candidate, model, prompt)
                    provider = candidate
                    break
                except Exception:
                    continue
            if content is None:
                return 502, {"error": "all providers exhausted"}
            self.redis.cache_set(cache_key, content)
            is_cached = False

        pt, ct = len(prompt), len(content)
        cost = 0.0 if is_cached else round((pt + ct) / 1000 * PRICE_PER_1K.get(model, 0.005), 6)
        self.pg.log_usage(
            {
                "ts": time.strftime("%Y-%m-%d %H:%M:%S"), "key": api_key, "model": model,
                "provider": provider, "prompt_tokens": pt, "completion_tokens": ct,
                "cost": cost, "cached": is_cached,
            }
        )
        return 200, {
            "id": "chatcmpl-selfbuilt",
            "model": model,
            "choices": [{"message": {"role": "assistant", "content": content}}],
            "usage": {"prompt_tokens": pt, "completion_tokens": ct},
            "x_gateway": {"provider": provider, "cached": is_cached, "cost_usd": cost},
        }


def _self_test() -> None:
    gw = Gateway()
    print("=== 自建 Gateway 自测 ===")
    print("后端：", gw.backends_info(), "\n")
    reqs = [
        ("gw-sales", {"model": "gpt-4o", "messages": [{"role": "user", "content": "什么是 Gateway"}]}),
        ("gw-sales", {"model": "gpt-4o", "messages": [{"role": "user", "content": "什么是 Gateway"}]}),  # 命中缓存
        ("gw-support", {"model": "gpt-4o", "messages": [{"role": "user", "content": "越权"}]}),
        ("bad", {"model": "claude", "messages": []}),
    ]
    for key, body in reqs:
        status, resp = gw.chat(key, body)
        info = resp.get("x_gateway") or resp.get("error")
        print(f"  {key:10} {body['model']:7} -> {status}  {info}")
    print("\n计费汇总（key, 调用数, 总成本, 命中缓存数）：")
    for row in gw.pg.usage_summary():
        print("  ", row)


def _serve(port: int = 4100) -> None:
    gw = Gateway()
    print("后端：", gw.backends_info())
    try:
        import uvicorn
        from fastapi import FastAPI, Header, Request

        app = FastAPI(title="Self-built Gateway (FastAPI+Redis+PG)")

        @app.post("/v1/chat/completions")
        async def chat(request: Request, authorization: str = Header(default="")):
            body = await request.json()
            _, resp = gw.chat(authorization.replace("Bearer ", "").strip(), body)
            return resp

        print(f"FastAPI 监听 http://localhost:{port}/v1/chat/completions")
        uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")
    except ImportError:
        print("缺 FastAPI/uvicorn，降级标准库 http.server。")
        from http.server import BaseHTTPRequestHandler, HTTPServer

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:  # noqa: N802
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length) or b"{}")
                key = self.headers.get("Authorization", "").replace("Bearer ", "").strip()
                status, resp = gw.chat(key, body)
                data = json.dumps(resp).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *args) -> None:
                pass

        print(f"http.server 监听 http://localhost:{port}/v1/chat/completions")
        HTTPServer(("0.0.0.0", port), Handler).serve_forever()


def main() -> int:
    if "--serve" in sys.argv:
        _serve()
    else:
        _self_test()
    return 0


if __name__ == "__main__":
    sys.exit(main())
