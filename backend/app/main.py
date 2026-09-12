import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api.auth_routes import router as auth_router
from .api.routes import router
from .config import get_settings
from .db import Base, engine

settings = get_settings()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

# 建表（仅创建缺失的表，不会修改已有表结构；如需重建表，运行 init_db.py）
Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.app_name, version=settings.version)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(router)

# 托管前端构建产物（Vue dist）
FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount(
        "/assets",
        StaticFiles(directory=str(FRONTEND_DIST / "assets")),
        name="assets",
    )


@app.get("/")
def index():
    """SPA 入口：返回前端 index.html，由 vue-router 接管路由。"""
    if FRONTEND_DIST.exists():
        return FileResponse(str(FRONTEND_DIST / "index.html"))
    return {
        "message": settings.app_name,
        "tip": "前端尚未构建，请构建 frontend 后再访问",
        "docs": "/docs",
    }


# SPA 前端路由回退：/login /register /history 等都返回 index.html
@app.get("/{full_path:path}")
def spa_fallback(full_path: str):
    """非 /api、/assets、/docs 开头的路径返回 SPA 入口。"""
    if full_path.startswith(("api/", "assets/", "docs", "openapi.json")):
        return None
    if (FRONTEND_DIST / "index.html").exists():
        return FileResponse(str(FRONTEND_DIST / "index.html"))
    return {"message": "frontend not built"}
