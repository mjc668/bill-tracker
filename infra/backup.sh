#!/usr/bin/env bash
# Hearthbill SQLite backup script.
#
# Usage: chmod +x backup.sh && ./backup.sh
#
# Takes a WAL-safe snapshot via the SQLite backup API inside the running
# container (never copy the .db file while the app is running), streams it to
# the host and gzips it. Reads BACKUP_DIR/BACKUP_KEEP_DAYS from the
# environment, falling back to ../.env (the compose .env) when present.
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

BACKUP_DIR="${BACKUP_DIR:-./backups}"
BACKUP_KEEP_DAYS="${BACKUP_KEEP_DAYS:-30}"

mkdir -p "$BACKUP_DIR"

BACKUP_FILE="$BACKUP_DIR/hearthbill-$(date +%Y%m%d-%H%M%S).db.gz"
TMP_FILE="$BACKUP_FILE.tmp"
TMP_DB="/tmp/hearthbill-backup.db"

# Never leave a partial archive behind on failure.
cleanup() {
  rm -f "$TMP_FILE"
  docker compose -f "$COMPOSE_FILE" exec -T app rm -f "$TMP_DB" 2>/dev/null || true
}
trap cleanup EXIT

docker compose -f "$COMPOSE_FILE" exec -T app python - "$TMP_DB" <<'PY'
import sqlite3
import sys

source = sqlite3.connect("/data/hearthbill.db")
target = sqlite3.connect(sys.argv[1])
with target:
    source.backup(target)
target.close()
source.close()
PY

docker compose -f "$COMPOSE_FILE" exec -T app cat "$TMP_DB" | gzip -9 >"$TMP_FILE"

# Verify the archive before it becomes visible under its final name.
gzip -t "$TMP_FILE"

mv "$TMP_FILE" "$BACKUP_FILE"

find "$BACKUP_DIR" -name 'hearthbill-*.db.gz' -mtime +"$BACKUP_KEEP_DAYS" -delete

echo "Backup written: $BACKUP_FILE"
