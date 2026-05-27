#!/usr/bin/env bash
# restart.sh — Restart paper-library services in dependency order.
#
# Usage (inside LXC or via pct exec):
#   bash /opt/paper-library/deploy/restart.sh

set -euo pipefail

MONGO_PORT=27017
API_PORT=8000

log() { echo "[restart] $*"; }
die() { echo "[restart] ERROR: $*" >&2; exit 1; }

# ─── mongod ───────────────────────────────────────────────────────────────────
log "Restarting mongod ..."
systemctl restart mongod

log "Waiting for MongoDB on port ${MONGO_PORT} ..."
for i in $(seq 1 15); do
  mongosh --quiet --eval "db.adminCommand('ping')" > /dev/null 2>&1 && break
  sleep 2
  if [[ "$i" -eq 15 ]]; then
    die "MongoDB did not come up after restart."
  fi
done
log "MongoDB READY."

# ─── paper-library ────────────────────────────────────────────────────────────
log "Restarting paper-library ..."
systemctl restart paper-library

log "Waiting for paper-library API on port ${API_PORT} ..."
for i in $(seq 1 15); do
  curl -sf "http://127.0.0.1:${API_PORT}/health" > /dev/null 2>&1 && break
  sleep 2
  if [[ "$i" -eq 15 ]]; then
    die "paper-library did not come up after restart."
  fi
done
log "paper-library READY."

log "All services restarted successfully."
