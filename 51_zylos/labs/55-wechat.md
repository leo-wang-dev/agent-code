# Lab 55 · 微信接入（务必用小号）

```bash
# 1. 安装 + 扫码登录
zylos add wechat
cd ~/zylos/.claude/skills/wechat && npm run admin -- login   # 终端出二维码，小号扫

# 2. 端到端首航：另一个微信给小号发"在吗"
pm2 logs zylos-wechat      # 入站
pm2 logs c4-dispatcher     # 投递；注意手机上的"对方正在输入…"

# 3. 会话令牌仓
cat ~/zylos/components/wechat/context-tokens.json | python3 -m json.tool | head

# 4. 直调出站契约（endpoint 从日志抄）
echo "直调渠道脚本发出的" | node ~/zylos/.claude/skills/wechat/scripts/send.js "<acct>|to:<user>"

# 5. 发图
echo "[MEDIA:image]/tmp/test.png" | node .../scripts/send.js "<acct>|to:<user>"

# 6. 断线自愈：断网 2 分钟再恢复，看 poller 2s 重试 → 30s 退避 → 游标续传

# 7.（简历数字 Z）微信问答往返 P95：20 次计时取分位
```
