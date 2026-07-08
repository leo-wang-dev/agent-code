"""企业微信适配器 —— 加密回调：msg_signature 校验 + AES-CBC 加解密。

对应文章第 47 篇 六、第三方接入（企业微信）。

企业微信的回调是加密模式：
  - msg_signature = sha1(sorted([token, timestamp, nonce, encrypt]))；
  - 密文 = base64( AES-CBC( random(16) + msglen(4,BE) + msg + receiveid ) )，
    key = base64decode(EncodingAESKey + "=")（32 字节），iv = key[:16]。

AES 用 `cryptography`（未装则打印安装指引，签名校验部分仍可跑）。
离线可跑：`python3 wecom.py`（本地生成密钥 → 加密 → 验签 → 解密 往返自测）。
"""

from __future__ import annotations

import base64
import hashlib
import os
import socket
import struct
from dataclasses import dataclass

try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

    _HAS_CRYPTO = True
except Exception:  # pragma: no cover
    Cipher = algorithms = modes = None  # type: ignore
    _HAS_CRYPTO = False


class WeComCryptoError(Exception):
    pass


def make_msg_signature(token: str, timestamp: str, nonce: str, encrypt: str) -> str:
    raw = "".join(sorted([token, timestamp, nonce, encrypt]))
    return hashlib.sha1(raw.encode()).hexdigest()


def verify_msg_signature(token: str, signature: str, timestamp: str, nonce: str, encrypt: str) -> bool:
    return make_msg_signature(token, timestamp, nonce, encrypt) == signature


def _aes_key(encoding_aes_key: str) -> bytes:
    key = base64.b64decode(encoding_aes_key + "=")
    if len(key) != 32:
        raise WeComCryptoError("AESKey 必须 32 字节（EncodingAESKey 43 字符）")
    return key


def _pkcs7_pad(data: bytes, block: int = 32) -> bytes:
    pad = block - (len(data) % block)
    return data + bytes([pad]) * pad


def _pkcs7_unpad(data: bytes) -> bytes:
    pad = data[-1]
    return data[:-pad]


def encrypt_message(msg: str, encoding_aes_key: str, receive_id: str) -> str:
    """加密（生产由企业微信服务器做；这里用于自测往返）。"""
    if not _HAS_CRYPTO:
        raise WeComCryptoError("需要 cryptography：pip install cryptography")
    key = _aes_key(encoding_aes_key)
    iv = key[:16]
    body = msg.encode()
    payload = os.urandom(16) + struct.pack(">I", len(body)) + body + receive_id.encode()
    padded = _pkcs7_pad(payload)
    encryptor = Cipher(algorithms.AES(key), modes.CBC(iv)).encryptor()
    ct = encryptor.update(padded) + encryptor.finalize()
    return base64.b64encode(ct).decode()


def decrypt_message(encrypt_b64: str, encoding_aes_key: str) -> tuple[str, str]:
    """解密，返回 (明文消息, receive_id)。"""
    if not _HAS_CRYPTO:
        raise WeComCryptoError("需要 cryptography：pip install cryptography")
    key = _aes_key(encoding_aes_key)
    iv = key[:16]
    ct = base64.b64decode(encrypt_b64)
    decryptor = Cipher(algorithms.AES(key), modes.CBC(iv)).decryptor()
    plain = _pkcs7_unpad(decryptor.update(ct) + decryptor.finalize())
    msg_len = struct.unpack(">I", plain[16:20])[0]
    msg = plain[20:20 + msg_len].decode()
    receive_id = plain[20 + msg_len:].decode()
    return msg, receive_id


@dataclass
class WeComCallback:
    token: str
    encoding_aes_key: str
    corp_id: str

    def handle(self, signature: str, timestamp: str, nonce: str, encrypt: str) -> str:
        """验签 → 解密 → 返回明文消息。生产里再走 Agent + 主动回复接口。"""
        if not verify_msg_signature(self.token, signature, timestamp, nonce, encrypt):
            raise WeComCryptoError("msg_signature 校验失败")
        msg, receive_id = decrypt_message(encrypt, self.encoding_aes_key)
        if receive_id != self.corp_id:
            raise WeComCryptoError(f"receive_id 不匹配: {receive_id}")
        return msg


def _demo() -> None:
    token = "demo-token"
    # 43 字符的 EncodingAESKey（base64，解码后 32 字节）
    encoding_aes_key = base64.b64encode(os.urandom(32)).decode()[:43]
    corp_id = "ww_demo_corp"

    if not _HAS_CRYPTO:
        print("[提示] 未安装 cryptography，AES 部分跳过。安装：pip install cryptography")
        # 仅演示签名校验
        sig = make_msg_signature(token, "1700000000", "nonce", "ENC")
        print("  签名校验:", verify_msg_signature(token, sig, "1700000000", "nonce", "ENC"))
        return

    inner_xml = (
        "<xml><ToUserName><![CDATA[ww_demo_corp]]></ToUserName>"
        "<FromUserName><![CDATA[zhangsan]]></FromUserName>"
        "<MsgType><![CDATA[text]]></MsgType>"
        "<Content><![CDATA[帮我查一下这个月的成本]]></Content></xml>"
    )

    print("=== 加密 → 验签 → 解密 往返 ===")
    encrypt = encrypt_message(inner_xml, encoding_aes_key, corp_id)
    ts, nonce = "1700000000", "randnonce"
    sig = make_msg_signature(token, ts, nonce, encrypt)
    print("  密文(前40):", encrypt[:40], "...")
    print("  msg_signature 校验:", verify_msg_signature(token, sig, ts, nonce, encrypt))

    cb = WeComCallback(token=token, encoding_aes_key=encoding_aes_key, corp_id=corp_id)
    recovered = cb.handle(sig, ts, nonce, encrypt)
    print("  解密还原一致:", recovered == inner_xml)

    print("\n=== 篡改密文被拒 ===")
    try:
        cb.handle(sig, ts, nonce, encrypt[:-4] + "AAAA")
    except WeComCryptoError as e:
        print("  被拒:", e)


if __name__ == "__main__":
    _demo()
