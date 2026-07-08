# Lab 57 · 守护与自愈

```bash
AM=~/zylos/activity-monitor; DB=~/zylos/comm-bridge/c4.db

# 1. 基本自愈（简历数字 Y）
tmux kill-session -t claude-main && date +%s
pm2 logs activity-monitor --lines 0   # Guardian 检测 → 计数 → 拉起；回来后 date +%s 求差

# 2. 指数退避：连续三次刚起来就 kill-session，看等待 5s→10s→20s；稳定 60s 后回到 5s

# 3. 假死自愈：接 56 篇 SIGSTOP，这次不解冻，看 proc frozen → 杀会话 → 自动拉起

# 4. 故障期体验：把 agent-status.json 的 health 改成 "rate_limited"
#    从微信发消息 → 秒收限流话术；60s 内再发 → 静默（冷却）

# 5. 心跳痕迹
sqlite3 $DB "SELECT id,status,substr(content,1,40) FROM control_queue WHERE content LIKE '%Heartbeat%' ORDER BY id DESC LIMIT 5;"
```
