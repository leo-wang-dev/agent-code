"""16 章配套：用户记忆面板示例 API。

对应文章第五节地雷 3"隐私边界"的应对：用户可见的"记忆面板"——
让用户看到 Agent 都记了什么，可以一条一条删（GDPR / 个保法的被遗忘权）。

提供一个纯 Python 的服务层 MemoryPanel（不绑任何 web 框架），
并在有 fastapi 依赖时额外挂出 REST 路由；缺依赖时打印接入指引并用离线自测代替。

  GET    /memory/{user_id}            列出该用户所有活跃记忆
  DELETE /memory/{user_id}/{fact_id}  删除单条（用户撤回，软删 + 应从向量索引移除）
  DELETE /memory/{user_id}            清空该用户全部记忆（合规：可被 user_id 完整清除）

离线可运行：`python3 16_memory_pipeline/memory_panel_api.py`
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from memory_system import MemoryStore, build_demo_store  # noqa: E402


class MemoryPanel:
    """记忆面板服务层——不依赖 web 框架，便于单测和复用。"""

    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    def list_memory(self, user_id: str) -> list[dict]:
        items = []
        for fact in self.store.all_facts():
            if fact.user_id != user_id or fact.is_deprecated:
                continue
            items.append(
                {
                    "id": fact.id,
                    "type": fact.type,
                    "key": fact.key,
                    "value": fact.value,
                    "confidence": round(fact.confidence, 3),
                    "importance": round(fact.importance, 3),
                    "source_conversation_id": fact.source_conversation_id,
                    "created_at": fact.created_at,
                }
            )
        return sorted(items, key=lambda x: x["created_at"])

    def delete_fact(self, user_id: str, fact_id: str) -> bool:
        """用户撤回单条：软删 + 标记需从向量索引移除。"""
        for fact in self.store.all_facts():
            if fact.id == fact_id and fact.user_id == user_id and not fact.is_deprecated:
                fact.is_deprecated = True
                fact.updated_at = time.time()
                # 线上此处还要：vector_db.delete(fact_id) 物理删除 embedding
                return True
        return False

    def delete_all(self, user_id: str) -> int:
        """合规：所有 fact 必须能被 user_id 完整清除。"""
        count = 0
        for fact in self.store.all_facts():
            if fact.user_id == user_id and not fact.is_deprecated:
                fact.is_deprecated = True
                count += 1
        return count


def build_app(panel: MemoryPanel):
    """有 fastapi 时挂 REST 路由；缺依赖返回 None。"""
    try:
        from fastapi import FastAPI, HTTPException
    except ImportError:
        print("[api] 未安装 fastapi，跳过 REST 路由。安装：pip install fastapi uvicorn")
        return None

    app = FastAPI(title="Memory Panel API")

    @app.get("/memory/{user_id}")
    def list_memory(user_id: str):
        return {"user_id": user_id, "facts": panel.list_memory(user_id)}

    @app.delete("/memory/{user_id}/{fact_id}")
    def delete_fact(user_id: str, fact_id: str):
        if not panel.delete_fact(user_id, fact_id):
            raise HTTPException(status_code=404, detail="fact not found")
        return {"deleted": fact_id}

    @app.delete("/memory/{user_id}")
    def delete_all(user_id: str):
        return {"deleted_count": panel.delete_all(user_id)}

    return app


def _demo() -> None:
    panel = MemoryPanel(build_demo_store())

    print("GET /memory/u1 —— 用户看到 Agent 记了什么：")
    items = panel.list_memory("u1")
    for item in items:
        print(f"  {item['id']:20s} [{item['type']}] {item['key']}={item['value']}")

    target = items[0]["id"]
    print(f"\nDELETE /memory/u1/{target} —— 用户撤回一条：")
    print(f"  deleted = {panel.delete_fact('u1', target)}")
    print(f"  剩余活跃条数：{len(panel.list_memory('u1'))}")

    print("\nDELETE /memory/u1 —— 合规清空：")
    print(f"  deleted_count = {panel.delete_all('u1')}")
    print(f"  剩余活跃条数：{len(panel.list_memory('u1'))}")

    app = build_app(panel)
    print(f"\nFastAPI 应用：{'已构建' if app else '未构建（离线自测已覆盖同一服务层）'}")


if __name__ == "__main__":
    _demo()
