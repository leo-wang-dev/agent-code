"""第三方适配器离线自测入口 —— 一次跑通微信公众号 + 企业微信收发。

对应文章第 47 篇 六、第三方接入。运行：`python3 demo_adapters.py`
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import wechat  # noqa: E402
import wecom  # noqa: E402


def main() -> None:
    print("#" * 56)
    print("# 微信公众号适配器")
    print("#" * 56)
    wechat._demo()

    print("\n" + "#" * 56)
    print("# 企业微信适配器")
    print("#" * 56)
    wecom._demo()


if __name__ == "__main__":
    main()
