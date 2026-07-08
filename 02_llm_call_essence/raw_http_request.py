"""产物：裸 HTTP 请求形态（对应文章 §一 "它就是一个普通的 REST API"）。

把一次 LLM 调用还原成最原始的 POST /v1/chat/completions 形态：一个 URL、一个
messages 数组、一段 JSON body。剥掉所有框架包装后，它和公司后台任意一个 REST 接口
长得一模一样，因此普通 HTTP 的所有可靠性手段（超时/重试/退避/熔断/降级/追踪）全部适用。

离线运行，绝不发网络请求：只把请求"打印"出来给你看，不真的发出去。

    python3 raw_http_request.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_code.llm_call import ChatMessage, LLMRequest, build_raw_http_request


# 文章里给出的响应示例：id / usage / finish_reason 三个字段一定要落盘或留意。
MOCK_RESPONSE = {
    "id": "chatcmpl-9xexample",
    "choices": [
        {
            "message": {"role": "assistant", "content": "BPE (Byte Pair Encoding) 是一种..."},
            "finish_reason": "stop",
        }
    ],
    "usage": {"prompt_tokens": 28, "completion_tokens": 186, "total_tokens": 214},
}

FINISH_REASON_MEANING = {
    "stop": "正常结束",
    "length": "输出被 max_tokens 截断",
    "tool_calls": "模型要调用工具",
    "content_filter": "被合规拦截",
}


def main() -> None:
    request = LLMRequest(
        model="gpt-4o",
        messages=[
            ChatMessage("system", "你是一个严谨的技术助手。"),
            ChatMessage("user", "什么是 BPE？"),
        ],
        temperature=0.7,
        max_tokens=500,
        stream=False,
    )

    print("=" * 60)
    print("① 请求：一个普通的 HTTP POST（这里只打印，不真的发出去）")
    print("=" * 60)
    print(build_raw_http_request(request))

    print("\n" + "=" * 60)
    print("② 响应：跟公司后台任意 REST 接口一样的 JSON")
    print("=" * 60)
    print(json.dumps(MOCK_RESPONSE, ensure_ascii=False, indent=2))

    reason = MOCK_RESPONSE["choices"][0]["finish_reason"]
    usage = MOCK_RESPONSE["usage"]
    print("\n" + "=" * 60)
    print("③ 上线后最容易漏的三个字段")
    print("=" * 60)
    print(f"id           = {MOCK_RESPONSE['id']}   ← 找 OpenAI 客服唯一凭证，必须落盘")
    print(f"usage        = {usage}   ← 月底对账唯一依据，必须落盘")
    print(f"finish_reason= {reason} ({FINISH_REASON_MEANING[reason]})  ← 回答异常先看它")


if __name__ == "__main__":
    main()
