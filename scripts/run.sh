#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

export PATH="$HOME/.local/bin:$PATH"

# 从 .preview 读取 expose_port，读不到 fallback 5000
EXPOSE_PORT=$(awk -F '[ =]+' '/^expose_port/ {gsub(/[^0-9]/, "", $2); print $2; exit}' .preview 2>/dev/null || echo 5000)
export PORT="$EXPOSE_PORT"

# 确保 Redis / PostgreSQL 已启动（幂等）
if ! redis-cli ping >/dev/null 2>&1; then
  redis-server --daemonize yes --port 6379
fi
service postgresql start >/dev/null 2>&1 || true
# 等待 postgres 就绪（最多 5s）；已就绪则立即跳过
if ! PGPASSWORD=resume psql -h 127.0.0.1 -U resume -d resume_agent -tAc "SELECT 1" >/dev/null 2>&1; then
  for i in 1 2 3 4 5; do
    PGPASSWORD=resume psql -h 127.0.0.1 -U resume -d resume_agent -tAc "SELECT 1" >/dev/null 2>&1 && break
    sleep 1
  done
fi

# 清理残留（绝不碰 9000）
fuser -k "${EXPOSE_PORT}/tcp" 2>/dev/null || true
sleep 1

# 启动后端（FastAPI 托管前端 dist），绑定 0.0.0.0
cd "$PROJECT_DIR/backend"
exec "$PROJECT_DIR/.venv/bin/uvicorn" app.main:app --host 0.0.0.0 --port "$EXPOSE_PORT" --workers 1