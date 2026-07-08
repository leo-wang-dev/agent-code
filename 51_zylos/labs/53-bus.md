# Lab 53 · 消息总线 C4

```bash
DB=~/zylos/comm-bridge/c4.db
R=~/zylos/.claude/skills/comm-bridge/scripts

# 1. 手工注入一条消息，全链路观察
node $R/c4-receive.js --channel web-console --endpoint lab-test --content "你好，报个到"
sqlite3 $DB "SELECT id,direction,channel,status,substr(content,1,30) FROM conversations ORDER BY id DESC LIMIT 3;"

# 2. 双队列状态
sqlite3 $DB "SELECT id,priority,status,substr(content,1,40) FROM control_queue ORDER BY id DESC LIMIT 5;"

# 3. 验证"投递时拼 suffix"——库里存裸内容
sqlite3 $DB "SELECT content FROM conversations WHERE direction='in' ORDER BY id DESC LIMIT 1;"
# 对比 tmux attach 里大脑实际收到的（带 ---- reply via: ...）

# 4. 大消息落盘
node $R/c4-receive.js --channel web-console --endpoint lab-test --content "$(python3 -c 'print("长"*3000)')"
ls ~/zylos/comm-bridge/attachments/

# 5. void 渠道
echo "给未来自己的备忘" | node $R/c4-send.js void lab-note
sqlite3 $DB "SELECT channel,endpoint_id,substr(content,1,20) FROM conversations WHERE channel='void';"
```
