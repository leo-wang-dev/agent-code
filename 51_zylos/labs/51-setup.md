# Lab 51 · 环境准备与首次启动验证

目标：装好 zylos，感受"它活着"。

## 步骤
1. 安装（会装齐依赖并跑 `zylos init`）：
   ```bash
   curl -fsSL https://raw.githubusercontent.com/zylos-ai/zylos-core/main/scripts/install.sh | bash
   ```
2. 围观大脑（只读，`Ctrl-b d` 退出）：
   ```bash
   tmux attach -t claude-main
   ```
3. 看神经系统（4 个常驻服务）：
   ```bash
   pm2 list        # scheduler / web-console / c4-dispatcher / activity-monitor
   ```
4. 发第一条消息：浏览器打开 web 控制台（默认 127.0.0.1:3456；远程机用 `ssh -L 3456:127.0.0.1:3456` 转发）聊一句。

三步都通 = 你的数字员工已经活了。
