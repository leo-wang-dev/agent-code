# Lab 52 · 进程封装

1. 看三层指令模板的拼装关系：
   ```bash
   head -5 ~/zylos/CLAUDE.md     # 生成物
   head -5 ~/zylos/ZYLOS.md      # 核心层（改这里）
   ```
   改 ZYLOS.md 加一行注释 → `zylos runtime claude` 重启 → 看 CLAUDE.md 被重新生成。
2. 验证 spec 文件"阅后即焚"：
   ```bash
   ls /tmp/.zylos-launch-* 2>/dev/null   # 正常永远为空
   ```
3. 大脑的进程树（60 篇判活伏笔）：
   ```bash
   PANE=$(tmux list-panes -t claude-main -F '#{pane_pid}')
   ps -p $PANE -o comm=; pgrep -P $PANE
   ```
4. 尸检报告：`cat ~/zylos/activity-monitor/claude-exit.log`
5. 环境隔离：`tmux show-environment -t claude-main | grep -i anthropic`（应看不到 key）
