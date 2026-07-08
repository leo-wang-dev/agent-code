"""JWT 全套实现（教学版）—— 纯标准库 hmac HS256，无第三方依赖。

对应文章第 46 篇 五、JWT 鉴权的工业级实现。

覆盖：密码哈希、access/refresh 双 token 签发、解码校验、过期/类型校验。

⚠️ 生产替代：
  - JWT 用 `python-jose[cryptography]` 或 `PyJWT`（支持更多算法/时钟偏移/JWKS）。
  - 密码哈希用 `passlib[bcrypt]`（本文件用 pbkdf2_hmac 做教学替身，够安全但接口简化）。
  本文件的价值是把 HS256 的签名/校验拆开讲清楚，便于理解，不建议直接上生产。

离线可运行：`python3 jwt_auth.py`
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time

SECRET_KEY = os.environ.get("JWT_SECRET", "dev-only-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_SECONDS = 3600          # 60 分钟
REFRESH_TOKEN_EXPIRE_SECONDS = 30 * 86400   # 30 天


class JWTError(Exception):
    """签名无效 / 过期 / 结构错误统一抛这个。"""


# ---------- base64url ----------

def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + pad)


# ---------- 密码哈希（教学替身，生产用 bcrypt/argon2）----------

def hash_password(password: str, *, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
    return f"pbkdf2$100000${salt.hex()}${digest.hex()}"


def verify_password(plain: str, stored: str) -> bool:
    try:
        _, iters, salt_hex, digest_hex = stored.split("$")
        digest = hashlib.pbkdf2_hmac(
            "sha256", plain.encode(), bytes.fromhex(salt_hex), int(iters)
        )
        return hmac.compare_digest(digest.hex(), digest_hex)
    except Exception:
        return False


# ---------- JWT 签发 / 校验 ----------

def _sign(signing_input: bytes) -> str:
    sig = hmac.new(SECRET_KEY.encode(), signing_input, hashlib.sha256).digest()
    return _b64url_encode(sig)


def encode(payload: dict) -> str:
    header = {"alg": ALGORITHM, "typ": "JWT"}
    h = _b64url_encode(json.dumps(header, separators=(",", ":")).encode())
    p = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{h}.{p}".encode()
    return f"{h}.{p}.{_sign(signing_input)}"


def decode(token: str) -> dict:
    try:
        h, p, sig = token.split(".")
    except ValueError as e:
        raise JWTError("malformed token") from e

    expected = _sign(f"{h}.{p}".encode())
    if not hmac.compare_digest(sig, expected):
        raise JWTError("invalid signature")

    payload = json.loads(_b64url_decode(p))
    if "exp" in payload and time.time() > payload["exp"]:
        raise JWTError("token expired")
    return payload


def create_access_token(user_id: int, tenant_id: int, role: str) -> str:
    now = int(time.time())
    return encode({
        "sub": str(user_id),
        "tenant_id": tenant_id,
        "role": role,
        "iat": now,
        "exp": now + ACCESS_TOKEN_EXPIRE_SECONDS,
        "type": "access",
    })


def create_refresh_token(user_id: int) -> str:
    now = int(time.time())
    return encode({
        "sub": str(user_id),
        "iat": now,
        "exp": now + REFRESH_TOKEN_EXPIRE_SECONDS,
        "type": "refresh",
    })


def _demo() -> None:
    print("=== 密码哈希 ===")
    stored = hash_password("s3cret")
    print("  hash:", stored[:40], "...")
    print("  verify 正确密码:", verify_password("s3cret", stored))
    print("  verify 错误密码:", verify_password("wrong", stored))

    print("\n=== JWT 签发 / 校验 ===")
    token = create_access_token(user_id=42, tenant_id=7, role="admin")
    print("  token:", token[:50], "...")
    payload = decode(token)
    print("  decoded:", {k: payload[k] for k in ("sub", "tenant_id", "role", "type")})

    print("\n=== 篡改检测 ===")
    tampered = token[:-4] + ("aaaa" if not token.endswith("aaaa") else "bbbb")
    try:
        decode(tampered)
        print("  篡改未被发现(不应出现)")
    except JWTError as e:
        print(f"  篡改被拒: {e}")

    print("\n=== 过期检测 ===")
    expired = encode({"sub": "1", "exp": int(time.time()) - 10, "type": "access"})
    try:
        decode(expired)
    except JWTError as e:
        print(f"  过期被拒: {e}")


if __name__ == "__main__":
    _demo()
