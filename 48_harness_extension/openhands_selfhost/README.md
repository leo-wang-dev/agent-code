# OpenHands 自部署

对应文章第 48 篇 二/三节：把通用 Harness 自部署后挂自定义工具 + prompt 当应用骨架。

## 启动

```bash
export LLM_API_KEY=sk-...          # 或指向自建 Gateway
docker compose up -d
# 浏览器打开 http://localhost:3000
```

## 关键接线点（文章 五、Fork 改造点）

1. **自定义工具**：把 `openhands_tools.py`（上级目录）里的领域工具注册进 OpenHands。
2. **system prompt**：注入用户身份/偏好。
3. **限制默认能力**：按需移除 shell 执行等高危工具。
4. **接自己的 UI / SSE 端点**。
5. **storage 层接 PostgreSQL**（替代默认 SQLite）。

## per-user 部署

给每个高价值用户起一个独立实例（不同 workspace 卷 + 不同环境变量）。
实例生命周期编排见上级目录 `per_user_orchestrator.py`（mock 演示，生产用 K8s）。

## 注意

- 镜像 tag 随上游演进较快，部署前对照官方 releases。
- Fork 维护成本高（文章 六、成本1）：约 1 名工程师 30-40% 时间。若要深度改造，
  优先考虑 DeepAgents SDK + 自定义 Middleware（见上级 `deepagents_middleware.py`）。
