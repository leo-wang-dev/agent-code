"""离线入口 —— 不依赖 FastAPI/Postgres，验证后端骨架的核心能力。

对应文章第 46 篇。演示：
  1. JWT 全套（签发/校验/篡改/过期）
  2. 多租户隔离（自动过滤）
  3. schema.sql 的 16 张表统计
  4. FastAPI app 能否构造（装了 fastapi 才试，缺则打印指引）

运行：`python3 run_demo.py`
"""

from __future__ import annotations

import re
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _demo_jwt() -> None:
    import jwt_auth

    print("=" * 56)
    print("1. JWT 全套（stdlib HS256 教学版）")
    print("=" * 56)
    stored = jwt_auth.hash_password("s3cret")
    print("  密码校验:", jwt_auth.verify_password("s3cret", stored),
          "/ 错误密码:", jwt_auth.verify_password("x", stored))
    token = jwt_auth.create_access_token(42, 7, "admin")
    payload = jwt_auth.decode(token)
    print("  token 解码:", {k: payload[k] for k in ("sub", "tenant_id", "role")})
    try:
        jwt_auth.decode(token[:-3] + "zzz")
    except jwt_auth.JWTError as e:
        print("  篡改被拒:", e)


def _demo_tenant() -> None:
    import multitenancy as mt

    print("\n" + "=" * 56)
    print("2. 多租户隔离（ContextVar 自动过滤）")
    print("=" * 56)
    table = mt.InMemoryTable()
    mt.current_tenant_id.set(1)
    table.insert({"name": "客服 Agent"})
    mt.current_tenant_id.set(2)
    table.insert({"name": "研究 Agent"})
    mt.current_tenant_id.set(1)
    print("  t1 可见:", [r["name"] for r in table.query_tenant()])
    mt.current_tenant_id.set(2)
    print("  t2 可见:", [r["name"] for r in table.query_tenant()])


def _demo_schema() -> None:
    print("\n" + "=" * 56)
    print("3. schema.sql —— 核心表统计")
    print("=" * 56)
    sql = (HERE / "schema.sql").read_text(encoding="utf-8")
    tables = re.findall(r"CREATE TABLE (\w+)", sql)
    print(f"  共 {len(tables)} 张表:")
    for i, t in enumerate(tables, 1):
        print(f"    {i:>2}. {t}")


def _demo_fastapi() -> None:
    print("\n" + "=" * 56)
    print("4. FastAPI app 构造")
    print("=" * 56)
    try:
        import app.main as m
        if m.app is None:
            m._print_install_help()
        else:
            print(f"  app 构造成功，已注册路由数: {len(m.app.routes)}")
            paths = sorted({getattr(r, 'path', '') for r in m.app.routes})
            for p in paths:
                if p.startswith("/api"):
                    print("    ", p)
    except Exception as e:  # noqa: BLE001
        print("  跳过（缺依赖或导入失败）:", e)


def main() -> None:
    _demo_jwt()
    _demo_tenant()
    _demo_schema()
    _demo_fastapi()


if __name__ == "__main__":
    main()
