# Lab 56 · 感知层

```bash
AM=~/zylos/activity-monitor

# 1. 工具事件流瀑布
tail -f $AM/tool-events.jsonl   # 另开窗口给员工发任务，看 prompt→pre_tool→post_tool→stop

# 2. 四路信号全览
cat $AM/agent-status.json $AM/proc-state.json $AM/api-activity.json $AM/statusline.json

# 3. 保质期机制
pm2 stop activity-monitor; sleep 6; stat -c '%y' $AM/agent-status.json
# 此刻发消息 → dispatcher 视 agent 为 offline，排队不投
pm2 start activity-monitor   # 恢复后积压投递

# 4. 假死检测现杀
PANE=$(tmux list-panes -t claude-main -F '#{pane_pid}'); PID=$(pgrep -P $PANE | head -1)
kill -STOP $PID
watch -n 5 cat $AM/proc-state.json   # lastDelta 归零 → ~60s 后 frozen:true
kill -CONT $PID   # 解冻（或留给 57 篇守护者动手）

# 5. 成本账本
cat $AM/cost-log.jsonl
```
