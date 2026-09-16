#!/usr/bin/env bash
# Nightly backup: Postgres dump + resumes archive, copied offsite, 14-day local retention.
# Add to root's crontab: 30 2 * * * /opt/job-bot/deploy/backup.sh >> /var/log/jobbot-backup.log 2>&1
set -euo pipefail

STAMP=$(date +%F)
DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="/opt/backups"

mkdir -p "$BACKUP_DIR"
cd "$DEPLOY_DIR"

docker compose exec -T postgres pg_dump -U jobbot jobbot | gzip > "$BACKUP_DIR/jobbot-$STAMP.sql.gz"

RESUMES_VOLUME="deploy_resumes"
tar -czf "$BACKUP_DIR/resumes-$STAMP.tar.gz" -C "/var/lib/docker/volumes/$RESUMES_VOLUME/_data" .

# Offsite copy - configure rclone first: `rclone config` (Google Drive / S3 / Backblaze etc).
if command -v rclone >/dev/null 2>&1; then
    rclone copy "$BACKUP_DIR" remote:jobbot-backups --max-age 24h
fi

find "$BACKUP_DIR" -type f -mtime +14 -delete

echo "Backup complete: $STAMP"
