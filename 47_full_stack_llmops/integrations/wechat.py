"""微信公众号适配器 —— 签名校验 + 明文消息收发（XML）。

对应文章第 47 篇 六、第三方接入 + 关键适配实现 + 重要：异步响应模式。

公众号明文模式：
  - URL 验证(GET)：校验 signature=sha1(sorted[token,timestamp,nonce]) 后回显 echostr；
  - 消息(POST)：解析 XML → 交给 Agent → 组装 XML 回复（或先回 success 走客服消息异步回复）。

纯标准库，离线可跑：`python3 wechat.py`（自测签名 + 解析 + 回复 XML）。
"""

from __future__ import annotations

import hashlib
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass


@dataclass
class WeChatMessage:
    to_user: str        # 开发者微信号（公众号）
    from_user: str      # 发送者 openid
    msg_type: str
    content: str
    create_time: int


def check_signature(token: str, signature: str, timestamp: str, nonce: str) -> bool:
    """校验微信服务器签名：sha1(sorted([token, timestamp, nonce]))。"""
    raw = "".join(sorted([token, timestamp, nonce]))
    computed = hashlib.sha1(raw.encode()).hexdigest()
    return computed == signature


def make_signature(token: str, timestamp: str, nonce: str) -> str:
    """（测试/自测用）按微信规则生成签名。"""
    raw = "".join(sorted([token, timestamp, nonce]))
    return hashlib.sha1(raw.encode()).hexdigest()


def parse_message(xml_body: str) -> WeChatMessage:
    """解析微信推送的 XML 消息。"""
    root = ET.fromstring(xml_body)

    def text(tag: str) -> str:
        el = root.find(tag)
        return el.text or "" if el is not None else ""

    return WeChatMessage(
        to_user=text("ToUserName"),
        from_user=text("FromUserName"),
        msg_type=text("MsgType"),
        content=text("Content"),
        create_time=int(text("CreateTime") or "0"),
    )


def format_text_reply(msg: WeChatMessage, content: str) -> str:
    """组装文本回复 XML（同步回复；注意来回 to/from 对调）。"""
    return (
        "<xml>"
        f"<ToUserName><![CDATA[{msg.from_user}]]></ToUserName>"
        f"<FromUserName><![CDATA[{msg.to_user}]]></FromUserName>"
        f"<CreateTime>{int(time.time())}</CreateTime>"
        "<MsgType><![CDATA[text]]></MsgType>"
        f"<Content><![CDATA[{content}]]></Content>"
        "</xml>"
    )


# 异步响应模式：微信 5 秒超时——超过必须先回 success，再走客服消息接口主动回复。
def handle_webhook(token: str, signature: str, timestamp: str, nonce: str,
                   xml_body: str, agent_reply) -> str:
    """webhook 主处理：验签 → 解析 → 生成回复 XML。

    agent_reply: Callable[[str], str] —— 传入用户文本，返回助手文本（这里同步 mock，
    生产里若耗时 > 5s 应改为立即回 'success' + 客服消息接口异步回复）。
    """
    if not check_signature(token, signature, timestamp, nonce):
        return "invalid signature"
    msg = parse_message(xml_body)
    reply_text = agent_reply(msg.content)
    return format_text_reply(msg, reply_text)


def _demo() -> None:
    token = "demo-token"
    ts, nonce = "1700000000", "abc123"

    print("=== 签名校验 ===")
    sig = make_signature(token, ts, nonce)
    print("  正确签名通过:", check_signature(token, sig, ts, nonce))
    print("  错误签名拒绝:", not check_signature(token, "deadbeef", ts, nonce))

    print("\n=== 消息解析 + 回复 ===")
    incoming = (
        "<xml><ToUserName><![CDATA[gh_public]]></ToUserName>"
        "<FromUserName><![CDATA[user_openid]]></FromUserName>"
        "<CreateTime>1700000000</CreateTime>"
        "<MsgType><![CDATA[text]]></MsgType>"
        "<Content><![CDATA[你好，我要退货]]></Content></xml>"
    )
    reply = handle_webhook(
        token, sig, ts, nonce, incoming,
        agent_reply=lambda text: f"收到您的问题「{text}」，正在为您处理退货流程。",
    )
    print("  回复 XML:")
    print("   ", reply)


if __name__ == "__main__":
    _demo()
