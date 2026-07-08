# 47 · 全栈 LLMOps 平台：Vue3 + ECharts + Docker

配套文章：《全栈 LLMOps 平台：Vue3 + ECharts 监控大盘 + Docker 部署》（系列第 47 篇）。

前端为**完整真实源码**（未构建，需 `npm install && npm run build`）；部署套件与
第三方适配器为可交付配置/脚本；Python 适配器离线可跑（含 AES 往返自测）。

## 文章"包含"清单 → 文件对照

| 文章承诺的产物 | 位置 |
|---|---|
| 完整 Vue3 + Tailwind + ECharts 前端 | `frontend/`（package.json/vite/tailwind/tsconfig + src/{views,components,charts,api,router,stores}） |
| 监控大盘 5 大面板组件 | `frontend/src/components/charts/`：RealtimeMetrics / CostBreakdown / LatencyPerformance / QualityMonitor / SecurityAlerts |
| 完整 docker-compose 部署套件 | `deploy/docker-compose.yml` + `Dockerfile.backend` + `Dockerfile.frontend` + `litellm_config.yaml` + `.env.example` |
| Nginx + SSL 配置模板（含 SSE 透传） | `deploy/nginx.conf` |
| 微信公众号 / 企业微信适配器 | `integrations/wechat.py`（签名+明文收发） / `integrations/wecom.py`（AES 加密回调） |
| 备份脚本 | `deploy/backup.sh` |

## 前端文件树（真实完整源码，不构建）

```
frontend/
├── package.json  vite.config.ts  tailwind.config.js  postcss.config.js  tsconfig.json  index.html
└── src/
    ├── main.ts  App.vue  style.css
    ├── router/index.ts
    ├── stores/{auth,chat}.ts
    ├── api/{client,auth,agent,chat,analytics}.ts
    ├── views/{auth/Login, chat/Chat, agents/Agents, analytics/Analytics, admin/Admin}.vue
    └── components/
        ├── chat/MessageContent.vue          # Markdown + 代码高亮 + DOMPurify 防 XSS
        └── charts/{RealtimeMetrics,CostBreakdown,LatencyPerformance,QualityMonitor,SecurityAlerts}.vue
```

## 离线可验证部分

```bash
python3 integrations/demo_adapters.py   # 微信公众号 + 企业微信 收发/验签/AES 往返自测
bash -n deploy/backup.sh                # 备份脚本语法检查
```

## 构建/部署（需 node + docker）

```bash
cd frontend && npm install && npm run build      # 前端产物
cd ../deploy && cp .env.example .env             # 填密钥
docker compose --env-file .env up -d
docker compose exec backend alembic upgrade head
```

## 生产替换点

- 前端 `analytics` 面板在后端未接通时用占位数据；接通 `/api/v1/analytics/dashboard` 后走真实数据。
- `wechat.py` 为明文模式；生产若开安全模式需接入 AES（参考 `wecom.py`）。
- `wecom.py` 的 `encrypt_message` 仅用于自测往返；生产只需 `decrypt_message` + 验签（加密由企业微信服务器完成）。
