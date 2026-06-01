#!/usr/bin/env bash
# update.sh — Pull latest code, reinstall deps, and restart services.
#
# Usage (inside LXC or via pct exec):
#   bash /opt/paper-library/deploy/update.sh

set -euo pipefail

INSTALL_DIR="/opt/paper-library"
VENV_DIR="/opt/paper-library-env"
API_PORT=8000
MONGO_PORT=27017

log() { echo "[update] $*"; }
die() { echo "[update] ERROR: $*" >&2; exit 1; }

# ─── Capture pre-update version ──────────────────────────────────────────────
OLD_VERSION="$(grep '^VERSION_NAME=' "${INSTALL_DIR}/VERSION.md" 2>/dev/null | cut -d= -f2 || echo 'unknown')"

# ─── Peek at the incoming version without applying it ─────────────────────────
REMOTE_VERSION="$(git -C "${INSTALL_DIR}" fetch --quiet origin 2>/dev/null; \
  git -C "${INSTALL_DIR}" show origin/HEAD:VERSION.md 2>/dev/null \
  | grep '^VERSION_NAME=' | cut -d= -f2 || echo 'unknown')"

echo ""
echo "  Current : ${OLD_VERSION}"
echo "  Incoming: ${REMOTE_VERSION}"
echo ""
read -r -p "  Proceed with update? [Y/n] " _confirm
case "${_confirm}" in
  [nN]|[nN][oO]) echo "[update] Aborted."; exit 0 ;;
  *) ;;
esac
echo ""

# ─── Pull latest code ─────────────────────────────────────────────────────────
log "Pulling latest code in ${INSTALL_DIR} ..."
git -C "${INSTALL_DIR}" pull --ff-only

# ─── Ensure data directories exist with correct ownership ────────────────────
log "Ensuring data directories ..."
mkdir -p "${INSTALL_DIR}/pdf" "${INSTALL_DIR}/venues" "${INSTALL_DIR}/strategies" "${INSTALL_DIR}/tasks"
chown paperuser:paperuser "${INSTALL_DIR}/pdf" "${INSTALL_DIR}/venues" "${INSTALL_DIR}/strategies" "${INSTALL_DIR}/tasks"

# ─── Reinstall dependencies ───────────────────────────────────────────────────
log "Installing Python dependencies ..."
"${VENV_DIR}/bin/pip" install --quiet --upgrade pip
"${VENV_DIR}/bin/pip" install --quiet -r "${INSTALL_DIR}/requirements.txt"

# ─── Reload systemd and restart services ─────────────────────────────────────
log "Reloading systemd daemon ..."
systemctl daemon-reload

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

log "Restarting paper-library ..."
systemctl restart paper-library

log "Waiting for paper-library API on port ${API_PORT} ..."
for i in $(seq 1 15); do
  curl -sf "http://127.0.0.1:${API_PORT}/health" > /dev/null 2>&1 && break
  sleep 2
  if [[ "$i" -eq 15 ]]; then
    die "paper-library did not come up after update."
  fi
done
log "paper-library READY."

# ─── Version diff ─────────────────────────────────────────────────────────────
NEW_VERSION="$(grep '^VERSION_NAME=' "${INSTALL_DIR}/VERSION.md" 2>/dev/null | cut -d= -f2 || echo 'unknown')"
log ""
log "=== Update complete ==="
log "  ${OLD_VERSION}  →  ${NEW_VERSION}"
