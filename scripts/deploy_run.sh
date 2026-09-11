#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

export PATH="$HOME/.local/bin:$PATH"

PORT=5000

# 解析 -p 参数（保留，与部署平台约定一致）
while getopts "p:h" opt; do
  case "$opt" in
    p) PORT="$OPTARG" ;;
    h) echo "Usage: $0 -p <port>"; exit 0 ;;
    *) echo "Invalid option: -$OPTARG"; exit 1 ;;
  esac
done

export PORT

# 数据库/缓存地址：优先平台注入的环境变量，fallback 本地默认
export RESUME_DATABASE_URL="${PGDATABASE_URL:-${DATABASE_URL:-postgresql://resume:resume@127.0.0.1:5432/resume_agent}}"
export RESUME_REDIS_URL="${REDIS_URL:-redis://127.0.0.1:6379/0}"

cd "$PROJECT_DIR"
exec "$PROJECT_DIR/.venv/bin/uvicorn" app.main:app --app-dir backend --host 0.0.0.0 --port "$PORT" --workers 1