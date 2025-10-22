#!/usr/bin/env bash
# Backup simple: copia zero.db y user_uploads a /opt/zero/backups/YYYY-MM-DD/
set -euo pipefail

PROJECT_DIR="/opt/zero"
BACKUP_ROOT="/opt/zero/backups"
DATE=$(date +%F)
DEST="${BACKUP_ROOT}/${DATE}"
mkdir -p "${DEST}"
echo "Backing up to ${DEST}"

# Ajusta ruta de DB si es distinta
if [ -f "${PROJECT_DIR}/zero.db" ]; then
  cp "${PROJECT_DIR}/zero.db" "${DEST}/zero.db"
fi

rsync -a --delete "${PROJECT_DIR}/user_uploads/" "${DEST}/user_uploads/"

# Mantener 30 días
find "${BACKUP_ROOT}" -maxdepth 1 -type d -mtime +30 -exec rm -rf {} \;

echo "Backup completado."
