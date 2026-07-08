# 04 · Memory 不存在，你只是在伪造历史

对应文章《Memory 不存在，你只是在伪造历史》（系列第 04 篇）。

记忆不在模型里，在你的代码和数据库里。所谓"记忆"，本质是客户端在每次请求里伪造的一段上下文。每个文件对应文章一节，全部离线可跑、确定性输出。

## 产物 → 文件 → 运行命令

| 文章对应 | 产物 | 文件 | 运行命令 |
|---|---|---|---|
| §一 无状态 API | 纯函数 f(messages) + "忘塞历史=记忆从未存在" | `stateless_memory.py` | `python3 stateless_memory.py` |
| §二 短时记忆三形态 | 完整历史 / 滑动窗口 / 摘要压缩 并排翻车对比 | `short_term_strategies.py` | `python3 short_term_strategies.py` |
| §二 分层混合 | Hierarchical Memory 三层组装 + 预算裁剪 | `layered_memory.py` | `python3 layered_memory.py` |
| §三 Token 预算管理 | 预算表 + 主动裁剪（而非被动报错） | `token_budget_planner.py` | `python3 token_budget_planner.py` |
| §四 长时记忆 | 检索式记忆（写入/读取双路径，本质是 RAG） | `long_term_retrieval.py` | `python3 long_term_retrieval.py` |
| §五 生产坑 | 并发/污染/漂移/冷启动/迁移 五坑防御 | `production_pitfalls.py` | `python3 production_pitfalls.py` |
| 汇总 | LayeredMemory 一把跑 | `run_demo.py` | `python3 run_demo.py` |

## 一次跑全部

```bash
for f in stateless_memory short_term_strategies layered_memory token_budget_planner long_term_retrieval production_pitfalls; do
  echo "===== $f ====="; python3 "$f.py"; echo
done
```

## 复用的核心实现

复用 `src/agent_code/memory_essence.py`：`BufferMemory` / `WindowMemory` / `SummaryMemory`（短时三形态）、`LayeredMemory`（分层）、`VectorMemory` + `extract_candidate_facts`（长时检索）、`fit_messages_to_budget` / `budget_breakdown`（预算管理）。

> 长时记忆的检索走词频余弦，命中演示用英文事实；短时记忆演示用中文对话。
