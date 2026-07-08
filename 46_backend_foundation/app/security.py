"""安全层 —— 复用章根 jwt_auth.py（stdlib HS256 教学版）做签发/校验。

对应文章第 46 篇 五、JWT 鉴权。生产替代见 jwt_auth.py 顶部说明
（换 python-jose / PyJWT + passlib[bcrypt]）。
"""

from __future__ import annotations

import sys
from pathlib import Path

# 章根目录的 jwt_auth.py（教学版 stdlib 实现）
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from jwt_auth import (  # noqa: E402
    JWTError,
    create_access_token,
    create_refresh_token,
    decode,
    hash_password,
    verify_password,
)

__all__ = [
    "JWTError",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "hash_password",
    "verify_password",
]


def decode_token(token: str) -> dict:
    """解码并校验；无效则抛 JWTError（API 层转 401）。"""
    return decode(token)
