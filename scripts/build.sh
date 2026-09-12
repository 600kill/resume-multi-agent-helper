#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

export PATH="$HOME/.local/bin:$PATH"

# Python 依赖（已就绪则跳过，未就绪用国内镜像加速）
if [ ! -x "$PROJECT_DIR/.venv/bin/uvicorn" ]; then
  uv sync --index-url https://mirrors.aliyun.com/pypi/simple/ || uv sync
fi

# 前端依赖与构建（dist 已存在则跳过重复构建）
cd "$PROJECT_DIR/frontend"
if [ ! -d "node_modules" ]; then
  pnpm install --frozen-lockfile
fi
if [ ! -d "dist" ]; then
  pnpm build
fi

echo "Build completed."