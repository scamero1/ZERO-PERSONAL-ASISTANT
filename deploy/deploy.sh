#!/usr/bin/env bash
# Deploy script para /opt/zero
set -euo pipefail

PROJECT_DIR="/opt/zero"
echo "Deploy: entrando en $PROJECT_DIR"
cd "$PROJECT_DIR"

# asegurarse de que .env existe
if [ ! -f .env ]; then
  echo ".env no encontrado en $PROJECT_DIR — crea .env a partir de .env.example"
  exit 1
fi

echo "Actualizando código (si es git repo)..."
if [ -d .git ]; then
  git fetch --all --prune
  git reset --hard origin/main || git reset --hard origin/master || true
fi

echo "Construyendo imágenes Docker..."
sudo docker compose build --no-cache

echo "Levantando contenedores..."
sudo docker compose up -d --remove-orphans

echo "Prueba de containers:"
sudo docker compose ps

echo "Deploy completado."
