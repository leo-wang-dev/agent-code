# Lab 54 · 投递引擎

```bash
# 1. 肉眼看一次完整投递
tmux attach -t claude-main   # 一个窗口围观
# 另一窗口注入多行消息，观察整段粘贴 → 回车 → 提交
node ~/zylos/.claude/skills/comm-bridge/scripts/c4-receive.js \
  --channel web-console --endpoint lab --content "第一行
第二行——多行也是一次粘贴"

# 2. 忙时不投：先让大脑跑长任务，任务中注入消息
pm2 logs c4-dispatcher --lines 50   # 看到 claim → release，直到空闲才投

# 3. 光标判定现场
tmux display-message -p -t claude-main '#{cursor_x} #{cursor_y}'   # 空框 cursor_x=2

# 4. 心跳代签日志
grep -i "auto-ack" ~/.pm2/logs/c4-dispatcher-out.log | tail -5

# 5.（简历数字）端到端投递 P95：多次计时 c4-receive 到 dispatcher "delivered"
```
