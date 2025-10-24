#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="/opt/zero"
cd "$PROJECT_DIR"

echo "Actualizando código desde origin/main..."
git fetch --all --prune
git reset --hard origin/main

echo "Parando contenedores actuales (si existen) y actualizando imágenes..."
docker compose pull || true
docker compose build

echo "Levantando contenedores actualizados..."
docker compose up -d --remove-orphans

echo "Limpieza de imágenes colgantes..."
docker image prune -f || true

echo "Update completado."
