#!/usr/bin/env bash
set -euo pipefail
# Ejecutar desde /opt/zero como usuario deploy (o con sudo)
PROJECT_DIR="/opt/zero"
cd "$PROJECT_DIR"

if [ ! -f .env ]; then
  echo ".env no encontrado en $PROJECT_DIR"
  exit 1
fi

echo "Construyendo imagen(es) Docker..."
sudo docker compose build --no-cache

echo "Levantando contenedores..."
sudo docker compose up -d --remove-orphans

echo "Recargando nginx..."
sudo systemctl reload nginx || true

echo "Despliegue completado."
