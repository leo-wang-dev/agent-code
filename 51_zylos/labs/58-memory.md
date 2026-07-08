# Lab 58 · 记忆系统

```bash
M=~/zylos/memory

# 1. 看员工现在记得什么
cat $M/state.md $M/references.md; ls -la $M/reference/ $M/users/

# 2. 触发一次 Memory Sync（聊 >15 条，或直接让它"做一次记忆同步"）
sqlite3 ~/zylos/comm-bridge/c4.db "SELECT id,end_conversation_id,substr(summary,1,60) FROM checkpoints ORDER BY id DESC LIMIT 3;"
diff <(git -C $M show HEAD:state.md 2>/dev/null) $M/state.md

# 3. "新会话还认识你"：告诉它一个新事实 → 同步 → /clear → 问它
# 4. git 审计层
git -C $M log --oneline | head
# 5. 体检 + 遗忘
node ~/zylos/.claude/skills/zylos-memory/scripts/memory-status.js
node ~/zylos/.claude/skills/zylos-memory/scripts/consolidate.js | python3 -m json.tool | head -40
```
