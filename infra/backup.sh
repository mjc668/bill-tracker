#!/usr/bin/env bash
# Bill Tracker postgres backup script.
#
# Usage: chmod +x backup.sh && ./backup.sh
#
# Reads from the environment, falling back to ../.env (the compose .env) when
# present. Only needs pg_dump, gzip and find on PATH.
set -euo pipefail
umask 077

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/../docker-compose.prod.yml"

if [ -f "$SCRIPT_DIR/../.env" ]; then
  # shellcheck disable=SC1091
  set -a
  # shellcheck disable=SC1091
  source "$SCRIPT_DIR/../.env"
  set +a
fi

POSTGRES_USER="${POSTGRES_USER:-paytracker}"
POSTGRES_DB="${POSTGRES_DB:-paytracker}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
BACKUP_KEEP_DAYS="${BACKUP_KEEP_DAYS:-30}"

mkdir -p "$BACKUP_DIR"

BACKUP_FILE="$BACKUP_DIR/paytracker-$(date +%Y%m%d-%H%M%S).sql.gz"
TMP_FILE="$BACKUP_FILE.tmp"

# Never leave a partial archive behind on failure.
cleanup() {
  rm -f "$TMP_FILE"
}
trap cleanup EXIT

docker compose -f "$COMPOSE_FILE" exec -T postgres \
  pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip -9 >"$TMP_FILE"

# Verify the archive before it becomes visible under its final name.
gzip -t "$TMP_FILE"

mv "$TMP_FILE" "$BACKUP_FILE"

find "$BACKUP_DIR" -name 'paytracker-*.sql.gz' -mtime +"$BACKUP_KEEP_DAYS" -delete

echo "Backup written: $BACKUP_FILE"
