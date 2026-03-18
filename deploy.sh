#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# deploy.sh — Manual production deploy script
# ---------------------------------------------------------------------------
# Usage:
#   ./deploy.sh                     # deploy from current branch
#   ./deploy.sh --build             # force image rebuild
#   ./deploy.sh --down-volumes      # DANGER: wipe data volumes and redeploy
#
# Requires:
#   - Docker + Docker Compose installed on the server
#   - .env file present at project root (NOT committed to git)
#   - Running from the project root directory
#
# Design: keep it simple — git pull + docker compose up.
# No Kubernetes, no Helm, no CI runners required.
# ---------------------------------------------------------------------------

set -euo pipefail

COMPOSE="docker compose -f docker/docker-compose.yml"
BUILD_FLAG=""
DOWN_VOLUMES=false

for arg in "$@"; do
    case "$arg" in
        --build)        BUILD_FLAG="--build" ;;
        --down-volumes) DOWN_VOLUMES=true ;;
        *)
            echo "Unknown argument: $arg"
            echo "Usage: ./deploy.sh [--build] [--down-volumes]"
            exit 1
            ;;
    esac
done

echo "==> Pulling latest code"
git pull --ff-only

echo "==> Checking .env exists"
if [ ! -f backend/.env ]; then
    echo "ERROR: backend/.env file not found. Copy backend/.env.example and fill in values."
    exit 1
fi

if [ "$DOWN_VOLUMES" = true ]; then
    echo "==> WARNING: Stopping containers and removing volumes (data will be lost)"
    read -p "Type 'yes' to confirm: " confirm
    if [ "$confirm" != "yes" ]; then
        echo "Aborted."
        exit 0
    fi
    $COMPOSE down -v
fi

echo "==> Stopping app container (keep DB containers running)"
$COMPOSE stop app || true

echo "==> Starting all services"
# shellcheck disable=SC2086
$COMPOSE up -d $BUILD_FLAG

echo "==> Waiting for readiness check"
for i in $(seq 1 12); do
    sleep 5
    if curl -sf http://localhost:8000/health/ready > /dev/null 2>&1; then
        echo "==> App is ready"
        $COMPOSE ps
        exit 0
    fi
    echo "    Waiting... ($((i * 5))s)"
done

echo "ERROR: App did not become ready after 60s"
$COMPOSE logs app --tail=50
exit 1
