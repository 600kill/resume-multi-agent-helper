#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

export PATH="$HOME/.local/bin:$PATH"

# 安装 Python 依赖
if command -v uv >/dev/null 2>&1 && [ -f "pyproject.toml" ]; then
  if [ -n "${PIP_TARGET:-}" ]; then
    # 部署模式：安装到平台指定的 PIP_TARGET
    uv export --frozen --no-hashes --no-dev 2>/dev/null | \
      uv pip install --no-cache --target "$PIP_TARGET" -r - || \
      uv pip install --no-cache --index-url https://mirrors.aliyun.com/pypi/simple/ --target "$PIP_TARGET" . 2>/dev/null || true
  else
    # 本地模式：优先走缓存的 .venv
    if [ ! -x "$PROJECT_DIR/.venv/bin/uvicorn" ]; then
      uv sync --index-url https://mirrors.aliyun.com/pypi/simple/ || uv sync
    fi
  fi
else
  [ -f "requirements.txt" ] && pip install -r requirements.txt
fi

# 构建前端产物（FastAPI 托管）
cd "$PROJECT_DIR/frontend"
if [ ! -d "node_modules" ]; then
  pnpm install --frozen-lockfile || pnpm install
fi
if [ ! -d "dist" ]; then
  pnpm build
fi

echo "Deploy build completed."