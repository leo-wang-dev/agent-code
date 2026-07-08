"""17 章配套：三层 ID 多租户隔离测试。

对应文章第五节"Mem0 的多租户设计 —— 三层 ID 体系"。

  user_id   ← 用户级别隔离（必填）
  agent_id  ← Agent 级别隔离（选填）
  run_id    ← 会话级别隔离（选填）

用 mem0_integration.Mem0OfflineClient 验证文章列出的四个组合场景：
  A：同一用户、多个 Agent，记忆互相隔离
  B：同一 Agent、多个用户，检索只命中本用户
  C：临时会话 run_id，会话结束可批量清理
  D：不指定 agent_id 的全局共享层

本文件既是示例也是断言测试——每个场景带 assert，跑通即证明隔离边界正确。

离线可运行：`python3 17_mem0/three_tier_id.py`
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mem0_integration import Mem0OfflineClient  # noqa: E402


def _memories(hits) -> set[str]:
    return {h["memory"] for h in hits}


def test_scene_a_agent_isolation() -> None:
    """同一用户、多个 Agent：客服记的事和销售记的事互相看不到。"""
    m = Mem0OfflineClient()
    m.add("我是上海人。", user_id="u123", agent_id="customer_service")
    m.add("我搬到深圳了。", user_id="u123", agent_id="sales")

    cs = _memories(m.search("住哪", user_id="u123", agent_id="customer_service"))
    sales = _memories(m.search("住哪", user_id="u123", agent_id="sales"))
    assert "user lives in Shanghai" in cs
    assert "user lives in Shenzhen" in sales
    assert cs.isdisjoint(sales), "客服与销售记忆串味！"
    print("  [A] Agent 隔离 ✓ 客服={} 销售={}".format(cs, sales))


def test_scene_b_user_isolation() -> None:
    """同一 Agent、多个用户：检索只命中本用户。"""
    m = Mem0OfflineClient()
    m.add("我是产品经理。", user_id="u123", agent_id="bot_a")
    m.add("我养了只猫。", user_id="u456", agent_id="bot_a")

    u123 = _memories(m.search("我是谁", user_id="u123", agent_id="bot_a"))
    u456 = _memories(m.search("我是谁", user_id="u456", agent_id="bot_a"))
    assert "user is a product manager" in u123
    assert "user is a product manager" not in u456
    print("  [B] 用户隔离 ✓ u123={} u456={}".format(u123, u456))


def test_scene_c_run_scoped() -> None:
    """临时会话 run_id：会话结束可批量清理，不污染持久层。"""
    m = Mem0OfflineClient()
    m.add("我搬到深圳了。", user_id="u123", run_id="session_xyz")
    before = _memories(m.search("住哪", user_id="u123", run_id="session_xyz"))
    assert "user lives in Shenzhen" in before

    removed = m.delete_all(user_id="u123", run_id="session_xyz")
    after = m.search("住哪", user_id="u123", run_id="session_xyz")
    assert removed >= 1 and after == []
    print("  [C] 会话级清理 ✓ 清理 {} 条，会话结束后为空".format(removed))


def test_scene_d_global_shared() -> None:
    """不指定 agent_id 的全局层与 Agent 私有层是不同作用域。"""
    m = Mem0OfflineClient()
    m.add("我是上海人。", user_id="u123")                       # 全局共享层
    m.add("我搬到深圳了。", user_id="u123", agent_id="bot_a")    # bot_a 私有层

    shared = _memories(m.search("住哪", user_id="u123"))
    private = _memories(m.search("住哪", user_id="u123", agent_id="bot_a"))
    assert "user lives in Shanghai" in shared
    assert "user lives in Shenzhen" in private
    assert shared != private
    print("  [D] 全局/私有分层 ✓ 全局={} bot_a={}".format(shared, private))


def _demo() -> None:
    print("三层 ID 多租户隔离测试（user / agent / run）：")
    test_scene_a_agent_isolation()
    test_scene_b_user_isolation()
    test_scene_c_run_scoped()
    test_scene_d_global_shared()
    print("\n全部 4 个隔离场景通过 ✓")


if __name__ == "__main__":
    _demo()
