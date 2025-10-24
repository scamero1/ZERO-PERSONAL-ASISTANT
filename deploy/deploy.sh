#!/usr/bin/env bash
set -euo pipefail
# Deploy inicial: clona si es necesario, construye imagenes y levanta servicios.
PROJECT_DIR="/opt/zero"
REPO="https://github.com/scamero1/ZERO-PERSONAL-ASISTANT.git"

echo "Deploy: comprobando directorio $PROJECT_DIR"
if [ ! -d "$PROJECT_DIR" ] || [ -z "$(ls -A "$PROJECT_DIR")" ]; then
  echo "Directorio vacío o no existe. Clonando repo..."
  sudo mkdir -p "$PROJECT_DIR"
  sudo chown "$(whoami):$(whoami)" "$PROJECT_DIR"
  git clone "$REPO" "$PROJECT_DIR"
fi

cd "$PROJECT_DIR"

if [ ! -f .env ]; then
  echo ".env no encontrado en $PROJECT_DIR. Crea .env a partir de .env.example y reintenta."
  exit 1
fi

# Detectar ruta de docker compose
DOCKER_COMPOSE_CMD="docker compose"
if ! command -v docker >/dev/null 2>&1; then
  echo "Docker no instalado. Instala Docker antes de ejecutar este script."
  exit 1
fi

echo "Actualizando repo y verificando branch origin/main..."
git fetch --all --prune || true
git reset --hard origin/main || git reset --hard origin/master || true

echo "Construyendo imagen(es) Docker..."
sudo $DOCKER_COMPOSE_CMD build --no-cache

echo "Levantando contenedores (detached)..."
sudo $DOCKER_COMPOSE_CMD up -d --remove-orphans

echo "Verificando estado de contenedores..."
sudo $DOCKER_COMPOSE_CMD ps

echo "Deploy finalizado."
