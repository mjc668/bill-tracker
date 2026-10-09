#!/usr/bin/env bash
# Platybill container entrypoint.
#
# Runs the app as a single container: permission setup, JWT secret
# persistence, a pre-migration SQLite backup, Alembic migrations and then
# supervisord (uvicorn + Next standalone).
#
# Two modes:
#   * root (Unraid / plain docker run): honors PUID/PGID, chowns /data and
#     drops privileges for the supervised processes.
#   * non-root (hardened compose `user:`): uses the current user as-is.
set -euo pipefail

DATA_DIR="${DATA_DIR:-/data}"
DB_PATH="${DB_PATH:-$DATA_DIR/platybill.db}"
BACKUP_DIR="$DATA_DIR/backups"
BACKUP_KEEP="${BACKUP_KEEP:-10}"
APP_USER="appuser"
VENV="/backend/.venv"

log() { printf '[platybill] %s\n' "$*"; }

mkdir -p "$DATA_DIR" "$BACKUP_DIR" 2>/dev/null || {
  log "ERROR: cannot create $DATA_DIR — check the volume permissions"
  log "       (bind mounts: chown to PUID/PGID, or 10001:10001 for compose)"
  exit 1
}

RUN_AS=()
SUPERVISOR_USER=""
TARGET_UID="$(id -u)"
TARGET_GID="$(id -g)"

if [ "$TARGET_UID" -eq 0 ]; then
  PUID="${PUID:-10001}"
  PGID="${PGID:-10001}"
  if [ "$PUID" -eq 0 ] || [ "$PGID" -eq 0 ]; then
    log "ERROR: refusing to run as root (PUID/PGID must not be 0)"
    exit 1
  fi
  # -o allows sharing a uid/gid that already exists (e.g. Unraid's 99/100).
  groupmod -o -g "$PGID" "$APP_USER" 2>/dev/null || true
  usermod -o -u "$PUID" -g "$PGID" "$APP_USER" 2>/dev/null || true
  chown -R "$PUID:$PGID" "$DATA_DIR" /frontend/.next
  RUN_AS=(setpriv --reuid "$PUID" --regid "$PGID" --clear-groups)
  SUPERVISOR_USER="user=$APP_USER"
  TARGET_UID="$PUID"
  TARGET_GID="$PGID"
fi

# --- JWT secret: env wins, otherwise generate once and persist in /data ---
SECRET_FILE="$DATA_DIR/jwt_secret"
if [ -z "${JWT_SECRET:-}" ]; then
  if [ ! -s "$SECRET_FILE" ]; then
    log "JWT_SECRET not set — generating one and storing it at $SECRET_FILE"
    (umask 077; head -c 48 /dev/urandom | base64 | tr -d '\n' >"$SECRET_FILE")
  fi
  JWT_SECRET="$(cat "$SECRET_FILE")"
  export JWT_SECRET
fi
if [ "$(id -u)" -eq 0 ]; then
  chown "$TARGET_UID:$TARGET_GID" "$SECRET_FILE" 2>/dev/null || true
fi

# --- Pre-migration backup: WAL-safe snapshot via the SQLite backup API ---
if [ -s "$DB_PATH" ]; then
  BACKUP_FILE="$BACKUP_DIR/pre-upgrade-$(date -u +%Y%m%d-%H%M%S).db"
  log "Backing up database to $BACKUP_FILE"
  "$VENV/bin/python" - "$DB_PATH" "$BACKUP_FILE" <<'PY'
import sqlite3
import sys

source = sqlite3.connect(sys.argv[1])
target = sqlite3.connect(sys.argv[2])
with target:
    source.backup(target)
target.close()
source.close()
PY
  if [ "$(id -u)" -eq 0 ]; then
    chown "$TARGET_UID:$TARGET_GID" "$BACKUP_FILE" 2>/dev/null || true
  fi
  # Keep only the newest BACKUP_KEEP pre-upgrade files.
  # shellcheck disable=SC2012  # filenames are controlled by this script
  ls -1t "$BACKUP_DIR"/pre-upgrade-*.db 2>/dev/null |
    tail -n "+$((BACKUP_KEEP + 1))" |
    xargs -r rm -f
fi

log "Running database migrations"
cd /backend
if [ "${#RUN_AS[@]}" -gt 0 ]; then
  "${RUN_AS[@]}" "$VENV/bin/alembic" upgrade head
else
  "$VENV/bin/alembic" upgrade head
fi

# --- supervisord: uvicorn on loopback, Next on the public port ---
SUPERVISOR_CONF="/tmp/supervisord.conf"
{
  cat <<'EOF'
[supervisord]
nodaemon=true
logfile=/dev/null
logfile_maxbytes=0
pidfile=/tmp/supervisord.pid

[program:backend]
command=/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8010
directory=/backend
autorestart=true
priority=10
stopsignal=TERM
stopasgroup=true
killasgroup=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0
EOF
  if [ -n "$SUPERVISOR_USER" ]; then echo "$SUPERVISOR_USER"; fi
  cat <<'EOF'

[program:frontend]
command=/usr/local/bin/node /frontend/server.js
directory=/frontend
environment=HOSTNAME="0.0.0.0",PORT="3010",NODE_ENV="production"
autorestart=true
priority=20
stopsignal=TERM
stopasgroup=true
killasgroup=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0
EOF
  if [ -n "$SUPERVISOR_USER" ]; then echo "$SUPERVISOR_USER"; fi
} >"$SUPERVISOR_CONF"

log "Starting Platybill on port 3010"
exec supervisord -c "$SUPERVISOR_CONF"
