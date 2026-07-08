#!/bin/bash
# 数据备份脚本 —— 对应文章第 47 篇 五、数据备份和灾难恢复。
# 配合 cron: 0 2 * * * /app/deploy/backup.sh
set -euo pipefail

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=${BACKUP_DIR:-/backups}
S3_BUCKET=${S3_BUCKET:-agent-platform-backups}
ALERT_WEBHOOK=${ALERT_WEBHOOK:-}

mkdir -p "$BACKUP_DIR"

# 1. PostgreSQL 全量备份（gzip）
docker compose exec -T postgres pg_dump -U agent agent_platform \
    | gzip > "$BACKUP_DIR/db_$DATE.sql.gz"

# 2. 上传到对象存储（S3 / OSS）—— 未配置 aws 时跳过
if command -v aws >/dev/null 2>&1; then
    aws s3 cp "$BACKUP_DIR/db_$DATE.sql.gz" "s3://$S3_BUCKET/db/$DATE/"
fi

# 3. 清理 30 天前的本地备份
find "$BACKUP_DIR" -name "db_*.sql.gz" -mtime +30 -delete

# 4. 成功告警
if [ -n "$ALERT_WEBHOOK" ]; then
    curl -fsS -X POST "$ALERT_WEBHOOK" \
        -H 'Content-Type: application/json' \
        -d "{\"text\":\"Backup completed: db_$DATE.sql.gz\"}" || true
fi

echo "backup done: $BACKUP_DIR/db_$DATE.sql.gz"
