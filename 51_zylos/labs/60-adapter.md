# Lab 60 · RuntimeAdapter

```bash
# 1. 切换运行时全链路验证
cat ~/.zylos/config.json          # 看 runtime 字段
zylos runtime codex               # 或 claude —— 只改一个字段
tmux ls                           # 会话名随之切换 claude-main ↔ codex-main

# 2. 读判活逻辑（对照文章）
# zylos-core/cli/lib/runtime/claude.js:164  与  codex.js:166 的 isRunning()

# 3.（进阶作业）照 index.js 的 REGISTRY，给第三种 CLI Agent 写 adapter 骨架：
#    实现 base.js 的 8 个方法（launch/stop/isRunning/checkAuth/...），注册进 REGISTRY。
```
