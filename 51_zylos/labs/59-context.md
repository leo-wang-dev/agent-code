# Lab 59 · 上下文生命周期

```bash
AM=~/zylos/activity-monitor; DB=~/zylos/comm-bridge/c4.db

# 1. 当前水位（Claude）
cat $AM/statusline.json | python3 -c "import json,sys;print(json.load(sys.stdin).get('context_window'))"

# 2. 两级触发（简历数字 N）：喂长材料，盯日志
tail -f $AM/context-monitor.log   # 56% 触发 memory sync → 70% 触发 new-session

# 3. 完整轮换验证接力：轮换前记住一个事实+起后台任务 → 触发轮换
sqlite3 $DB "SELECT substr(content,1,80) FROM conversations WHERE channel='void' ORDER BY id DESC LIMIT 1;"  # 交接摘要
# 新会话起来后问事实+后台任务下落，应无缝接上

# 4. bypass 通道
sqlite3 $DB "SELECT id,bypass_state,substr(content,1,50) FROM control_queue WHERE content LIKE '%new-session%' ORDER BY id DESC LIMIT 3;"

# 5.（Codex）验证 last vs total
tail -c 65536 ~/.codex/sessions/$(date +%Y/%m/%d)/rollout-*.jsonl | grep token_count | tail -1 | python3 -m json.tool
```
