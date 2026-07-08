-- =====================================================================
-- LLMOps 平台核心数据库 Schema —— 16 张表（PostgreSQL 16 + pgvector）
-- 对应文章第 46 篇 四、数据库 schema 设计。
--
-- 说明：
--   - VECTOR(1024) 需要 pgvector 扩展；纯 PG 环境请注释掉相关列/索引。
--   - 建库：CREATE EXTENSION IF NOT EXISTS vector;
--   - 迁移管理见 alembic/（本文件是权威 DDL 参照，迁移与之保持一致）。
-- =====================================================================

CREATE EXTENSION IF NOT EXISTS vector;

-- 1. 租户 -------------------------------------------------------------
CREATE TABLE tenants (
    id         BIGSERIAL PRIMARY KEY,
    name       VARCHAR(100) NOT NULL,
    plan       VARCHAR(20),                       -- free / pro / enterprise
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. 用户 -------------------------------------------------------------
CREATE TABLE users (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       BIGINT REFERENCES tenants(id),
    email           VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255),
    role            VARCHAR(20),                   -- admin / user / viewer
    status          VARCHAR(20) DEFAULT 'active',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_users_tenant ON users(tenant_id);

-- 3. Agent 配置 -------------------------------------------------------
CREATE TABLE agents (
    id          BIGSERIAL PRIMARY KEY,
    tenant_id   BIGINT REFERENCES tenants(id),
    name        VARCHAR(100) NOT NULL,
    description TEXT,
    system_prompt TEXT,
    model       VARCHAR(50),
    temperature FLOAT DEFAULT 0.2,
    tools       JSONB,                             -- 工具列表
    config      JSONB,                             -- 其他配置
    is_active   BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_agents_tenant ON agents(tenant_id);

-- 4. 会话 -------------------------------------------------------------
CREATE TABLE sessions (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id        BIGINT REFERENCES users(id),
    agent_id       BIGINT REFERENCES agents(id),
    tenant_id      BIGINT NOT NULL,
    title          VARCHAR(200),
    metadata       JSONB,
    created_at     TIMESTAMPTZ DEFAULT NOW(),
    last_active_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_sessions_user ON sessions(user_id);

-- 5. 消息 -------------------------------------------------------------
CREATE TABLE messages (
    id           BIGSERIAL PRIMARY KEY,
    session_id   UUID REFERENCES sessions(id),
    role         VARCHAR(20),                      -- user / assistant / system / tool
    content      TEXT,
    tool_calls   JSONB,
    tool_call_id VARCHAR(100),
    tokens_used  JSONB,                            -- {input: N, output: M}
    cost_usd     NUMERIC(10, 6),
    latency_ms   INTEGER,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_messages_session ON messages(session_id, created_at);

-- 6. 审计日志（写入频繁，独立表）--------------------------------------
CREATE TABLE audit_logs (
    id              BIGSERIAL PRIMARY KEY,
    trace_id        VARCHAR(100),
    user_id         BIGINT,
    tenant_id       BIGINT,
    agent_id        BIGINT,
    action          VARCHAR(50),                   -- tool_call / llm_call / approval
    target_resource VARCHAR(200),
    details         JSONB,
    outcome         VARCHAR(20),                   -- success / failure / blocked
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_audit_trace ON audit_logs(trace_id);
CREATE INDEX idx_audit_user_time ON audit_logs(user_id, created_at);

-- 7. Memory L1 用户档案 -----------------------------------------------
CREATE TABLE user_profiles (
    user_id    BIGINT PRIMARY KEY REFERENCES users(id),
    fields     JSONB,                              -- {name, age, occupation, ...}
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 8. Memory L2 偏好（向量库）------------------------------------------
CREATE TABLE memory_preferences (
    id         BIGSERIAL PRIMARY KEY,
    user_id    BIGINT NOT NULL,
    content    TEXT,
    embedding  VECTOR(1024),
    importance FLOAT DEFAULT 0.5,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_pref_user_emb ON memory_preferences
    USING ivfflat (embedding vector_cosine_ops);

-- 9. Memory L3 事件层 -------------------------------------------------
CREATE TABLE memory_episodes (
    id          BIGSERIAL PRIMARY KEY,
    user_id     BIGINT NOT NULL,
    content     TEXT,
    embedding   VECTOR(1024),
    occurred_at TIMESTAMPTZ,
    expires_at  TIMESTAMPTZ,
    importance  FLOAT DEFAULT 0.5,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_episode_user ON memory_episodes(user_id);

-- 10. Memory L4 分层摘要（对齐第 43 篇对话历史分层摘要）---------------
CREATE TABLE memory_summaries (
    id         BIGSERIAL PRIMARY KEY,
    session_id UUID REFERENCES sessions(id),
    layer      SMALLINT,                           -- 1 / 2 / 3 层
    summary    TEXT,
    round_lo   INTEGER,
    round_hi   INTEGER,
    tokens     INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_summary_session ON memory_summaries(session_id, layer);

-- 11. Token 计费明细 --------------------------------------------------
CREATE TABLE token_usage (
    id            BIGSERIAL PRIMARY KEY,
    trace_id      VARCHAR(100),
    user_id       BIGINT,
    tenant_id     BIGINT,
    agent_id      BIGINT,
    model         VARCHAR(50),
    input_tokens  INTEGER,
    output_tokens INTEGER,
    cost_usd      NUMERIC(10, 6),
    cached        BOOLEAN DEFAULT FALSE,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_usage_user_time ON token_usage(user_id, created_at);
CREATE INDEX idx_usage_tenant_time ON token_usage(tenant_id, created_at);

-- 12. API Key（第三方/程序化访问）------------------------------------
CREATE TABLE api_keys (
    id          BIGSERIAL PRIMARY KEY,
    tenant_id   BIGINT REFERENCES tenants(id),
    user_id     BIGINT REFERENCES users(id),
    name        VARCHAR(100),
    key_hash    VARCHAR(255) NOT NULL,             -- 只存哈希，不存明文
    scopes      JSONB,
    last_used_at TIMESTAMPTZ,
    revoked     BOOLEAN DEFAULT FALSE,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_apikey_hash ON api_keys(key_hash);

-- 13. 评测运行 --------------------------------------------------------
CREATE TABLE eval_runs (
    id         BIGSERIAL PRIMARY KEY,
    tenant_id  BIGINT,
    agent_id   BIGINT,
    dataset    VARCHAR(100),
    pass_rate  FLOAT,
    metrics    JSONB,                              -- {faithfulness, precision, ...}
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_evalrun_agent ON eval_runs(agent_id, created_at);

-- 14. 评测用例（含 bad case 回归集）----------------------------------
CREATE TABLE eval_cases (
    id          BIGSERIAL PRIMARY KEY,
    run_id      BIGINT REFERENCES eval_runs(id),
    question    TEXT,
    expected    TEXT,
    actual      TEXT,
    score       FLOAT,
    is_bad_case BOOLEAN DEFAULT FALSE,
    category    VARCHAR(50),                       -- rag_miss / prompt_gap / tool_fail / ...
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_evalcase_run ON eval_cases(run_id);

-- 15. 语义缓存（对齐第 44 篇）-----------------------------------------
CREATE TABLE semantic_cache (
    id         BIGSERIAL PRIMARY KEY,
    tenant_id  BIGINT,
    query      TEXT,
    embedding  VECTOR(1024),
    response   TEXT,
    model      VARCHAR(50),
    hit_count  INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_cache_tenant_emb ON semantic_cache
    USING ivfflat (embedding vector_cosine_ops);

-- 16. 安全事件（对齐第 40-42 篇防御层）-------------------------------
CREATE TABLE security_events (
    id          BIGSERIAL PRIMARY KEY,
    tenant_id   BIGINT,
    user_id     BIGINT,
    event_type  VARCHAR(50),                       -- prompt_injection / guardrail / hitl
    severity    VARCHAR(20),                       -- low / medium / high
    detail      JSONB,
    handled     BOOLEAN DEFAULT FALSE,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_secevent_tenant_time ON security_events(tenant_id, created_at);

-- 种子数据（演示用）--------------------------------------------------
INSERT INTO tenants (name, plan) VALUES ('Demo Tenant', 'pro');
INSERT INTO users (tenant_id, email, hashed_password, role)
    VALUES (1, 'demo@example.com', 'pbkdf2$...', 'admin');
INSERT INTO agents (tenant_id, name, model) VALUES (1, '客服 Agent', 'gpt-4o');
